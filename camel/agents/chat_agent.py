from typing import Any, Dict, List, Optional, Tuple

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from camel.configs import ChatGPTConfig
from camel.messages import ChatMessage, MessageType, SystemMessage
from camel.typing import ModelType
from camel.utils import get_model_token_limit, num_tokens_from_messages


class ChatAgent:
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
        model: ModelType = ModelType.GPT_3_5_TURBO,
        model_config: Any = None,
        message_window_size: Optional[int] = None,
    ) -> None:

        self.system_message = system_message
        self.role_name = system_message.role_name
        self.role_type = system_message.role_type
        self.meta_dict = system_message.meta_dict

        self.model = model
        self.model_config = model_config or ChatGPTConfig()
        self.model_token_limit = get_model_token_limit(self.model)
        self.message_window_size = message_window_size

        self.terminated = False
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
    def step(
        self,
        input_message: ChatMessage,
    ) -> Tuple[Optional[List[ChatMessage]], bool, Dict[str, Any]]:
        r"""Performs a single step in the chat session by generating a response
        to the input message.

        Args:
            input_message (ChatMessage): The input message to the agent.

        Returns:
            Tuple[Optional[List[ChatMessage]], bool, Dict[str, Any]]: A tuple
                containing the output messages, a boolean indicating whether
                the chat session has terminated, and information about the chat
                session.
        """
        messages = self.update_messages(input_message)
        if self.message_window_size is not None and len(
                messages) > self.message_window_size:
            messages = [self.system_message
                        ] + messages[-self.message_window_size:]
        openai_messages = [message.to_openai_message() for message in messages]
        num_tokens = num_tokens_from_messages(openai_messages, self.model)

        if num_tokens < self.model_token_limit:
            response = openai.ChatCompletion.create(
                model=self.model.value,
                messages=openai_messages,
                **self.model_config.__dict__,
            )
            output_messages = [
                ChatMessage(role_name=self.role_name, role_type=self.role_type,
                            meta_dict=dict(), **dict(choice["message"]))
                for choice in response["choices"]
            ]
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
            self.terminated = True
            output_messages = None

            info = self.get_info(
                None,
                None,
                ["max_tokens_exceeded"],
                num_tokens,
            )

        return output_messages, self.terminated, info

    def __repr__(self) -> str:
        r"""Returns a string representation of the :obj:`ChatAgent`.

        Returns:
            str: The string representation of the :obj:`ChatAgent`.
        """
        return f"ChatAgent({self.role_name}, {self.role_type}, {self.model})"
