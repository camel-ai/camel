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
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

from colorama import Fore
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential

from camel.agents import BaseAgent
from camel.configs import ChatGPTConfig
from camel.messages import ChatMessage, MessageType, SystemMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.typing import ModelType, RoleType
from camel.utils import (
    num_tokens_from_messages,
    openai_api_key_required,
    print_text_animated,
)


@dataclass(frozen=True)
class ChatAgentResponse:
    r"""Response of a ChatAgent.

    Attributes:
        msgs (List[ChatMessage]): A list of zero, one or several messages.
            If the list is empty, there is some error in message generation.
            If the list has one message, this is normal mode.
            If the list has several messages, this is the critic mode.
        terminated (bool): A boolean indicating whether the agent decided
            to terminate the chat session.
        info (Dict[str, Any]): Extra information about the chat message.
    """
    msgs: List[ChatMessage]
    terminated: bool
    info: Dict[str, Any]

    @property
    def msg(self):
        if len(self.msgs) != 1:
            raise RuntimeError("Property msg is only available"
                               "for a single message in msgs")
        return self.msgs[0]


class ChatAgent(BaseAgent):
    r"""Class for managing conversations of CAMEL Chat Agents.

    Args:
        system_message (SystemMessage): The system message for the chat agent.
        model (ModelType, optional): The LLM model to use for generating
            responses. (default :obj:`ModelType.GPT_3_5_TURBO`)
        model_config (Any, optional): Configuration options for the LLM model.
            (default: :obj:`None`)
        message_window_size (int, optional): The maximum number of previous
            messages to include in the context window. If `None`, no windowing
            is performed. (default: :obj:`None`)
    """

    def __init__(
        self,
        system_message: SystemMessage,
        model: Optional[ModelType] = None,
        model_config: Optional[Any] = None,
        message_window_size: Optional[int] = None,
    ) -> None:

        self.system_message: SystemMessage = system_message
        self.role_name: str = system_message.role_name
        self.role_type: RoleType = system_message.role_type

        self.model: ModelType = (model if model is not None else
                                 ModelType.GPT_3_5_TURBO)
        self.model_config: ChatGPTConfig = model_config or ChatGPTConfig()
        self.message_window_size: Optional[int] = message_window_size

        self.model_backend: BaseModelBackend = ModelFactory.create(
            self.model, self.model_config.__dict__)
        self.model_token_limit: int = self.model_backend.token_limit

        self.terminated: bool = False
        self.init_messages()

    def reset(self) -> List[MessageType]:
        r"""Resets the :obj:`ChatAgent` to its initial state and returns the
        stored messages.

        Returns:
            List[MessageType]: The stored messages.
        """
        self.terminated = False
        self.init_messages()
        return self.stored_messages

    def get_info(
        self,
        id: Optional[str],
        usage: Optional[Dict[str, int]],
        termination_reasons: List[str],
        num_tokens: int,
    ) -> Dict[str, Any]:
        r"""Returns a dictionary containing information about the chat session.

        Args:
            id (str, optional): The ID of the chat session.
            usage (Dict[str, int], optional): Information about the usage of
                the LLM model.
            termination_reasons (List[str]): The reasons for the termination of
                the chat session.
            num_tokens (int): The number of tokens used in the chat session.

        Returns:
            Dict[str, Any]: The chat session information.
        """
        return {
            "id": id,
            "usage": usage,
            "termination_reasons": termination_reasons,
            "num_tokens": num_tokens,
        }

    def init_messages(self) -> None:
        r"""Initializes the stored messages list with the initial system
        message.
        """
        self.stored_messages: List[MessageType] = [self.system_message]

    def update_messages(self, message: ChatMessage) -> List[MessageType]:
        r"""Updates the stored messages list with a new message.

        Args:
            message (ChatMessage): The new message to add to the stored
                messages.

        Returns:
            List[ChatMessage]: The updated stored messages.
        """
        self.stored_messages.append(message)
        return self.stored_messages

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    @openai_api_key_required
    def step(
        self,
        input_message: ChatMessage,
        print_response: bool = False,
        print_response_color: Fore = Fore.MAGENTA,
    ) -> ChatAgentResponse:
        r"""Performs a single step in the chat session by generating a response
        to the input message.

        Args:
            input_message (ChatMessage): The input message to the agent.
                Its `role` field that specifies the role at backend may be
                either `user` or `assistant` but it will be set to `user`
                anyway since for the self agent any incoming message is
                external.
            print_response (bool, optional): Print response on-the-fly
                animatedly. (default: :obj:`False`)
            print_response_color (Fore, optional): Color for the response
                to be printed. (default: :obj:`Fore.MAGENTA`)

        Returns:
            ChatAgentResponse: A struct containing the output messages,
                a boolean indicating whether the chat session has terminated,
                and information about the chat session.
        """
        msg_user_at_backend = input_message.set_user_role_at_backend()
        messages = self.update_messages(msg_user_at_backend)
        if self.message_window_size is not None and len(
                messages) > self.message_window_size:
            messages = [self.system_message
                        ] + messages[-self.message_window_size:]
        openai_messages = [message.to_openai_message() for message in messages]
        num_tokens = num_tokens_from_messages(openai_messages, self.model)

        info: Dict[str, Any]

        if num_tokens < self.model_token_limit:
            response = self.model_backend.run(openai_messages)
            if not self.model_backend.streaming:
                if not isinstance(response, dict):
                    raise RuntimeError("OpenAI returned unexpected struct")
                output_messages = self.handle_batch_response(
                    response, print_response, print_response_color)
                info = self.get_info(
                    response["id"],
                    response["usage"],
                    [
                        str(choice["finish_reason"])
                        for choice in response["choices"]
                    ],
                    num_tokens,
                )
            else:
                output_messages, finish_reasons, usage_dict, response_id = \
                    self.handle_stream_response(
                        response,
                        num_tokens,
                        print_response,
                        print_response_color
                    )
                info = self.get_info(
                    response_id,
                    usage_dict,
                    finish_reasons,
                    num_tokens,
                )
        else:
            self.terminated = True
            output_messages = []

            info = self.get_info(
                None,
                None,
                ["max_tokens_exceeded"],
                num_tokens,
            )

        return ChatAgentResponse(output_messages, self.terminated, info)

    def handle_batch_response(
            self, response: Dict[str, Any], print_response: bool = False,
            print_response_color: Fore = Fore.MAGENTA) -> List[ChatMessage]:
        r"""

        Args:
            response (dict): Model response.
            print_response (bool, optional): Print response on-the-fly
                animatedly. (default: :obj:`False`)
            print_response_color (Fore, optional): Color for the response
                to be printed. (default: :obj:`Fore.MAGENTA`)

        Returns:
            List[ChatMessage]: A tuple of list of output `ChatMessage`.
        """
        output_messages: List[ChatMessage] = []
        for choice in response["choices"]:
            chat_message = ChatMessage(role_name=self.role_name,
                                       role_type=self.role_type,
                                       meta_dict=dict(),
                                       **dict(choice["message"]))
            if print_response:
                self.print_message(print_response_color, chat_message)
            output_messages.append(chat_message)
        return output_messages

    def handle_stream_response(
        self,
        response: Any,
        prompt_tokens: int,
        print_response: bool = False,
        print_response_color: Fore = Fore.MAGENTA,
    ) -> Tuple[List[ChatMessage], List[str], Dict[str, int], str]:
        r"""

        Args:
            response (dict): Model response.
            prompt_tokens (int): Number of input prompt tokens.
            print_response (bool, optional): Print response on-the-fly
                animatedly. (default: :obj:`False`)
            print_response_color (Fore, optional): Color for the response
                to be printed. (default: :obj:`Fore.MAGENTA`)

        Returns:
            tuple: A tuple of list of output `ChatMessage`, list of
                finish reasons, usage dictionary, and response id.
        """
        content_dict = defaultdict(lambda: "")
        finish_reasons = defaultdict(lambda: "")
        output_messages: List[ChatMessage] = []
        response_id: str = ""
        # All choices in one response share one role
        role: str = ""
        for i, chunk in enumerate(response):
            chunk: Dict[str, Any]
            response_id = chunk["id"]
            for _, choice in enumerate(chunk["choices"]):
                index = choice["index"]
                choice: Dict[str, Any]
                delta = choice["delta"]
                if len(delta) != 0:
                    # When response has not been stopped
                    # Notice that only the first chunk has the "role"
                    role = delta.get("role", role)
                    delta_content = delta.get("content", "")
                    content_dict[index] += delta_content
                    if print_response:
                        # Skip role information except first time print
                        self.print_message(print_response_color, delta_content,
                                           end_newline=False,
                                           skip_role_info=(i != 0))
                else:
                    # When that choice has finished
                    if print_response:
                        # Just print a new line at the end
                        print_text_animated("", reset=True)
                    finish_reasons[index] = choice["finish_reason"]
                    chat_message = ChatMessage(
                        role_name=self.role_name, role_type=self.role_type,
                        meta_dict=dict(),
                        **dict(role=role, content=content_dict[index]))
                    output_messages.append(chat_message)
        finish_reasons = [
            finish_reasons[i] for i in range(len(finish_reasons))
        ]
        usage_dict = self.get_usage_dict(output_messages, prompt_tokens)
        return output_messages, finish_reasons, usage_dict, response_id

    def get_usage_dict(self, output_messages: List[ChatMessage],
                       prompt_tokens: int) -> Dict[str, int]:
        r"""Get usage dictionary when using the stream mode.

        Args:
            output_messages (list): List of output messages.
            prompt_tokens (int): Number of input prompt tokens.

        Returns:
            dict: Usage dictionary.
        """
        openai_messages = [
            message.to_openai_message() for message in output_messages
        ]
        completion_tokens = num_tokens_from_messages(openai_messages,
                                                     self.model)
        prompt_tokens = prompt_tokens
        usage_dict = dict(completion_tokens=completion_tokens,
                          prompt_tokens=prompt_tokens,
                          total_tokens=completion_tokens + prompt_tokens)
        return usage_dict

    def print_message(self, print_response_color: str,
                      message: Union[ChatMessage, str],
                      end_newline: bool = True, skip_role_info: bool = False):
        r"""Print a `ChatMessage` content with specified color animatedly.

        Args:
            print_response_color (Fore): Color to print the chat message.
            message (ChatMessage or str): A `ChatMessage` object.
            end_newline (bool, optional): Whether print a newline at
                the end of text. (default: :obj:`False`)
            skip_role_info (bool, optional): Whether skip printing
                the role info. (default: :obj:`False`)
        """
        role_info = f'{self.role_name} ({self.role_type.value}): '
        if not skip_role_info:
            print_text_animated(print_response_color + role_info,
                                end_newline=False)
        msg = message if isinstance(message, str) else message.content
        print_text_animated(print_response_color + msg,
                            end_newline=end_newline, reset=True)

    def __repr__(self) -> str:
        r"""Returns a string representation of the :obj:`ChatAgent`.

        Returns:
            str: The string representation of the :obj:`ChatAgent`.
        """
        return f"ChatAgent({self.role_name}, {self.role_type}, {self.model})"
