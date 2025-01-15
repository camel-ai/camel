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
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from camel.bots import DiscordApp


class TestDiscordApp(unittest.TestCase):
    def setUp(self):
        # Set environment variables to simulate the token
        os.environ['DISCORD_BOT_TOKEN'] = 'fake_token'

    def tearDown(self):
        # Clear the environment variable after the test
        if 'DISCORD_BOT_TOKEN' in os.environ:
            del os.environ['DISCORD_BOT_TOKEN']

    @patch('discord.Client')
    def test_init_with_token_from_env(self, mock_discord_client):
        # Initialize DiscordApp using the token from environment variables
        app = DiscordApp()
        self.assertEqual(app.token, 'fake_token')
        self.assertIsNotNone(app.client)
        mock_discord_client.assert_called_once()

    @patch('discord.Client')
    def test_init_with_provided_token(self, mock_discord_client):
        # Initialize DiscordApp with a provided token
        app = DiscordApp(token='custom_token')
        self.assertEqual(app.token, 'custom_token')
        mock_discord_client.assert_called_once()

    @patch('discord.Client')
    def test_init_raises_value_error_without_token(self, mock_discord_client):
        # Test that ValueError is raised if no token is set
        del os.environ['DISCORD_BOT_TOKEN']  # Remove the environment variable
        with self.assertRaises(ValueError):
            DiscordApp()

    @patch('discord.Client')
    async def test_on_ready(self, mock_discord_client):
        # Test the on_ready event handler
        mock_discord_client.user = MagicMock(name='TestBot')
        app = DiscordApp()

        with patch('camel.bots.discord_app.logger') as mock_logger:
            await app.on_ready()
            mock_logger.info.assert_called_once_with(
                f'We have logged in as {mock_discord_client.user}'
            )

    @patch('discord.Client')
    async def test_on_message_ignore_own_message(self, mock_discord_client):
        # Test that on_message ignores messages from the bot itself
        app = DiscordApp()
        mock_message = MagicMock()
        mock_message.author = mock_discord_client.user

        await app.on_message(mock_message)
        mock_message.channel.send.assert_not_called()

    @patch('discord.Client')
    async def test_on_message_respond_in_allowed_channel(
        self, mock_discord_client
    ):
        # Test that on_message responds in allowed channels
        app = DiscordApp(channel_ids=[123])
        mock_message = MagicMock()
        mock_message.author = MagicMock()
        mock_message.channel.id = 123  # Allowed channel
        mock_discord_client.user.mentioned_in.return_value = True

        with patch('camel.bots.discord_app.logger') as mock_logger:
            await app.on_message(mock_message)
            mock_logger.info.assert_called_once_with(
                f"Received message: {mock_message.content}"
            )

    @patch('discord.Client')
    async def test_on_message_ignore_non_mentioned_message(
        self, mock_discord_client
    ):
        # Test that on_message ignores messages that don't mention the bot
        app = DiscordApp(channel_ids=[123])
        mock_message = MagicMock()
        mock_message.author = MagicMock()
        mock_message.channel.id = 123
        mock_discord_client.user.mentioned_in.return_value = False

        await app.on_message(mock_message)
        mock_message.channel.send.assert_not_called()

    @patch('discord.Client')
    async def test_on_message_ignore_outside_channel(
        self, mock_discord_client
    ):
        # Test that on_message ignores messages outside the allowed channels
        app = DiscordApp(channel_ids=[123])
        mock_message = MagicMock()
        mock_message.author = MagicMock()
        mock_message.channel.id = 456  # Not in allowed channels

        await app.on_message(mock_message)
        mock_message.channel.send.assert_not_called()

    @patch('discord.Client')
    async def test_start_bot(self, mock_discord_client):
        # Test that the start method calls the correct start function
        app = DiscordApp()
        app._client.start = AsyncMock()

        await app.start()
        app._client.start.assert_called_once_with('fake_token')

    @patch('discord.Client')
    def test_run_bot(self, mock_discord_client):
        # Test that the run method calls the correct synchronous start function
        app = DiscordApp()
        app._client.run = MagicMock()

        app.run()
        app._client.run.assert_called_once_with('fake_token')


if __name__ == '__main__':
    unittest.main()
