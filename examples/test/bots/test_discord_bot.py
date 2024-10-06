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

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from camel.agents import ChatAgent
from camel.bots.discord_bot import DiscordBot


class TestDiscordBot(unittest.TestCase):
    def setUp(self):
        self.chat_agent_mock = MagicMock(spec=ChatAgent)
        self.token = "fake_token"
        self.channel_ids = [123, 456]

    def test_init_token_provided_uses_provided_token(self):
        bot = DiscordBot(self.chat_agent_mock, discord_token=self.token)
        self.assertEqual(bot.token, self.token)

    @patch('discord.Client')
    def test_on_ready(self, mock_client_class):
        # Setup a mock for the Client instance
        mock_client = MagicMock()
        user_mock = MagicMock()
        user_mock.__str__.return_value = 'BotUser'
        mock_client.user = user_mock

        # Ensure the mock client class returns the mock client instance
        mock_client_class.return_value = mock_client

        # Initialize the bot with the mocked client
        bot = DiscordBot(self.chat_agent_mock, discord_token=self.token)

        async def test():
            with patch('builtins.print') as mocked_print:
                await bot.on_ready()
                mocked_print.assert_called_with('We have logged in as BotUser')

        asyncio.run(test())

    @patch('discord.Client')
    def test_on_message_ignores_own_messages(self, mock_client_class):
        mock_client = MagicMock()
        mock_user = MagicMock()
        mock_client.user = mock_user

        mock_client_class.return_value = mock_client

        bot = DiscordBot(self.chat_agent_mock, discord_token=self.token)

        message_mock = MagicMock()
        message_mock.author = mock_user

        # Make the send method an async function
        message_mock.channel.send = AsyncMock()

        async def test():
            await bot.on_message(message_mock)
            message_mock.channel.send.assert_not_called()

        asyncio.run(test())

    @patch('discord.Client')
    def test_on_message_handles_channel_check(self, mock_client_class):
        mock_client = MagicMock()
        channel_ids = [123, 456]
        mock_client.user = MagicMock()

        mock_client_class.return_value = mock_client

        bot = DiscordBot(
            self.chat_agent_mock,
            channel_ids=channel_ids,
            discord_token=self.token,
        )

        message_mock = MagicMock()
        message_mock.channel.id = 789  # Not in channel_ids

        # Make the send method an async function
        message_mock.channel.send = AsyncMock()

        async def test():
            await bot.on_message(message_mock)
            message_mock.channel.send.assert_not_called()

        asyncio.run(test())

    @patch('discord.Client')
    def test_on_message_sends_response_when_mentioned(self, mock_client_class):
        mock_client = MagicMock()
        channel_ids = [123, 456]
        mock_client.user = MagicMock()

        mock_client_class.return_value = mock_client

        bot = DiscordBot(
            self.chat_agent_mock,
            channel_ids=channel_ids,
            discord_token=self.token,
        )

        message_mock = MagicMock()
        message_mock.channel.id = 123  # In channel_ids
        message_mock.content = "Hello, @bot!"
        message_mock.mentions = []  # Bot is not mentioned
        mock_client.user.mentioned_in = MagicMock(return_value=True)

        response_message = "Hello, human!"
        self.chat_agent_mock.step.return_value = MagicMock(
            msg=MagicMock(content=response_message)
        )
        # Make the send method an async function
        message_mock.channel.send = AsyncMock()

        async def test():
            await bot.on_message(message_mock)
            message_mock.channel.send.assert_called_once_with(response_message)

        asyncio.run(test())

    @patch('discord.Client')
    def test_on_message_ignores_when_not_mentioned(self, mock_client_class):
        mock_client = MagicMock()
        channel_ids = [123, 456]
        mock_client.user = MagicMock()

        mock_client_class.return_value = mock_client

        bot = DiscordBot(
            self.chat_agent_mock,
            channel_ids=channel_ids,
            discord_token=self.token,
        )

        message_mock = MagicMock()
        message_mock.channel.id = 123  # In channel_ids
        message_mock.content = "Hello, bot!"
        message_mock.mentions = []  # Bot is not mentioned
        mock_client.user.mentioned_in = MagicMock(return_value=False)

        response_message = "Hello, human!"
        self.chat_agent_mock.step.return_value = MagicMock(
            msg=MagicMock(content=response_message)
        )
        # Make the send method an async function
        message_mock.channel.send = AsyncMock()

        async def test():
            await bot.on_message(message_mock)
            message_mock.channel.send.assert_not_called()

        asyncio.run(test())


if __name__ == '__main__':
    unittest.main()
