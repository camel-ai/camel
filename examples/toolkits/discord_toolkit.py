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

import asyncio
import os
from typing import Any, Dict, List, Optional

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import DiscordToolkit
from camel.types import ModelPlatformType, ModelType


class DiscordAssistant:
    """A Discord assistant class using the CAMEL framework.

    This class provides a high-level interface for interacting with Discord
    using the CAMEL agent framework and the DiscordToolkit.
    """

    def __init__(
        self,
        bot_token: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        database_path: Optional[str] = None,
        model_temperature: float = 0.0,
    ):
        """Initialize the Discord assistant.

        Args:
            bot_token (str): The Discord bot token.
            client_id (Optional[str]): The client ID for Discord OAuth.
            client_secret (Optional[str]): The client secret for Discord OAuth.
            redirect_uri (Optional[str]): The redirect URI for OAuth callbacks.
            database_path (Optional[str]): Path to SQLite database for storing
                installations.
            model_temperature (float): Temperature parameter for the model.
        """
        # Create Discord toolkit
        self.discord_toolkit = DiscordToolkit(
            bot_token=bot_token,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            database_path=database_path,
        )
        self.tools = self.discord_toolkit.get_tools()

        # Set up model configuration
        sys_msg = """You are a professional Discord assistant that 
        can help users manage and interact with Discord servers.
        You can send messages, retrieve channel information,
        manage members, and add emoji reactions."""

        model_config_dict = ChatGPTConfig(
            temperature=model_temperature,
        ).as_dict()

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict=model_config_dict,
        )

        # Set up agent
        self.camel_agent = ChatAgent(
            system_message=sys_msg,
            model=model,
            tools=self.tools,
        )
        self.camel_agent.reset()

    async def setup(self) -> bool:
        """Set up and connect to Discord.

        Returns:
            bool: Whether the connection was successful.
        """
        return await self.discord_toolkit.start_bot()

    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process a user query using the CAMEL agent.

        Args:
            query (str): The user query to process.

        Returns:
            Dict[str, Any]: The processing result.
        """
        # Use astep to asynchronously process the query
        response = await self.camel_agent.astep(query)
        return {
            'response': response.content,
            'tool_calls': response.info.get('tool_calls', []),
        }

    async def list_channels(self, guild_id: str) -> List[Dict[str, Any]]:
        """List all channels in a guild.

        Args:
            guild_id (str): The Discord guild ID.

        Returns:
            List[Dict[str, Any]]: The list of channels.
        """
        result = await self.process_query(
            f"Get all channels in guild {guild_id}"
        )
        return result.get('tool_calls', [])

    async def send_channel_message(
        self, channel_id: str, message: str
    ) -> Dict[str, Any]:
        """Send a message to a channel.

        Args:
            channel_id (str): The Discord channel ID.
            message (str): The message content.

        Returns:
            Dict[str, Any]: The result of sending the message.
        """
        result = await self.process_query(
            f"Send message to channel {channel_id}: {message}"
        )
        return result

    async def get_recent_messages(
        self, channel_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent messages from a channel.

        Args:
            channel_id (str): The Discord channel ID.
            limit (int): The maximum number of messages to retrieve.

        Returns:
            List[Dict[str, Any]]: The list of messages.
        """
        result = await self.process_query(
            f"Get the {limit} most recent messages from channel {channel_id}"
        )
        return result.get('tool_calls', [])

    def shutdown(self) -> bool:
        """Shut down the Discord assistant.

        Returns:
            bool: Whether the shutdown was successful.
        """
        return self.discord_toolkit.stop_bot()


async def main():
    """Main function demonstrating the Discord assistant usage."""
    # Get Discord bot token from environment variable
    discord_token = os.environ.get(
        "DISCORD_BOT_TOKEN", "your_discord_bot_token"
    )
    client_id = os.environ.get("DISCORD_CLIENT_ID")
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET")
    redirect_uri = os.environ.get("DISCORD_REDIRECT_URI")
    database_path = os.environ.get(
        "DISCORD_DB_PATH", "discord_installations.db"
    )

    # Initialize Discord assistant
    assistant = DiscordAssistant(
        bot_token=discord_token,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        database_path=database_path,
    )

    # Set up and connect to Discord
    connected = await assistant.setup()
    if not connected:
        print(
            """Failed to connect to Discord. 
            Please check if your token is valid."""
        )
        return

    try:
        # Example 1: List channels in a guild
        guild_id = os.environ.get("DISCORD_GUILD_ID", "your_guild_id")
        print(f"Getting channels for guild {guild_id}...")
        channels_result = await assistant.list_channels(guild_id)
        print(f"Channels: {channels_result}")

        # Example 2: Send a message to a channel
        channel_id = os.environ.get("DISCORD_CHANNEL_ID", "your_channel_id")
        message = "Hello! I'm a Discord assistant powered by CAMEL-AI."
        print(f"Sending message to channel {channel_id}...")
        message_result = await assistant.send_channel_message(
            channel_id, message
        )
        print(f"Message result: {message_result}")

        # Example 3: Get recent messages
        print(f"Getting recent messages from channel {channel_id}...")
        messages_result = await assistant.get_recent_messages(channel_id, 5)
        print(f"Recent messages: {messages_result}")

        # Example 4: Use a custom query with astep
        custom_query = (
            f"Create a text channel named 'camel-ai-chat' in guild {guild_id},"
            "then send a welcome message to the new channel"
        )
        print("Executing custom query...")
        custom_result = await assistant.process_query(custom_query)
        print(f"Custom query result: {custom_result}")

        # Example 5: Direct use of astep
        print("Using astep directly to add a reaction...")
        message_id = os.environ.get("DISCORD_MESSAGE_ID", "your_message_id")
        reaction_query = (
            f"Add a '👍' reaction to message {message_id}"
            "in channel {channel_id}"
        )
        reaction_result = await assistant.camel_agent.astep(reaction_query)
        print(f"Reaction result: {reaction_result.content}")

    finally:
        # Shut down
        assistant.shutdown()
        print("Disconnected from Discord")


if __name__ == "__main__":
    asyncio.run(main())
