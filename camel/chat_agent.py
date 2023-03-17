from typing import Any, Dict, List, Optional, Tuple

import openai
from camel_typing import (MessageType, ModeType, RoleType, SystemMessage,
                          ChatMessage)
from camel_utils import get_model_token_limit, num_tokens_from_messages
from configs import ChatGPTConfig
from tenacity import retry, stop_after_attempt


class ChatAgent:
    def __init__(
        self,
        system_message: SystemMessage,
        model: ModeType,
        model_config: Any = None,
    ) -> None:
        self.system_message = system_message
        self.role_name = system_message.role_name
        self.role_type = system_message.role_type

        self.model = model
        self.model_config = model_config or ChatGPTConfig()
        self.model_token_limit = get_model_token_limit(self.model)

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

    @retry(stop=stop_after_attempt(5))
    def step(
        self, input_message: ChatMessage
    ) -> Tuple[List[ChatMessage], bool, Dict[str, Any]]:
        messages = self.update_messages(input_message)
        openai_messages = [message.to_openai_message() for message in messages]
        num_tokens = num_tokens_from_messages(openai_messages, self.model)

        if num_tokens < self.model_token_limit:
            response = openai.ChatCompletion.create(
                model=self.model.value,
                messages=openai_messages,
                **self.model_config.__dict__,
            )
            output_messages = [
                ChatMessage(self.role_name, self.role_type,
                            **dict(choice["message"]))
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


if __name__ == "__main__":
    from configs import SystemMessageGenerator
    chat_gpt_args = ChatGPTConfig()
    system_message = SystemMessageGenerator().from_role(
        "doctor", RoleType.ASSISTANT)
    assistant = ChatAgent(
        system_message,
        ModeType.GPT_3_5_TURBO,
        chat_gpt_args,
    )

    assert str(assistant) == (
        "ChatAgent(doctor, RoleType.ASSISTANT, ModeType.GPT_3_5_TURBO)")

    assistant.reset()
    messages, terminated, info = assistant.step(
        ChatMessage("patient", RoleType.USER, "user", "Hello!"))

    assert terminated is False
    assert messages != []
    print(info)

    assistant.reset()
    messages, terminated, info = assistant.step(
        ChatMessage("patient", RoleType.USER, "user", "Hello!" * 4096))

    assert terminated is True
    assert messages == []
    print(info)
