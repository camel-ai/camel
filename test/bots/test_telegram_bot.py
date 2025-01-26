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
import unittest
from unittest.mock import MagicMock, patch

from camel.agents import ChatAgent
from camel.bots.telegram_bot import TelegramBot


class TestTelegramBot(unittest.TestCase):
    def setUp(self):
        self.chat_agent_mock = MagicMock(spec=ChatAgent)
        self.telegram_token = "123456789:fake_token"

    def test_init_token_provided_uses_provided_token(self):
        bot = TelegramBot(
            self.chat_agent_mock, telegram_token=self.telegram_token
        )
        self.assertEqual(bot.token, self.telegram_token)

    @patch('telebot.TeleBot')
    def test_on_message(self, mock_telebot):
        # Setup bot and mocks for message handling
        bot = TelegramBot(
            self.chat_agent_mock, telegram_token=self.telegram_token
        )
        mock_bot_instance = mock_telebot.return_value

        message_mock = MagicMock()
        message_mock.text = "Hello, world!"

        user_msg_mock = "Hello, world!"
        response_msg_mock = MagicMock(msg=MagicMock(content="Hello back!"))

        self.chat_agent_mock.reset = MagicMock()
        self.chat_agent_mock.step = MagicMock(return_value=response_msg_mock)

        # Test the message handling
        bot.on_message(message_mock)

        # Check if the chat agent's methods are called appropriately
        self.chat_agent_mock.reset.assert_called_once()
        self.chat_agent_mock.step.assert_called_once_with(user_msg_mock)

        # Check if the bot replies with the correct message
        mock_bot_instance.reply_to.assert_called_once_with(
            message_mock, "Hello back!"
        )

    @patch('telebot.TeleBot')
    def test_run_starts_polling(self, mock_telebot):
        bot = TelegramBot(
            self.chat_agent_mock, telegram_token=self.telegram_token
        )
        mock_bot_instance = mock_telebot.return_value
        bot.run()
        mock_bot_instance.infinity_polling.assert_called_once()


if __name__ == '__main__':
    unittest.main()
