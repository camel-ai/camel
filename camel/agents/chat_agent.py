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
import json
from collections import defaultdict
from dataclasses import dataclass
from types import GeneratorType
from typing import Any, Callable, Dict, List, Optional, Tuple

from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential

from camel.agents import BaseAgent
from camel.configs import BaseConfig, ChatGPTConfig
from camel.functions import OpenAIFunction
from camel.messages import BaseMessage, FunctionCallingMessage, OpenAIMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.typing import ModelType, RoleType
from camel.utils import (
    get_model_encoding,
    num_tokens_from_messages,
    openai_api_key_required,
)


@dataclass(frozen=True)
class ChatAgentResponse:
    r"""Response of a ChatAgent.

    Attributes:
        msgs (List[BaseMessage]): A list of zero, one or several messages.
            If the list is empty, there is some error in message generation.
            If the list has one message, this is normal mode.
            If the list has several messages, this is the critic mode.
        terminated (bool): A boolean indicating whether the agent decided
            to terminate the chat session.
        info (Dict[str, Any]): Extra information about the chat message.
    """
    msgs: List[BaseMessage]
    terminated: bool
    info: Dict[str, Any]

    @property
    def msg(self):
        if len(self.msgs) != 1:
            raise RuntimeError("Property msg is only available "
                               "for a single message in msgs.")
        return self.msgs[0]


@dataclass(frozen=True)
class ChatRecord:
    r"""Historical records of who made what message.

    Attributes:
        role_at_backend (str): Role of the message that mirrors OpenAI
            message role that may be `system` or `user` or `assistant`.
        message (BaseMessage): Message payload.
    """
    role_at_backend: str
    message: BaseMessage

    def to_openai_message(self):
        r"""Converts the payload message to OpenAI-compatible format.

        Returns:
            OpenAIMessage: OpenAI-compatible message
        """
        return self.message.to_openai_message(self.role_at_backend)


@dataclass(frozen=True)
class FunctionCallingRecord:
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

        return (f"Function Execution: {self.func_name}\n"
                f"\tArgs: {self.args}\n"
                f"\tResult: {self.result}")


