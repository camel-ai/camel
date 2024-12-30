# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from pydantic import BaseModel

from camel.agents.base import BaseAgent
from camel.memories import (
    AgentMemory,
    ChatHistoryMemory,
    MemoryRecord,
    ScoreBasedContextCreator,
)
from camel.messages import BaseMessage, FunctionCallingMessage, OpenAIMessage
from camel.models import (
    BaseModelBackend,
    ModelFactory,
    ModelManager,
    ModelProcessingError,
)
from camel.responses import ChatAgentResponse
from camel.toolkits import FunctionTool
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelPlatformType,
    ModelType,
    OpenAIBackendRole,
    RoleType,
)
from camel.utils import (
    get_model_encoding,
)

if TYPE_CHECKING:
    from openai import Stream

    from camel.terminators import ResponseTerminator


logger = logging.getLogger(__name__)

# AgentOps decorator setting
try:
    import os

    if os.getenv("AGENTOPS_API_KEY") is not None:
        from agentops import track_agent
    else:
        raise ImportError
except (ImportError, AttributeError):
    from camel.utils import track_agent


class FunctionCallingRecord(BaseModel):
    r"""Historical records of functions called in the conversation.

    Attributes:
        func_name (str): The name of the function being called.
        args (Dict[str, Any]): The dictionary of arguments passed to
            the function.
        result (Any): The execution result of calling this function.
    """

    func_name: str
    args: Dict[str, Any]
    result: Any

    def __str__(self) -> str:
        r"""Overridden version of the string function.

        Returns:
            str: Modified string to represent the function calling.
        """
        return (
            f"Function Execution: {self.func_name}\n"
            f"\tArgs: {self.args}\n"
            f"\tResult: {self.result}"
        )

    def as_dict(self) -> dict[str, Any]:
        r"""Returns the function calling record as a dictionary.

        Returns:
            dict[str, Any]: The function calling record as a dictionary.
        """
        return self.model_dump()


