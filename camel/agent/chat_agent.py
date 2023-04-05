from typing import Any, Dict, List, Optional, Tuple

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from camel.configs import ChatGPTConfig
from camel.message import ChatMessage, MessageType, SystemMessage
from camel.typing import ModeType
from camel.utils import get_model_token_limit, num_tokens_from_messages


class ChatAgent:

    def __init__(
        self,
        system_message: SystemMessage,
        model: ModeType,
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

    def reset(self) -> None:
        self.terminated = False
        self.init_messages()
        return self.stored_messages

    def get_info(
        self,
        id: Optional[str],
        usage: Optional[Dict[str, int]],
        finish_reasons: List[str],
        num_tokens: int,
    ) -> Dict[str, Any]:
        return {
            "id": id,
            "usage": usage,
            "finish_reasons": finish_reasons,
            "num_tokens": num_tokens,
        }

    def init_messages(self) -> None:
        self.stored_messages: List[MessageType] = [self.system_message]

    def update_messages(self, message: ChatMessage) -> List[ChatMessage]:
        self.stored_messages.append(message)
        return self.stored_messages

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    def step(
        self,
        input_message: ChatMessage,
    ) -> Tuple[List[ChatMessage], bool, Dict[str, Any]]:
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
            self.update_messages(output_messages[0])

        else:
            self.terminated = True
            output_messages = []

            info = self.get_info(
                None,
                None,
                ["max_tokens_exceeded"],
                num_tokens,
            )

        return output_messages, self.terminated, info

    def __repr__(self) -> str:
        return f"ChatAgent({self.role_name}, {self.role_type}, {self.model})"