class ChatAgent(BaseAgent):
    r"""Class for managing conversations of CAMEL Chat Agents.

    Args:
        system_message (BaseMessage): The system message for the chat agent.
        model (ModelType, optional): The LLM model to use for generating
            responses. (default :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any, optional): Configuration options for the LLM model.
            (default: :obj:`None`)
        message_window_size (int, optional): The maximum number of previous
            messages to include in the context window. If `None`, no windowing
            is performed. (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
            agent. (default: :obj:`None`)
        function_list (Optional[List[OpenAIFunction]]): List of available
            :obj:`OpenAIFunction`. (default: :obj:`None`)
    """

    def __init__(
        self,
        system_message: BaseMessage,
        model: Optional[ModelType] = None,
        model_config: Optional[BaseConfig] = None,
        message_window_size: Optional[int] = None,
        output_language: Optional[str] = None,
        function_list: Optional[List[OpenAIFunction]] = None,
    ) -> None:

        self.orig_sys_message: BaseMessage = system_message
        self.system_message = system_message
        self.role_name: str = system_message.role_name
        self.role_type: RoleType = system_message.role_type
        self.output_language: Optional[str] = output_language
        if self.output_language is not None:
            self.set_output_language(self.output_language)

        self.model: ModelType = (model if model is not None else
                                 ModelType.GPT_3_5_TURBO)
        self.message_window_size: Optional[int] = message_window_size

        self.func_dict: Dict[str, Callable] = {}
        if function_list is not None:
            for func in function_list:
                self.func_dict[func.name] = func.func
        self.model_config = model_config or ChatGPTConfig()

        self.model_backend: BaseModelBackend = ModelFactory.create(
            self.model, self.model_config.__dict__)
        self.model_token_limit: int = self.model_backend.token_limit

        self.terminated: bool = False
        self.stored_messages: List[ChatRecord]
        self.init_messages()

    def reset(self):
        r"""Resets the :obj:`ChatAgent` to its initial state and returns the
        stored messages.

        Returns:
            List[BaseMessage]: The stored messages.
        """
        self.terminated = False
        self.init_messages()

    @property
    def system_message(self) -> BaseMessage:
        r"""The getter method for the property :obj:`system_message`.

        Returns:
            BaseMessage: The system message of this agent.
        """
        return self._system_message

    @system_message.setter
    def system_message(self, message: BaseMessage):
        r"""The setter method for the property :obj:`system_message`.

        Args:
            message (BaseMessage): The message to be set as the
                new system message of this agent.
        """
        self._system_message = message

    def is_function_calling_enabled(self) -> bool:
        r"""Whether OpenAI function calling is enabled for this agent.

        Returns:
            bool: Whether OpenAI function calling is enabled for this
                agent, determined by whether the dictionary of functions
                is empty.
        """
        return len(self.func_dict) > 0

    def set_output_language(self, output_language: str) -> BaseMessage:
        r"""Sets the output language for the system message. This method
        updates the output language for the system message. The output
        language determines the language in which the output text should be
        generated.

        Args:
            output_language (str): The desired output language.

        Returns:
            BaseMessage: The updated system message object.
        """
        self.output_language = output_language
        content = (self.orig_sys_message.content +
                   ("\nRegardless of the input language, "
                    f"you must output text in {output_language}."))
        self.system_message = self.system_message.create_new_instance(content)
        return self.system_message

    def get_info(self, id: Optional[str], usage: Optional[Dict[str, int]],
                 termination_reasons: List[str], num_tokens: int,
                 called_funcs: List[FunctionCallingRecord]) -> Dict[str, Any]:
        r"""Returns a dictionary containing information about the chat session.

        Args:
            id (str, optional): The ID of the chat session.
            usage (Dict[str, int], optional): Information about the usage of
                the LLM model.
            termination_reasons (List[str]): The reasons for the termination
                of the chat session.
            num_tokens (int): The number of tokens used in the chat session.
            called_funcs (List[FunctionCallingRecord]): The list of function
                calling records, containing the information of called
                functions.

        Returns:
            Dict[str, Any]: The chat session information.
        """
        return {
            "id": id,
            "usage": usage,
            "termination_reasons": termination_reasons,
            "num_tokens": num_tokens,
            "called_functions": called_funcs,
        }

    def init_messages(self) -> None:
        r"""Initializes the stored messages list with the initial system
        message.
        """
        self.stored_messages = [ChatRecord('system', self.system_message)]

    def update_messages(self, role: str,
                        message: BaseMessage) -> List[ChatRecord]:
        r"""Updates the stored messages list with a new message.

        Args:
            message (BaseMessage): The new message to add to the stored
                messages.

        Returns:
            List[BaseMessage]: The updated stored messages.
        """
        if role not in {'system', 'user', 'assistant', 'function'}:
            raise ValueError(f"Unsupported role {role}")
        self.stored_messages.append(ChatRecord(role, message))
        return self.stored_messages

    def submit_message(self, message: BaseMessage) -> None:
        r"""Submits the externally provided message as if it were an answer of
        the chat LLM from the backend. Currently, the choice of the critic is
        submitted with this method.

        Args:
            message (BaseMessage): An external message to be added as an
                assistant response.
        """
        self.stored_messages.append(ChatRecord('assistant', message))

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    @openai_api_key_required
    def step(
        self,
        input_message: BaseMessage,
    ) -> ChatAgentResponse:
        r"""Performs a single step in the chat session by generating a response
        to the input message.

        Args:
            input_message (BaseMessage): The input message to the agent.
            Its `role` field that specifies the role at backend may be either
            `user` or `assistant` but it will be set to `user` anyway since
            for the self agent any incoming message is external.

        Returns:
            ChatAgentResponse: A struct containing the output messages,
                a boolean indicating whether the chat session has terminated,
                and information about the chat session.
        """
        messages = self.update_messages('user', input_message)

        output_messages: List[BaseMessage]
        info: Dict[str, Any]
        called_funcs: List[FunctionCallingRecord] = []
        while True:
            # Format messages and get the token number
            openai_messages: Optional[List[OpenAIMessage]]
            num_tokens: int
            openai_messages, num_tokens = self.preprocess_messages(messages)

            # Terminate when number of tokens exceeds the limit
            if num_tokens >= self.model_token_limit:
                return self.step_token_exceed(num_tokens, called_funcs)

            # Obtain LLM's response and validate it
            response = self.model_backend.run(openai_messages)
            self.validate_model_response(response)

            if not self.model_backend.stream:
                output_messages, finish_reasons, usage_dict, response_id = (
                    self.handle_batch_response(response))
            else:
                output_messages, finish_reasons, usage_dict, response_id = (
                    self.handle_stream_response(response, num_tokens))

            if self.is_function_calling_enabled(
            ) and finish_reasons[0] == 'function_call':
                # Do function calling
                func_assistant_msg, func_result_msg, func_record = (
                    self.step_function_call(response))

                # Update the messages
                messages = self.update_messages('assistant',
                                                func_assistant_msg)
                messages = self.update_messages('function', func_result_msg)
                called_funcs.append(func_record)
            else:
                # Function calling disabled or chat stopped
                info = self.get_info(
                    response_id,
                    usage_dict,
                    finish_reasons,
                    num_tokens,
                    called_funcs,
                )
                break

        return ChatAgentResponse(output_messages, self.terminated, info)

    def preprocess_messages(
            self,
            messages: List[ChatRecord]) -> Tuple[List[OpenAIMessage], int]:
        r"""Truncate the list of messages if message window is defined and
        the current length of message list is beyond the window size. Then
        convert the list of messages to OpenAI's input format and calculate
        the number of tokens.

        Args:
            messages (List[ChatRecord]): The list of structs containing
                information about previous chat messages.

        Returns:
            tuple: A tuple containing the truncated list of messages in
                OpenAI's input format and the number of tokens.
        """

        if (self.message_window_size
                is not None) and (len(messages) > self.message_window_size):
            messages = [ChatRecord('system', self.system_message)
                        ] + messages[-self.message_window_size:]

        openai_messages: List[OpenAIMessage]
        openai_messages = [record.to_openai_message() for record in messages]
        num_tokens = num_tokens_from_messages(openai_messages, self.model)

        return openai_messages, num_tokens

    def validate_model_response(self, response: Any) -> None:
        r"""Validate the type of the response returned by the model.

        Args:
            response (Any): The response returned by the model.
        """
        if not self.model_backend.stream:
            if not isinstance(response, dict):
                raise RuntimeError("OpenAI returned unexpected batch struct")
        else:
            if not isinstance(response, GeneratorType):
                raise RuntimeError("OpenAI returned unexpected stream struct")

    def handle_batch_response(
        self, response: Dict[str, Any]
    ) -> Tuple[List[BaseMessage], List[str], Dict[str, int], str]:
        r"""

        Args:
            response (dict): Model response.

        Returns:
            tuple: A tuple of list of output `ChatMessage`, list of
                finish reasons, usage dictionary, and response id.
        """
        output_messages: List[BaseMessage] = []
        for choice in response["choices"]:
            chat_message = BaseMessage(role_name=self.role_name,
                                       role_type=self.role_type,
                                       meta_dict=dict(),
                                       content=choice["message"]['content'])
            output_messages.append(chat_message)
        finish_reasons = [
            str(choice["finish_reason"]) for choice in response["choices"]
        ]
        return output_messages, finish_reasons, dict(
            response["usage"]), response["id"]

    def handle_stream_response(
        self,
        response: Any,
        prompt_tokens: int,
    ) -> Tuple[List[BaseMessage], List[str], Dict[str, int], str]:
        r"""

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
        role: str = ""
        for chunk in response:
            response_id = chunk["id"]
            for choice in chunk["choices"]:
                index: int = choice["index"]
                delta: Dict = choice["delta"]
                if len(delta) != 0:
                    # When response has not been stopped
                    # Notice that only the first chunk has the "role"
                    role = delta.get("role", role)
                    delta_content = delta.get("content", "")
                    content_dict[index] += delta_content
                else:
                    finish_reasons_dict[index] = choice["finish_reason"]
                    chat_message = BaseMessage(role_name=self.role_name,
                                               role_type=self.role_type,
                                               meta_dict=dict(),
                                               content=content_dict[index])
                    output_messages.append(chat_message)
        finish_reasons = [
            finish_reasons_dict[i] for i in range(len(finish_reasons_dict))
        ]
        usage_dict = self.get_usage_dict(output_messages, prompt_tokens)
        return output_messages, finish_reasons, usage_dict, response_id

    def step_token_exceed(
            self, num_tokens: int,
            called_funcs: List[FunctionCallingRecord]) -> ChatAgentResponse:
        r"""Return trivial response containing number of tokens and information
        of called functions when the number of tokens exceeds.

        Args:
            num_tokens (int): Number of tokens in the messages.
            called_funcs (List[FunctionCallingRecord]): List of information
                objects of functions called in the current step.

        Returns:
            ChatAgentResponse: The struct containing trivial outputs and
                information about token number and called functions.
        """

        self.terminated = True
        output_messages: List[BaseMessage] = []

        info = self.get_info(
            None,
            None,
            ["max_tokens_exceeded"],
            num_tokens,
            called_funcs,
        )

        return ChatAgentResponse(
            output_messages,
            self.terminated,
            info,
        )

    def step_function_call(
        self, response: Dict[str, Any]
    ) -> Tuple[FunctionCallingMessage, FunctionCallingMessage,
               FunctionCallingRecord]:
        r"""Execute the function with arguments following the model's response.

        Args:
            response (Dict[str, Any]): the response obtained by calling the
                model.

        Returns:
            tuple: a tuple consisting of two obj:`FunctionCallingMessage`,
                one about the arguments and the other about the execution
                result, and a struct for logging information about this
                function call.
        """

        # Note that when function calling is enabled, `n` is set to 1.
        choice = response["choices"][0]

        func_name = choice["message"]["function_call"]["name"]
        func = self.func_dict[func_name]

        args_str: str = choice["message"]["function_call"]["arguments"]
        args = json.loads(args_str.replace("\'", "\""))

        # Pass the extracted arguments to the indicated function
        try:
            result = func(**args)
        except Exception:
            raise ValueError(
                f"Execution of function {func.__name__} failed with "
                f"arguments being {args}.")

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
        func_record = FunctionCallingRecord(func_name, args, result)
        return assist_msg, func_msg, func_record

    def get_usage_dict(self, output_messages: List[BaseMessage],
                       prompt_tokens: int) -> Dict[str, int]:
        r"""Get usage dictionary when using the stream mode.

        Args:
            output_messages (list): List of output messages.
            prompt_tokens (int): Number of input prompt tokens.

        Returns:
            dict: Usage dictionary.
        """
        encoding = get_model_encoding(self.model.value_for_tiktoken)
        completion_tokens = 0
        for message in output_messages:
            completion_tokens += len(encoding.encode(message.content))
        usage_dict = dict(completion_tokens=completion_tokens,
                          prompt_tokens=prompt_tokens,
                          total_tokens=completion_tokens + prompt_tokens)
        return usage_dict

    def __repr__(self) -> str:
        r"""Returns a string representation of the :obj:`ChatAgent`.

        Returns:
            str: The string representation of the :obj:`ChatAgent`.
        """
        return f"ChatAgent({self.role_name}, {self.role_type}, {self.model})"
