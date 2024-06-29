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
import argparse
import os
from typing import TYPE_CHECKING, Optional

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import OpenAIModel
from camel.types import ModelType

# Conditionally import telebot types only for type checking
if TYPE_CHECKING:
    from telebot.types import Message  # type: ignore[import-untyped]


parser = argparse.ArgumentParser(
    description="Arguments for telegram bot.",
)
parser.add_argument(
    "--sys_msg",
    type=str,
    help="System message for the telegram bot.",
    required=False,
    default="You are a helpful assistant.",
)
parser.add_argument(
    "--model_type",
    type=str,
    help="Model type for the telegram bot.",
    required=False,
    default=ModelType.GPT_3_5_TURBO.value,
)

args = parser.parse_args()


class TelegramBot:
    r"""Represents a Telegram bot that is powered by an agent.

    Args:
        chat_agent (ChatAgent): Chat agent that will power the bot.
        telegram_token (str, optional): The bot token.
    """

    def __init__(
        self,
        chat_agent: ChatAgent,
        telegram_token: Optional[str] = None,
    ) -> None:
        self.chat_agent = chat_agent

        if not telegram_token:
            self.token = os.getenv('TELEGRAM_TOKEN')
            if not self.token:
                raise ValueError(
                    "`TELEGRAM_TOKEN` not found in environment variables. "
                    "Get it from t.me/BotFather."
                )
        else:
            self.token = telegram_token

        try:
            import telebot  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "Please install `telebot` first. "
                "You can install it by running "
                "`pip install pyTelegramBotAPI`."
            )
        self.bot = telebot.TeleBot(token=self.token)

        # Register the message handler within the constructor
        self.bot.message_handler(func=lambda message: True)(self.on_message)

    def run(self) -> None:
        r"""Start the Telegram bot."""
        print("Telegram bot is running...")
        self.bot.infinity_polling()

    def on_message(self, message: 'Message') -> None:
        r"""Handles incoming messages from the user.

        Args:
            message (types.Message): The incoming message object.
        """
        self.chat_agent.reset()

        if not message.text:
            return

        user_msg = BaseMessage.make_user_message(
            role_name="User", content=message.text
        )
        assistant_response = self.chat_agent.step(user_msg)

        self.bot.reply_to(message, assistant_response.msg.content)


def main():
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=args.sys_msg,
    )
    model = OpenAIModel(
        model_type=ModelType(args.model_type),
        model_config_dict=ChatGPTConfig().__dict__,
    )
    agent = ChatAgent(
        assistant_sys_msg,
        model=model,
    )
    bot = TelegramBot(agent)
    bot.run()


if __name__ == "__main__":
    main()
