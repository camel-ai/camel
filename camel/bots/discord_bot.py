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
import os
from typing import List, Optional

from camel.agents import ChatAgent
from camel.messages import BaseMessage


class DiscordBot:
    r"""Represents a Discord bot that is powered by an agent.

    Attributes:
        client (discord.Client): The Discord client.
        chat_agent (ChatAgent): Chat agent that will power the bot.
        channel_ids (List[int], optional): The channel IDs that the bot will listen to.
        discord_token (str, optional): The bot token.
    """

    def __init__(
        self,
        chat_agent: ChatAgent,
        channel_ids: Optional[List[int]] = None,
        discord_token: Optional[str] = None,
    ) -> None:
        self.chat_agent = chat_agent

        if not discord_token:
            self.token = os.getenv('DISCORD_TOKEN')
            if not self.token:
                raise ValueError(
                    "`DISCORD_TOKEN` not found in environment variables. Get it here: `https://discord.com/developers/applications`."
                )
        else:
            self.token = discord_token

        self.channel_ids = channel_ids

        try:
            import discord
        except ImportError:
            raise ImportError(
                "Please install `discord` first. You can install it by running "
                "`python3 -m pip install -U discord.py`."
            )
        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)

        # Register event handlers
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

    def run(self):
        """Start the Discord bot using its token.

        This method starts the Discord bot by running the client with the provided token.
        """
        self.client.run(self.token)

    async def on_ready(self):
        """
        This method is called when the bot has successfully connected to the Discord server.
        It prints a message indicating that the bot has logged in and displays the username of the bot.
        """
        print(f'We have logged in as {self.client.user}')

    async def on_message(self, message):
        """
        Event handler for when a message is received.

        Parameters:
        - message (discord.Message): The message object received.

        Returns:
        - None

        """
        if message.author == self.client.user:
            return

        if self.channel_ids is not None:
            if message.channel.id not in self.channel_ids:
                return

        if not self.client.user.mentioned_in(message):
            return

        self.chat_agent.reset()

        user_msg = BaseMessage.make_user_message(
            role_name="User", content=message.content
        )
        assistant_response = self.chat_agent.step(user_msg)
        await message.channel.send(assistant_response.msg.content)