@track_agent(name="ChatAgent")
class ChatAgent(BaseAgent):
    r"""Class for managing conversations of CAMEL Chat Agents.

    Args:
        system_message (Union[BaseMessage, str], optional): The system message
            for the chat agent.
        model (BaseModelBackend, optional): The model backend to use for
            generating responses. (default: :obj:`ModelPlatformType.DEFAULT`
            with `ModelType.DEFAULT`)
        memory (AgentMemory, optional): The agent memory for managing chat
            messages. If `None`, a :obj:`ChatHistoryMemory` will be used.
            (default: :obj:`None`)
        message_window_size (int, optional): The maximum number of previous
            messages to include in the context window. If `None`, no windowing
            is performed. (default: :obj:`None`)
        token_limit (int, optional): The maximum number of tokens in a context.
            The context will be automatically pruned to fulfill the limitation.
            If `None`, it will be set according to the backend model.
            (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
            agent. (default: :obj:`None`)
        tools (Optional[List[Union[FunctionTool, Callable]]], optional): List
            of available :obj:`FunctionTool` or :obj:`Callable`. (default:
            :obj:`None`)
        response_terminators (List[ResponseTerminator], optional): List of
            :obj:`ResponseTerminator` bind to one chat agent.
            (default: :obj:`None`)
        scheduling_strategy (str): name of function that defines how to select
            the next model in ModelManager. (default: :str:`round_robin`)
        single_iteration (bool): Whether to let the agent perform only one
            model calling at each step. (default: :obj:`False`)
    """

    def __init__(
        self,
        system_message: Optional[Union[BaseMessage, str]] = None,
        model: Optional[
            Union[BaseModelBackend, List[BaseModelBackend]]
        ] = None,
        memory: Optional[AgentMemory] = None,
        message_window_size: Optional[int] = None,
        token_limit: Optional[int] = None,
        output_language: Optional[str] = None,
        tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        external_tools: Optional[
            List[Union[FunctionTool, Callable, Dict[str, Any]]]
        ] = None,
        response_terminators: Optional[List[ResponseTerminator]] = None,
        scheduling_strategy: str = "round_robin",
        single_iteration: bool = False,
    ) -> None:
        # Set up model backend
        self.model_backend = ModelManager(
            (
                model
                if model is not None
                else ModelFactory.create(
                    model_platform=ModelPlatformType.DEFAULT,
                    model_type=ModelType.DEFAULT,
                )
            ),
            scheduling_strategy=scheduling_strategy,
        )
        self.model_type = self.model_backend.model_type

        # Set up memory
        context_creator = ScoreBasedContextCreator(
            self.model_backend.token_counter,
            token_limit or self.model_backend.token_limit,
        )
        self.memory: AgentMemory = memory or ChatHistoryMemory(
            context_creator, window_size=message_window_size
        )

        # Set up system message and initialize messages
        self._system_message = (
            BaseMessage.make_assistant_message(
                role_name="Assistant", content=system_message
            )
            if isinstance(system_message, str)
            else system_message
        )
        self._output_language = output_language
        self._update_system_message_for_output_language()
        self.init_messages()

        # Set up role name and role type
        self.role_name: str = (
            getattr(self.system_message, "role_name", None) or "assistant"
        )
        self.role_type: RoleType = (
            getattr(self.system_message, "role_type", None)
            or RoleType.ASSISTANT
        )

        # Set up tools
        self._tools = (
            [
                tool if isinstance(tool, FunctionTool) else FunctionTool(tool)
                for tool in tools
            ]
            if tools
            else []
        )

        # Set up other properties
        self.terminated = False
        self.response_terminators = response_terminators or []
        self.single_iteration = single_iteration

    def reset(self):
        r"""Resets the :obj:`ChatAgent` to its initial state."""
        self.terminated = False
        self.init_messages()
        for terminator in self.response_terminators:
            terminator.reset()

    @property
    def system_message(self) -> Optional[BaseMessage]:
        return self._system_message

    @property
    def tool_dict(self) -> Dict[str, FunctionTool]:
        return {tool.get_function_name(): tool for tool in self._tools}

    @property
    def tool_list(self) -> List[str]:
        return [tool.get_function_name() for tool in self._tools]

    @property
    def tool_schemas(self) -> List[Dict[str, Any]]:
        return [tool.get_openai_tool_schema() for tool in self._tools]

    def add_tool(self, tool: Union[FunctionTool, Callable]) -> None:
        r"""Add a tool to the agent."""
        new_tool = (
            tool if isinstance(tool, FunctionTool) else FunctionTool(tool)
        )
        self._tools.append(new_tool)

    def remove_tool(self, tool_name: str) -> bool:
        r"""Remove a tool from the agent by name.

        Returns:
            bool: Whether the tool was successfully removed.
        """
        for tool in self._tools:
            if tool.get_function_name() != tool_name:
                continue
            self._tools.remove(tool)
            return True
        return False

    @property
    def has_tools(self) -> bool:
        r"""Whether tool calling is enabled for this agent.

        Returns:
            bool: Whether tool calling is enabled for this agent, determined
                by whether the dictionary of tools is empty.
        """
        return len(self._tools) > 0

    def update_memory(
        self, message: BaseMessage, role: OpenAIBackendRole
    ) -> None:
        r"""Updates the agent memory with a new message.

        Args:
            message (BaseMessage): The new message to add to the stored
                messages.
            role (OpenAIBackendRole): The backend role type.
        """
        self.memory.write_record(
            MemoryRecord(message=message, role_at_backend=role)
        )

    def _update_system_message_for_output_language(self) -> None:
        r"""Updates the output language for the system message. The output
        language determines the language in which the output text should be
        generated.
        """
        language_prompt = (
            "\nRegardless of the input language, "
            f"you must output text in {self._output_language}."
        )
        if self._system_message is not None:
            content = self._system_message.content + language_prompt
            self._system_message = self._system_message.create_new_instance(
                content
            )
        else:
            self._system_message = BaseMessage.make_assistant_message(
                role_name="Assistant",
                content=language_prompt,
            )

    def get_info(
        self,
        session_id: Optional[str],
        usage: Optional[Dict[str, int]],
        termination_reasons: List[str],
        num_tokens: int,
        tool_calls: List[FunctionCallingRecord],
    ) -> Dict[str, Any]:
        r"""Returns a dictionary containing information about the chat session.

        Args:
            session_id (str, optional): The ID of the chat session.
            usage (Dict[str, int], optional): Information about the usage of
                the LLM.
            termination_reasons (List[str]): The reasons for the termination
                of the chat session.
            num_tokens (int): The number of tokens used in the chat session.
            tool_calls (List[FunctionCallingRecord]): The list of function
                calling records, containing the information of called tools.

        Returns:
            Dict[str, Any]: The chat session information.
        """
        return {
            "id": session_id,
            "usage": usage,
            "termination_reasons": termination_reasons,
            "num_tokens": num_tokens,
            "tool_calls": tool_calls,
        }

    def init_messages(self) -> None:
        r"""Initializes the stored messages list with the current system
        message.
        """
        self.memory.clear()
        if self.system_message is not None:
            self.update_memory(self.system_message, OpenAIBackendRole.SYSTEM)

    def record_message(self, message: BaseMessage) -> None:
        r"""Records the externally provided message into the agent memory as if
        it were an answer of the :obj:`ChatAgent` from the backend. Currently,
        the choice of the critic is submitted with this method.

        Args:
            message (BaseMessage): An external message to be recorded in the
                memory.
        """
        self.update_memory(message, OpenAIBackendRole.ASSISTANT)

    def step(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> ChatAgentResponse:
        r"""Executes a single step in the chat session, generating a response
        to the input message.

        Args:
            input_message (Union[BaseMessage, str]): The input message for the
                agent. If provided as a BaseMessage, the `role` is adjusted to
                `user` to indicate an external message.
            response_format (Optional[Type[BaseModel]], optional): A Pydantic
                model defining the expected structure of the response. Used to
                generate a structured response if provided. (default:
                :obj:`None`)

        Returns:
            ChatAgentResponse: Contains output messages, a termination status
                flag, and session information.
        """

        # Convert input message to BaseMessage if necessary
        input_message = (
            BaseMessage.make_user_message(
                role_name="User", content=input_message
            )
            if isinstance(input_message, str)
            else input_message
        )

        # Add user input to memory
        self.update_memory(input_message, OpenAIBackendRole.USER)

        return self._handle_step(response_format)

    def _handle_step(
        self,
        response_format: Optional[Type[BaseModel]],
    ) -> ChatAgentResponse:
        r"""Handles a single or multi-step interaction."""
        # Record function calls made during the session
        tool_call_records: List[FunctionCallingRecord] = []

        while True:
            try:
                openai_messages, num_tokens = self.memory.get_context()
            except RuntimeError as e:
                return self._step_token_exceed(
                    e.args[1], tool_call_records, "max_tokens_exceeded"
                )

            # Process model response
            (
                response,
                output_messages,
                finish_reasons,
                usage_dict,
                response_id,
            ) = self._step_model_response(
                openai_messages, response_format, num_tokens
            )

            # Single-step mode
            if self.single_iteration:
                break

            # Handle tool requests
            if (
                isinstance(response, ChatCompletion)
                and response.choices[0].message.tool_calls
            ):
                tool_call_records.append(self._step_tool_call(response))

        # Final info and response
        info = self._step_get_info(
            output_messages,
            finish_reasons,
            usage_dict,
            response_id,
            tool_call_records,
            num_tokens,
        )

        self._log_final_output(output_messages)
        return ChatAgentResponse(
            msgs=output_messages, terminated=self.terminated, info=info
        )

    def _log_final_output(self, output_messages: List[BaseMessage]) -> None:
        r"""Log final messages or warnings about multiple responses."""
        if len(output_messages) == 1:
            self.record_message(output_messages[0])
        else:
            logger.warning(
                "Multiple messages returned in `step()`. Record "
                "selected message manually using `record_message()`."
            )

    # TODO: Redesign this method
    async def step_async(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> ChatAgentResponse:
        r"""Performs a single step in the chat session by generating a response
        to the input message. This agent step can call async function calls.

        Args:
            input_message (Union[BaseMessage, str]): The input message to the
                agent. For BaseMessage input, its `role` field that specifies
                the role at backend may be either `user` or `assistant` but it
                will be set to `user` anyway since for the self agent any
                incoming message is external. For str input, the `role_name`
                would be `User`.
            response_format (Optional[Type[BaseModel]], optional): A pydantic
                model class that includes value types and field descriptions
                used to generate a structured response by LLM. This schema
                helps in defining the expected output format. (default:
                :obj:`None`)

        Returns:
            ChatAgentResponse: A struct containing the output messages,
                a boolean indicating whether the chat session has terminated,
                and information about the chat session.
        """
        if isinstance(input_message, str):
            input_message = BaseMessage.make_user_message(
                role_name="User", content=input_message
            )

        self.update_memory(input_message, OpenAIBackendRole.USER)

        tool_call_records: List[FunctionCallingRecord] = []
        while True:
            try:
                openai_messages, num_tokens = self.memory.get_context()
            except RuntimeError as e:
                return self._step_token_exceed(
                    e.args[1], tool_call_records, "max_tokens_exceeded"
                )

            (
                response,
                output_messages,
                finish_reasons,
                usage_dict,
                response_id,
            ) = self._step_model_response(
                openai_messages, response_format, num_tokens
            )

            if (
                not self.has_tools
                or not isinstance(response, ChatCompletion)
                or not response.choices[0].message.tool_calls
            ):
                break

            # Normal function calling
            tool_call_records.append(
                await self._step_tool_call_async(response)
            )

        info = self._step_get_info(
            output_messages,
            finish_reasons,
            usage_dict,
            response_id,
            tool_call_records,
            num_tokens,
        )

        if len(output_messages) == 1:
            # Auto record if the output result is a single message
            self.record_message(output_messages[0])
        else:
            logger.warning(
                "Multiple messages returned in `step()`, message won't be "
                "recorded automatically. Please call `record_message()` to "
                "record the selected message manually."
            )

        return ChatAgentResponse(
            msgs=output_messages, terminated=self.terminated, info=info
        )

    def _step_model_response(
        self,
        openai_messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]],
        num_tokens: int,
    ) -> tuple[
        Union[ChatCompletion, Stream],
        List[BaseMessage],
        List[str],
        Dict[str, int],
        str,
    ]:
        r"""Internal function for agent step model response."""

        response = None
        # Obtain the model's response
        for _ in range(len(self.model_backend.models)):
            try:
                response = self.model_backend.run(
                    openai_messages, response_format, self.tool_schemas
                )
                break
            except Exception as exc:
                logger.error(
                    f"An error occurred while running model "
                    f"{self.model_backend.model_type}, "
                    f"index: {self.model_backend.current_model_index}",
                    exc_info=exc,
                )
                continue
        if not response:
            raise ModelProcessingError(
                "Unable to process messages: none of the provided models "
                "run succesfully."
            )

        logger.info(
            f"Model {self.model_backend.model_type}, "
            f"index {self.model_backend.current_model_index}, "
            f"processed these messages: {openai_messages}"
        )

        if isinstance(response, ChatCompletion):
            output_messages, finish_reasons, usage_dict, response_id = (
                self.handle_batch_response(response)
            )
        else:
            output_messages, finish_reasons, usage_dict, response_id = (
                self.handle_stream_response(response, num_tokens)
            )
        return (
            response,
            output_messages,
            finish_reasons,
            usage_dict,
            response_id,
        )

    def _step_get_info(
        self,
        output_messages: List[BaseMessage],
        finish_reasons: List[str],
        usage_dict: Dict[str, int],
        response_id: str,
        tool_calls: List[FunctionCallingRecord],
        num_tokens: int,
    ) -> Dict[str, Any]:
        r"""Process the output of a chat step and gather information about the
        step.

        This method checks for termination conditions, updates the agent's
        state, and collects information about the chat step, including tool
        calls and termination reasons.

        Args:
            output_messages (List[BaseMessage]): The messages generated in
                this step.
            finish_reasons (List[str]): The reasons for finishing the
                generation for each message.
            usage_dict (Dict[str, int]): Dictionary containing token usage
                information.
            response_id (str): The ID of the response from the model.
            tool_calls (List[FunctionCallingRecord]): Records of function calls
                made during this step.
            num_tokens (int): The number of tokens used in this step.

        Returns:
            Dict[str, Any]: A dictionary containing information about the chat
                step, including termination status, reasons, and tool call
                information.

        Note:
            This method iterates over all response terminators and checks if
            any of them signal termination. If a terminator signals
            termination, the agent's state is updated accordingly, and the
            termination reason is recorded.
        """
        termination = [
            terminator.is_terminated(output_messages)
            for terminator in self.response_terminators
        ]
        # Terminate the agent if any of the terminator terminates
        self.terminated, termination_reason = next(
            (
                (terminated, termination_reason)
                for terminated, termination_reason in termination
                if terminated
            ),
            (False, None),
        )
        # For now only retain the first termination reason
        if self.terminated and termination_reason is not None:
            finish_reasons = [termination_reason] * len(finish_reasons)

        info = self.get_info(
            response_id,
            usage_dict,
            finish_reasons,
            num_tokens,
            tool_calls,
        )
        return info

    def handle_batch_response(
        self, response: ChatCompletion
    ) -> Tuple[List[BaseMessage], List[str], Dict[str, int], str]:
        r"""Process a batch response from the model and extract the necessary
        information.

        Args:
            response (dict): Model response.

        Returns:
            tuple: A tuple of list of output `ChatMessage`, list of
                finish reasons, usage dictionary, and response id.
        """
        output_messages: List[BaseMessage] = []
        for choice in response.choices:
            chat_message = BaseMessage(
                role_name=self.role_name,
                role_type=self.role_type,
                meta_dict=dict(),
                content=choice.message.content or "",
                parsed=getattr(choice.message, "parsed", None),
            )
            # Process log probabilities, append to the message meta information
            if choice.logprobs is not None:
                tokens_logprobs = choice.logprobs.content

                if tokens_logprobs is not None:
                    # Extract and structure logprob information
                    logprobs_info = [
                        {
                            "token": token_logprob.token,
                            "logprob": token_logprob.logprob,
                            "top_logprobs": [
                                (top_logprob.token, top_logprob.logprob)
                                for top_logprob in token_logprob.top_logprobs
                            ],
                        }
                        for token_logprob in tokens_logprobs
                    ]
                # Ensure meta_dict exists before adding logprobs info
                if chat_message.meta_dict is None:
                    chat_message.meta_dict = {}
                chat_message.meta_dict["logprobs_info"] = logprobs_info
            # Append the processed chat message to output
            output_messages.append(chat_message)

        finish_reasons = [
            str(choice.finish_reason) for choice in response.choices
        ]
        usage = (
            self._safe_model_dump(response.usage)
            if response.usage is not None
            else {}
        )
        return (
            output_messages,
            finish_reasons,
            usage,
            response.id,
        )

    def _safe_model_dump(self, obj) -> dict:
        r"""Safely dump a Pydantic model to a dictionary.

        This method attempts to use the `model_dump` method if available,
        otherwise it falls back to the `dict` method.

        Args:
            obj: The Pydantic model instance to be dumped.

        Returns:
            dict: A dictionary representation of the Pydantic model.
        """
        # Check if the `model_dump` method exists (Pydantic v2)
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        # Fallback to `dict()` method (Pydantic v1)
        elif hasattr(obj, "dict"):
            return obj.dict()
        else:
            raise TypeError("The object is not a Pydantic model")

    def handle_stream_response(
        self,
        response: Stream[ChatCompletionChunk],
        prompt_tokens: int,
    ) -> Tuple[List[BaseMessage], List[str], Dict[str, int], str]:
        r"""Process a stream response from the model and extract the necessary
        information.

        Args:
            response (dict): Model response.
            prompt_tokens (int): Number of input prompt tokens.

        Returns:
            tuple: A tuple of list of output `ChatMessage`, list of
                finish reasons, usage dictionary, and response id.
        """
        content_dict: defaultdict = defaultdict(lambda: "")
        finish_reasons_dict: defaultdict = defaultdict(lambda: "")
        output_messages: List[BaseMessage] = []
        response_id: str = ""
        # All choices in one response share one role
        for chunk in response:
            response_id = chunk.id
            for choice in chunk.choices:
                index = choice.index
                delta = choice.delta
                if delta.content is not None:
                    # When response has not been stopped
                    # Notice that only the first chunk_dict has the "role"
                    content_dict[index] += delta.content
                if choice.finish_reason:
                    finish_reasons_dict[index] = choice.finish_reason
                    chat_message = BaseMessage(
                        role_name=self.role_name,
                        role_type=self.role_type,
                        meta_dict=dict(),
                        content=content_dict[index],
                    )
                    output_messages.append(chat_message)
        finish_reasons = [
            finish_reasons_dict[i] for i in range(len(finish_reasons_dict))
        ]
        usage_dict = self.get_usage_dict(output_messages, prompt_tokens)
        return output_messages, finish_reasons, usage_dict, response_id

    def _step_token_exceed(
        self,
        num_tokens: int,
        tool_calls: List[FunctionCallingRecord],
        termination_reason: str,
    ) -> ChatAgentResponse:
        r"""Return trivial response containing number of tokens and information
        of called functions when the number of tokens exceeds.

        Args:
            num_tokens (int): Number of tokens in the messages.
            tool_calls (List[FunctionCallingRecord]): List of information
                objects of functions called in the current step.
            termination_reason (str): String of termination reason.

        Returns:
            ChatAgentResponse: The struct containing trivial outputs and
                information about token number and called functions.
        """
        self.terminated = True
        output_messages: List[BaseMessage] = []

        info = self.get_info(
            None,
            None,
            [termination_reason],
            num_tokens,
            tool_calls,
        )

        return ChatAgentResponse(
            msgs=output_messages,
            terminated=self.terminated,
            info=info,
        )

    def _step_tool_call(
        self,
        response: ChatCompletion,
    ) -> FunctionCallingRecord:
        r"""Execute the function with arguments following the model's response.

        Args:
            response (Dict[str, Any]): The response obtained by calling the
                model.

        Returns:
            tuple: A tuple consisting of two obj:`FunctionCallingMessage`,
                one about the arguments and the other about the execution
                result, and a struct for logging information about this
                function call.
        """
        choice = response.choices[0]
        if choice.message.tool_calls is None:
            raise RuntimeError("Tool call is None")
        func_name = choice.message.tool_calls[0].function.name

        arguments_str = choice.message.tool_calls[0].function.arguments
        args = self._safe_json_loads(arguments_str)

        tool = self.tool_dict[func_name]
        result = tool(**args)

        assist_msg = FunctionCallingMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=None,
            content="",
            func_name=func_name,
            args=args,
        )
        func_msg = FunctionCallingMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=None,
            content="",
            func_name=func_name,
            result=result,
        )

        # Record information about this function call
        func_record = FunctionCallingRecord(
            func_name=func_name, args=args, result=result
        )
        self.update_memory(assist_msg, OpenAIBackendRole.ASSISTANT)
        self.update_memory(func_msg, OpenAIBackendRole.FUNCTION)

        return func_record

    def _safe_json_loads(self, arguments_str):
        # Replace Python types with their JSON equivalents
        arguments_str = arguments_str.replace("None", "null")
        arguments_str = arguments_str.replace("True", "true")
        arguments_str = arguments_str.replace("False", "false")

        # Attempt to parse the corrected string
        try:
            return json.loads(arguments_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

    async def _step_tool_call_async(
        self,
        response: ChatCompletion,
    ) -> FunctionCallingRecord:
        r"""Execute the async function with arguments following the model's
        response.

        Args:
            response (Dict[str, Any]): The response obtained by calling the
                model.

        Returns:
            tuple: A tuple consisting of two obj:`FunctionCallingMessage`,
                one about the arguments and the other about the execution
                result, and a struct for logging information about this
                function call.
        """
        # Note that when function calling is enabled, `n` is set to 1.
        choice = response.choices[0]
        if choice.message.tool_calls is None:
            raise RuntimeError("Tool call is None")
        func_name = choice.message.tool_calls[0].function.name

        args = json.loads(choice.message.tool_calls[0].function.arguments)
        tool = self.tool_dict[func_name]
        result = await tool(**args)

        assist_msg = FunctionCallingMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=None,
            content="",
            func_name=func_name,
            args=args,
        )
        func_msg = FunctionCallingMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=None,
            content="",
            func_name=func_name,
            result=result,
        )

        # Record information about this function call
        func_record = FunctionCallingRecord(
            func_name=func_name, args=args, result=result
        )

        self.update_memory(assist_msg, OpenAIBackendRole.ASSISTANT)
        self.update_memory(func_msg, OpenAIBackendRole.FUNCTION)

        return func_record

    def get_usage_dict(
        self, output_messages: List[BaseMessage], prompt_tokens: int
    ) -> Dict[str, int]:
        r"""Get usage dictionary when using the stream mode.

        Args:
            output_messages (list): List of output messages.
            prompt_tokens (int): Number of input prompt tokens.

        Returns:
            dict: Usage dictionary.
        """
        encoding = get_model_encoding(self.model_type.value_for_tiktoken)
        completion_tokens = 0
        for message in output_messages:
            completion_tokens += len(encoding.encode(message.content))
        usage_dict = dict(
            completion_tokens=completion_tokens,
            prompt_tokens=prompt_tokens,
            total_tokens=completion_tokens + prompt_tokens,
        )
        return usage_dict

    def add_model_scheduling_strategy(self, name: str, strategy_fn: Callable):
        r"""Add a scheduling strategy method provided by user to ModelManger.

        Args:
            name (str): The name of the strategy.
            strategy_fn (Callable): The scheduling strategy function.
        """
        self.model_backend.add_strategy(name, strategy_fn)

    def __repr__(self) -> str:
        r"""Returns a string representation of the :obj:`ChatAgent`.

        Returns:
            str: The string representation of the :obj:`ChatAgent`.
        """
        return (
            f"ChatAgent({self.role_name}, {self.role_type}, {self.model_type})"
        )
