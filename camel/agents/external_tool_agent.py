# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from typing import List, Optional, Set

from pydantic import BaseModel

from camel.agents.chat_agent import ChatAgent, FunctionCallingRecord
from camel.memories import AgentMemory
from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.responses import ChatAgentResponse
from camel.terminators import ResponseTerminator
from camel.toolkits import OpenAIFunction
from camel.types import ChatCompletion, OpenAIBackendRole
from camel.utils import Constants


class ExternalToolAgent(ChatAgent):
    r"""An agent that accepts external tools. When an external tool is
    called, the agent will directly return the tool calling request,
    insteaed of executing the tool.

    Args:
        system_message (BaseMessage): The system message for the chat agent.
        external_tools (List[OpenAIFunction], optional): The external tools
            to use in the agent. Upon request, these tools will not be
            automatically executed. Instead, it will return the tool calling
            request. (default: :obj:`None`)
        internal_tools (List[OpenAIFunction], optional): The internal tools
            to use in the agent. These tools will be automatically executed
            locally when requested. (default: :obj:`None`)
        model (BaseModelBackend, optional): The model backend to use for
            generating responses. (default: :obj:`OpenAIModel` with
            `GPT_4O_MINI`)
        api_key (str, optional): The API key for authenticating with the
            LLM service. Only OpenAI and Anthropic model supported (default:
            :obj:`None`)
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
        response_terminators (List[ResponseTerminator], optional): List of
            :obj:`ResponseTerminator` bind to one chat agent.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        system_message: BaseMessage,
        external_tools: Optional[List[OpenAIFunction]] = None,
        internal_tools: Optional[List[OpenAIFunction]] = None,
        model: Optional[BaseModelBackend] = None,
        api_key: Optional[str] = None,
        memory: Optional[AgentMemory] = None,
        message_window_size: Optional[int] = None,
        token_limit: Optional[int] = None,
        output_language: Optional[str] = None,
        response_terminators: Optional[List[ResponseTerminator]] = None,
    ):
        self.external_tools = external_tools or []
        self.internal_tools = internal_tools or []
        tools = self.external_tools + self.internal_tools
        super().__init__(
            system_message,
            model,
            api_key,
            memory,
            message_window_size,
            token_limit,
            output_language,
            tools,
            response_terminators,
        )
        self.external_tool_names: Set[str] = {
            tool.openai_tool_schema["function"]["name"]
            for tool in self.external_tools
        }

    def step(
        self,
        input_message: BaseMessage,
        output_schema: Optional[BaseModel] = None,
    ) -> ChatAgentResponse:
        r"""Performs a single step in the chat session by generating a response
        to the input message.

        Args:
            input_message (BaseMessage): The input message to the agent.
                Its `role` field that specifies the role at backend may be
                either `user` or `assistant` but it will be set to `user`
                anyway since for the self agent any incoming message is
                external.
            output_schema (Optional[BaseModel]): An optional pydantic model
                that includes value types and field descriptions used to
                generate a structured response by LLM. This schema helps
                in defining the expected output format.

        Returns:
            ChatAgentResponse: A struct containing the output messages,
                a boolean indicating whether the chat session has terminated,
                and information about the chat session.
        """
        self.update_memory(input_message, OpenAIBackendRole.USER)

        tool_calls: List[FunctionCallingRecord] = []

        while True:
            # Check if token has exceeded
            try:
                openai_messages, num_tokens = self.memory.get_context()
            except RuntimeError as e:
                return self.step_token_exceed(
                    e.args[1], tool_calls, "max_tokens_exceeded"
                )

            if output_schema is not None and len(self.func_dict) == 0:
                self._add_output_schema_to_tool_list(output_schema)

            # get response from model
            (
                response,
                output_messages,
                finish_reasons,
                usage_dict,
                response_id,
            ) = self._step_model_response(openai_messages, num_tokens)

            # if the model response is not a function call, break the loop
            if not (
                self.is_tools_added()
                and isinstance(response, ChatCompletion)
                and response.choices[0].message.tool_calls is not None
            ):
                break

            # if the model calls an external tool, directly return the request
            tool_call_requests = response.choices[0].message.tool_calls
            called_tool_names = {
                tool_call.function.name for tool_call in tool_call_requests
            }
            if set(called_tool_names) & self.external_tool_names:
                # if model calls an external tool, directly return the request
                info = self._step_get_info(
                    output_messages,
                    finish_reasons,
                    usage_dict,
                    response_id,
                    tool_calls,
                    num_tokens,
                )
                info["tool_call_requests"] = tool_call_requests
                return ChatAgentResponse(
                    msgs=output_messages, terminated=self.terminated, info=info
                )

            # Tools added for function calling and not in stream mode
            func_assistant_msg, func_result_msg, func_record = (
                self.step_tool_call(response)
            )
            tool_calls.append(func_record)
            # Update the messages
            self.update_memory(func_assistant_msg, OpenAIBackendRole.ASSISTANT)
            self.update_memory(func_result_msg, OpenAIBackendRole.FUNCTION)

        output_structured = Constants.FUNC_NAME_FOR_STRUCTURE_OUTPUT in [
            record.func_name for record in tool_calls
        ]
        if output_schema is not None and not output_structured:
            self._add_output_schema_to_tool_list(output_schema)

            (
                response,
                output_messages,
                finish_reasons,
                usage_dict,
                response_id,
            ) = self._step_model_response(openai_messages, num_tokens)

            if isinstance(response, ChatCompletion):
                # Tools added for function calling and not in stream mode
                func_assistant_msg, func_result_msg, func_record = (
                    self.step_tool_call(response)
                )
                tool_calls.append(func_record)
                # Update the messages
                self.update_memory(
                    func_assistant_msg, OpenAIBackendRole.ASSISTANT
                )
                self.update_memory(func_result_msg, OpenAIBackendRole.FUNCTION)

        info = self._step_get_info(
            output_messages,
            finish_reasons,
            usage_dict,
            response_id,
            tool_calls,
            num_tokens,
        )

        # if use structure response, set structure result as content of
        # BaseMessage
        if output_schema and self.model_type.is_openai:
            for base_message_item in output_messages:
                base_message_item.content = str(info['tool_calls'][-1].result)

        return ChatAgentResponse(
            msgs=output_messages, terminated=self.terminated, info=info
        )

    async def step_async(
        self,
        input_message: BaseMessage,
        output_schema: Optional[BaseModel] = None,
    ) -> ChatAgentResponse:
        r"""Performs a single step in the chat session by generating a response
        to the input message. This agent step can call async function calls.

        Args:
            input_message (BaseMessage): The input message to the agent.
                Its `role` field that specifies the role at backend may be
                either `user` or `assistant` but it will be set to `user`
                anyway since for the self agent any incoming message is
                external.
            output_schema (Optional[BaseModel]): An optional pydantic model
                that includes value types and field descriptions used to
                generate a structured response by LLM. This schema helps
                in defining the expected output format.

        Returns:
            ChatAgentResponse: A struct containing the output messages,
                a boolean indicating whether the chat session has terminated,
                and information about the chat session.
        """
        self.update_memory(input_message, OpenAIBackendRole.USER)

        tool_calls: List[FunctionCallingRecord] = []

        while True:
            try:
                openai_messages, num_tokens = self.memory.get_context()
            except RuntimeError as e:
                return self.step_token_exceed(
                    e.args[1], tool_calls, "max_tokens_exceeded"
                )

            if output_schema is not None and len(self.func_dict) == 0:
                self._add_output_schema_to_tool_list(output_schema)

            (
                response,
                output_messages,
                finish_reasons,
                usage_dict,
                response_id,
            ) = self._step_model_response(openai_messages, num_tokens)

            if not (
                self.is_tools_added()
                and isinstance(response, ChatCompletion)
                and response.choices[0].message.tool_calls is not None
            ):
                break

            tool_call_requests = response.choices[0].message.tool_calls
            called_tool_names = {
                tool_call.function.name for tool_call in tool_call_requests
            }
            if set(called_tool_names) & self.external_tool_names:
                # if model calls an external tool, directly return the request
                info = self._step_get_info(
                    output_messages,
                    finish_reasons,
                    usage_dict,
                    response_id,
                    tool_calls,
                    num_tokens,
                )
                info["tool_call_requests"] = tool_call_requests
                return ChatAgentResponse(
                    msgs=output_messages, terminated=self.terminated, info=info
                )

            # Do function calling, and enter the next loop
            (
                func_assistant_msg,
                func_result_msg,
                func_record,
            ) = await self.step_tool_call_async(response)
            # Record the function calling
            tool_calls.append(func_record)
            # Update the messages
            self.update_memory(func_assistant_msg, OpenAIBackendRole.ASSISTANT)
            self.update_memory(func_result_msg, OpenAIBackendRole.FUNCTION)

        output_structured = Constants.FUNC_NAME_FOR_STRUCTURE_OUTPUT in [
            record.func_name for record in tool_calls
        ]
        if output_schema is not None and not output_structured:
            self._add_output_schema_to_tool_list(output_schema)

            (
                response,
                output_messages,
                finish_reasons,
                usage_dict,
                response_id,
            ) = self._step_model_response(openai_messages, num_tokens)

            if isinstance(response, ChatCompletion):
                # Tools added for function calling and not in stream mode
                func_assistant_msg, func_result_msg, func_record = (
                    self.step_tool_call(response)
                )
                tool_calls.append(func_record)
                # Update the messages
                self.update_memory(
                    func_assistant_msg, OpenAIBackendRole.ASSISTANT
                )
                self.update_memory(func_result_msg, OpenAIBackendRole.FUNCTION)

        info = self._step_get_info(
            output_messages,
            finish_reasons,
            usage_dict,
            response_id,
            tool_calls,
            num_tokens,
        )

        # if use structure response, set structure result as content of
        # BaseMessage
        if output_schema and self.model_type.is_openai:
            for base_message_item in output_messages:
                base_message_item.content = str(info['tool_calls'][0].result)

        return ChatAgentResponse(
            msgs=output_messages, terminated=self.terminated, info=info
        )
