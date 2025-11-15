import json
from copy import deepcopy
from datetime import date, datetime
from typing import Any, Literal, Optional

from loguru import logger
from pydantic import BaseModel, Field

from tau2.data_model.message import (
    AssistantMessage,
    Message,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.data_model.tasks import EnvAssertion, EnvFunctionCall, InitializationData
from tau2.environment.db import DB
from tau2.environment.tool import Tool
from tau2.environment.toolkit import ToolKitBase, ToolSignature, get_tool_signatures


class EnvironmentInfo(BaseModel):
    """
    Environment information.
    """

    domain_name: str = Field(description="The name of the domain.")
    policy: str = Field(description="The policy of the agent.")
    tool_defs: Optional[dict[str, ToolSignature]] = Field(
        description="The tool definitions of the environment.", default=None
    )


class Environment:
    """
    Environment
    """

    def __init__(
        self,
        domain_name: str,
        policy: str,
        tools: Optional[ToolKitBase] = None,
        user_tools: Optional[ToolKitBase] = None,
        solo_mode: bool = False,
    ):
        """
        Environment
        Args:
            domain_name: The name of the domain.
            policy: The policy of the domain.
            tools: The tools available to the assistant in the domain.
            user_tools: The tools available to the user in the domain.
            solo_mode: The agent will have access to both user and assistant tools.
        """
        self.domain_name = domain_name
        self.policy = policy
        self.tools = tools
        self.user_tools = user_tools
        self.solo_mode = solo_mode
        if self.solo_mode:
            self.validate_solo_mode()
        self.sync_tools()

    def get_domain_name(self) -> str:
        """
        Get the name of the domain.
        """
        return self.domain_name

    def get_policy(self) -> str:
        """
        Get the policy of the domain.
        """
        return self.policy

    def get_tools(self) -> list[Tool]:
        """
        Get the tools of the domain.
        """
        if self.tools is None:
            raise ValueError("Tools not available")
        return list(self.tools.get_tools().values())

    def get_user_tools(self) -> list[Tool]:
        """
        Get the tools of the domain.
        """
        if self.user_tools is None:
            raise ValueError("User tools not available")
        return list(self.user_tools.get_tools().values())

    def get_tools_description(
        self, env_type: Literal["user", "assistant"]
    ) -> Optional[str]:
        """
        Return a description of the user tools.
        """
        if env_type == "user":
            tool_kit = self.user_tools
        elif env_type == "assistant":
            tool_kit = self.tools
        else:
            raise ValueError(f"Invalid environment type: {env_type}")
        if tool_kit is None:
            return None
        tools = sorted(tool_kit.get_tools().values(), key=lambda x: x.name)
        return "\n\n".join(
            [f"{i + 1}. {t.name}\n{t.short_desc}" for i, t in enumerate(tools)]
        )

    def use_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Use a tool available to the assistant of the domain.
        """
        if self.tools is None:
            raise ValueError("Tools not available")
        return self.tools.use_tool(tool_name=tool_name, **kwargs)

    def use_user_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Use a tool available to the user of the domain.
        """
        if self.user_tools is None:
            raise ValueError("User tools not available")
        return self.user_tools.use_tool(tool_name=tool_name, **kwargs)

    def make_tool_call(
        self,
        tool_name: str,
        requestor: Literal["user", "assistant"] = "assistant",
        **kwargs,
    ) -> Any:
        """
        Make a tool call based on the requestor.
        Args:
            tool_name: The name of the tool to call.
            requestor: The requestor of the tool call.
            kwargs: The arguments to pass to the tool.
        Returns:
            The response of the tool call.

        Note: This does not call sync_tools.
        """
        if requestor == "user":
            if self.solo_mode:
                raise ValueError("User tool calls are not allowed in solo mode")
            return self.use_user_tool(tool_name=tool_name, **kwargs)
        elif requestor == "assistant":
            if self.solo_mode and self.user_tools is not None:
                if self.user_tools.has_tool(tool_name):
                    return self.use_user_tool(tool_name=tool_name, **kwargs)
            return self.use_tool(tool_name=tool_name, **kwargs)
        else:
            raise ValueError(f"Invalid requestor: {requestor}")

    def sync_tools(self):
        """
        Sync the user and assistant tools.
        Subclass should override this method if tools need to be synced.
        """
        pass

    def run_env_function_call(self, env_function_call: EnvFunctionCall) -> Any:
        """
        Runs any function available on agent environment or user environment.
        """
        env_type = env_function_call.env_type
        func_name = env_function_call.func_name
        if env_type == "user":
            tool_kit = self.user_tools
        elif env_type == "assistant":
            tool_kit = self.tools
        else:
            raise ValueError(f"Invalid environment type: {env_type}")
        func = getattr(tool_kit, func_name)
        if func is None:
            raise ValueError(f"Function {func_name} not found in {env_type} tools")
        res = func(**env_function_call.arguments)
        self.sync_tools()
        return res

    def run_env_assertion(
        self,
        assertion: EnvAssertion,
        raise_assertion_error: bool = True,
    ) -> bool:
        """
        Runs any assertion function on agent tools or user tools.
        """
        if not isinstance(assertion, EnvAssertion):
            raise ValueError(f"Assertion must be an EnvAssertion. Got {assertion}")
        res = self.run_env_function_call(assertion)
        if not isinstance(res, bool):
            raise ValueError(
                f"Function {assertion.func_name} returned {type(res)} instead of bool"
            )
        assert_pass = res == assertion.assert_value
        if raise_assertion_error:
            assert assert_pass, assertion.message or f"Assertion failed: {assertion}"
        return assert_pass

    def run_env_function_calls(self, env_function_calls: list[EnvFunctionCall]) -> None:
        """
        Run a list of environment function calls. If the function call is an assertion,
        an assertion check will be performed.
        """
        for env_function_call in env_function_calls:
            if isinstance(env_function_call, EnvAssertion):
                self.run_env_assertion(env_function_call, raise_assertion_error=True)
            else:
                self.run_env_function_call(env_function_call)

    def get_info(self, include_tool_info: bool = False) -> EnvironmentInfo:
        """
        Get environment information.
        """
        return EnvironmentInfo(
            domain_name=self.domain_name,
            policy=self.policy,
            tool_defs=(
                get_tool_signatures(self.tools)
                if self.tools is not None and include_tool_info
                else None
            ),
            user_tool_defs=(
                get_tool_signatures(self.user_tools)
                if self.user_tools is not None and include_tool_info
                else None
            ),
        )

    def check_db(self, reference: DB) -> bool:
        """
        Compare the agent database with the reference
        """
        return self.get_db_hash() == reference.get_hash()

    def check_user_db(self, reference: DB) -> bool:
        """
        Compare the user database with the reference
        """
        return self.get_user_db_hash() == reference.get_hash()

    def get_db_hash(self) -> Optional[str]:
        """
        Get a hash of the agent database
        Returns None if the database is not available
        """
        if self.tools is None:
            return None
        return self.tools.get_db_hash()

    def get_user_db_hash(self) -> Optional[str]:
        """
        Get a hash of the user database
        Returns None if the database is not available
        """
        if self.user_tools is None:
            return None
        return self.user_tools.get_db_hash()

    def set_state(
        self,
        initialization_data: Optional[InitializationData],
        initialization_actions: Optional[list[EnvFunctionCall]],
        message_history: list[Message],
    ):
        """
        Set the state of the environment given initialization data and a list of messages.
        """
        if self.solo_mode:
            assert all(
                [not isinstance(message, UserMessage) for message in message_history]
            ), "User messages are not allowed in solo mode"

        def get_actions_from_messages(
            messages: list[Message],
        ) -> list[tuple[ToolCall, ToolMessage]]:
            """
            Get the actions from the messages.
            """
            messages = deepcopy(messages)[::-1]
            actions = []
            while messages:
                message = messages.pop()
                if isinstance(message, ToolMessage):
                    raise ValueError(
                        "Tool message not expected. Tool messages should always follow a tool call."
                    )
                if (
                    isinstance(message, (AssistantMessage, UserMessage))
                    and message.is_tool_call()
                ):
                    tool_calls = message.tool_calls
                    for tc in tool_calls:
                        if len(messages) == 0:
                            raise ValueError("Tool message expected. Got None.")
                        tm = messages.pop()
                        if not isinstance(tm, ToolMessage):
                            raise ValueError(f"Tool message expected. Got {type(tm)}")
                        if tc.id != tm.id:
                            raise ValueError(
                                f"Tool call id mismatch. Got {tc.id} and {tm.id}"
                            )
                        actions.append((tc, tm))

            return actions

        if initialization_data is not None:
            if initialization_data.agent_data is not None:
                self.tools.update_db(initialization_data.agent_data)
            if initialization_data.user_data is not None:
                self.user_tools.update_db(initialization_data.user_data)

        if initialization_actions is not None:
            for action in initialization_actions:
                self.run_env_function_call(action)

        action_responses = get_actions_from_messages(message_history)
        for tool_call, expected_response in action_responses:
            response = self.get_response(tool_call)
            try:
                content = json.loads(response.content)
            except json.JSONDecodeError:
                content = response.content
            try:
                expected_content = json.loads(expected_response.content)
            except json.JSONDecodeError:
                expected_content = expected_response.content
            if content != expected_content:
                raise ValueError(
                    f"Tool call:\n{tool_call}\n\nReturned:\n{response}\n\nExpected:\n{expected_response}"
                )
        self.sync_tools()

    @classmethod
    def to_json_str(cls, resp: Any) -> str:
        """
        Convert a response to a JSON string.
        """

        def _process(resp: Any) -> str:
            if isinstance(resp, BaseModel):
                return resp.model_dump()
            elif isinstance(resp, str):
                return resp
            elif resp is None:
                return resp
            elif isinstance(resp, (int, float, bool)):
                return str(resp)
            elif isinstance(resp, list):
                return [_process(item) for item in resp]
            elif isinstance(resp, tuple):
                return tuple(_process(item) for item in resp)
            elif isinstance(resp, dict):
                return {k: _process(v) for k, v in resp.items()}
            elif isinstance(resp, (datetime, date)):
                # TODO: this did not fix the error: Object of type date is not JSON serializable
                return resp.isoformat()
            else:
                raise ValueError(f"Unsupported type: {type(resp)}")

        if not isinstance(resp, str):
            return json.dumps(_process(resp), default=str)  # FIXME: add default=str
        return resp

    def set_solo_mode(self, solo_mode: bool):
        """
        Set the solo mode of the environment.
        """
        self.solo_mode = solo_mode
        if solo_mode:
            self.validate_solo_mode()

    def validate_solo_mode(self) -> None:
        """
        Validate the tool call in solo mode.
        """
        assistant_tool_names = set(self.tools.get_tools().keys())
        user_tool_names = (
            set(self.user_tools.get_tools().keys())
            if self.user_tools is not None
            else set()
        )
        overlap = assistant_tool_names & user_tool_names
        if len(overlap) > 0:
            raise ValueError(f"Tool names overlap: {overlap}")

    def get_response(self, message: ToolCall) -> ToolMessage:
        """
        Get the response of the domain. This also calls sync_tools.
        Args:
            message: The message to get the response for.
        Returns:
            The response of the tool call.
        """
        error = False
        try:
            resp = self.make_tool_call(
                message.name, requestor=message.requestor, **message.arguments
            )
            self.sync_tools()
        except Exception as e:
            resp = f"Error: {e}"
            error = True
        logger.debug(f"Response: {resp}")
        resp = self.to_json_str(resp)
        return ToolMessage(
            id=message.id,
            content=resp,
            requestor=message.requestor,
            role="tool",
            error=error,
        )
