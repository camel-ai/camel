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
from asyncio import AbstractEventLoop, Task
from typing import Any, Dict, List, Optional

from camel.bots.discord import (
    DiscordApp,
    DiscordBaseInstallationStore,
    DiscordSQLiteInstallationStore,
)
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer


@MCPServer()
class DiscordToolkit(BaseToolkit):
    r"""A toolkit for interacting with Discord servers using the Discord API.

    This toolkit provides functionality for sending messages,
    retrieving channel information, managing guild members,
    and handling Discord application installations.

    Attributes:
        bot_token (str): The Discord bot token used for authentication.
        client_id (Optional[str]): The client ID for Discord OAuth.
        client_secret (Optional[str]): The client secret for Discord OAuth.
        redirect_uri (Optional[str]): The redirect URI for OAuth callbacks.
        installation_store (Optional[DiscordBaseInstallationStore]):
            The store for managing Discord installations.
        discord_app (DiscordApp): The Discord application instance.
    """

    def __init__(
        self,
        bot_token: str,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        installation_store: Optional[DiscordBaseInstallationStore] = None,
        database_path: Optional[str] = None,
        channel_ids: Optional[List[int]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the DiscordToolkit.

        Args:
            bot_token (str): The Discord bot token used for authentication.
            client_id (Optional[str]): The client ID for Discord OAuth.
                (default: :obj:`None`)
            client_secret (Optional[str]): The client secret for Discord OAuth.
                (default: :obj:`None`)
            redirect_uri (Optional[str]): The redirect URI for OAuth callbacks.
                (default: :obj:`None`)
            installation_store (Optional[DiscordBaseInstallationStore]):
                The store for managing Discord installations.
                If None and database_path is provided,
                a SQLite store will be created.
                (default: :obj:`None`)
            database_path (Optional[str]): Path to SQLite database for storing
                installations. (default: :obj:`None`)
            channel_ids (Optional[List[int]]): List of Discord channel IDs
                to monitor.
                (default: :obj:`None`)
            timeout (Optional[float]): The timeout for toolkit operations.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        import discord

        # Create installation store if database path is provided
        if installation_store is None and database_path is not None:
            installation_store = DiscordSQLiteInstallationStore(database_path)

        # Initialize Discord app
        self.bot_token = bot_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.installation_store = installation_store

        # Create intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        # Initialize Discord app
        self.discord_app = DiscordApp(
            token=bot_token,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            installation_store=installation_store,
            channel_ids=channel_ids,
            intents=intents,
        )

        self._is_running = False
        self._event_loop: Optional[AbstractEventLoop] = None
        self._background_task: Optional[Task[Any]] = None

    async def start_bot(self) -> bool:
        r"""Start the Discord bot.

        Returns:
            bool: True if the bot was started successfully, False otherwise.
        """
        if not self._is_running:
            try:
                # Initialize installation store if available
                if self.installation_store:
                    await self.installation_store.init()

                # Start the bot in a background task
                self._event_loop = asyncio.get_event_loop()
                self._background_task = asyncio.create_task(
                    self.discord_app.start()
                )
                self._is_running = True
                return True
            except Exception as e:
                print(f"Failed to start Discord bot: {e!s}")
                return False
        return True

    async def send_message(
        self, channel_id: str, content: str
    ) -> Dict[str, Any]:
        r"""Send a message to a Discord channel.

        Args:
            channel_id (str): The ID of the channel to send the message to.
            content (str): The content of the message to send.

        Returns:
            Dict[str, Any]: Information about the sent message or an error.
        """
        if not self._is_running:
            await self.start_bot()

        try:
            channel = await self.discord_app.client.fetch_channel(
                int(channel_id)
            )
            message = await channel.send(content)

            return {
                'id': str(message.id),
                'content': message.content,
                'channel_id': str(message.channel.id),
                'timestamp': str(message.created_at),
            }
        except Exception as e:
            return {'error': str(e)}

    async def get_channel_messages(
        self, channel_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        r"""Retrieve messages from a Discord channel.

        Args:
            channel_id (str): The ID of the channel to retrieve messages from.
            limit (int): The maximum number of messages to retrieve.
                (default: :obj:`100`)

        Returns:
            List[Dict[str, Any]]: A list of messages or an error.
        """
        if not self._is_running:
            await self.start_bot()

        try:
            channel = await self.discord_app.client.fetch_channel(
                int(channel_id)
            )
            messages = [msg async for msg in channel.history(limit=limit)]

            return [
                {
                    'id': str(msg.id),
                    'content': msg.content,
                    'author': str(msg.author),
                    'author_id': str(msg.author.id),
                    'timestamp': str(msg.created_at),
                }
                for msg in messages
            ]
        except Exception as e:
            return [{'error': str(e)}]

    async def get_guild_channels(self, guild_id: str) -> List[Dict[str, Any]]:
        r"""Retrieve channels from a Discord guild.

        Args:
            guild_id (str): The ID of the guild to retrieve channels from.

        Returns:
            List[Dict[str, Any]]: A list of channels or an error.
        """
        if not self._is_running:
            await self.start_bot()

        try:
            guild = await self.discord_app.client.fetch_guild(int(guild_id))
            channels = await guild.fetch_channels()

            return [
                {
                    'id': str(channel.id),
                    'name': channel.name,
                    'type': str(channel.type),
                    'position': channel.position,
                }
                for channel in channels
            ]
        except Exception as e:
            return [{'error': str(e)}]

    async def get_guild_members(
        self, guild_id: str, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        r"""Retrieve members from a Discord guild.

        Args:
            guild_id (str): The ID of the guild to retrieve members from.
            limit (int): The maximum number of members to retrieve.
                (default: :obj:`1000`)

        Returns:
            List[Dict[str, Any]]: A list of members or an error.
        """
        if not self._is_running:
            await self.start_bot()

        try:
            guild = await self.discord_app.client.fetch_guild(int(guild_id))
            members = [
                member async for member in guild.fetch_members(limit=limit)
            ]

            return [
                {
                    'id': str(member.id),
                    'name': member.name,
                    'display_name': member.display_name,
                    'joined_at': str(member.joined_at),
                    'roles': [str(role.name) for role in member.roles],
                }
                for member in members
            ]
        except Exception as e:
            return [{'error': str(e)}]

    async def add_reaction(
        self, channel_id: str, message_id: str, emoji: str
    ) -> Dict[str, Any]:
        r"""Add a reaction to a Discord message.

        Args:
            channel_id (str): The ID of the channel containing the message.
            message_id (str): The ID of the message to add a reaction to.
            emoji (str): The emoji to add as a reaction.

        Returns:
            Dict[str, Any]: Information about the reaction or an error.
        """
        if not self._is_running:
            await self.start_bot()

        try:
            channel = await self.discord_app.client.fetch_channel(
                int(channel_id)
            )
            message = await channel.fetch_message(int(message_id))
            await message.add_reaction(emoji)
            return {'success': True, 'message_id': message_id, 'emoji': emoji}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def create_channel(
        self,
        guild_id: str,
        name: str,
        channel_type: str = "text",
        category_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Create a new channel in a Discord guild.

        Args:
            guild_id (str): The ID of the guild to create the channel in.
            name (str): The name of the channel to create.
            channel_type (str): The type of channel to
                create ("text", "voice", "category").
                (default: :obj:`"text"`)
            category_id (Optional[str]): The ID of the category to
                 place the channel in.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: Information about the created channel or an error.
        """
        if not self._is_running:
            await self.start_bot()

        try:
            import discord

            guild = await self.discord_app.client.fetch_guild(int(guild_id))

            type_map = {
                "text": discord.ChannelType.text,
                "voice": discord.ChannelType.voice,
                "category": discord.ChannelType.category,
            }

            kwargs = {
                "type": type_map.get(
                    channel_type.lower(), discord.ChannelType.text
                )
            }
            if category_id:
                kwargs[
                    "category"
                ] = await self.discord_app.client.fetch_channel(
                    int(category_id)
                )

            channel = await guild.create_channel(name, **kwargs)

            return {
                'id': str(channel.id),
                'name': channel.name,
                'type': str(channel.type),
                'created_at': str(channel.created_at),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def install_app(self, code: str) -> Dict[str, Any]:
        r"""Install the Discord application using an authorization code.

        Args:
            code (str): The authorization code from the OAuth flow.

        Returns:
            Dict[str, Any]: Information about the installation or an error.
        """
        if not self._is_running:
            await self.start_bot()

        try:
            # Exchange code for token
            token_response = (
                await self.discord_app.exchange_code_for_token_response(code)
            )
            if not token_response:
                return {
                    'success': False,
                    'error': 'Failed to exchange code for token',
                }

            # Get user info
            access_token = ""
            if (
                isinstance(token_response, dict)
                and "access_token" in token_response
            ):
                access_token = token_response["access_token"]

            user_info = await self.discord_app.get_user_info(access_token)
            if not user_info:
                return {'success': False, 'error': 'Failed to get user info'}

            # Create installation
            guild_id = ""
            refresh_token = ""
            expires_in = 604800  # Default to 7 days

            if isinstance(user_info, dict) and "id" in user_info:
                guild_id = str(user_info["id"])

            if isinstance(token_response, dict):
                if "refresh_token" in token_response:
                    refresh_token = str(token_response["refresh_token"])
                if "expires_in" in token_response:
                    expires_in = int(token_response["expires_in"])

            await self.discord_app.save_installation(
                guild_id, access_token, refresh_token, expires_in
            )

            return {
                'success': True,
                'guild_id': guild_id,
                'user_info': user_info,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def refresh_token(self, guild_id: str) -> Dict[str, Any]:
        r"""Refresh the access token for a Discord installation.

        Args:
            guild_id (str): The ID of the guild to refresh the token for.

        Returns:
            Dict[str, Any]: Information about
                the refresh operation or an error.
        """
        if not self._is_running:
            await self.start_bot()

        try:
            # Get installation
            if self.installation_store is None:
                return {
                    'success': False,
                    'error': 'No installation store configured',
                }

            installation = await self.installation_store.find_by_guild(
                guild_id
            )
            if not installation:
                return {'success': False, 'error': 'Installation not found'}

            # Refresh token
            new_token = await self.discord_app.refresh_access_token(
                installation.refresh_token
            )
            if not new_token:
                return {'success': False, 'error': 'Failed to refresh token'}

            return {'success': True, 'token': new_token}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def stop_bot(self) -> bool:
        r"""Stop the Discord bot.

        Returns:
            bool: True if the bot was stopped successfully, False otherwise.
        """
        if self._is_running and self.discord_app.client:
            try:
                if self._event_loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        self.discord_app.client.close(), self._event_loop
                    )
                self._is_running = False
                return True
            except Exception as e:
                print(f"Failed to stop Discord bot: {e!s}")
                return False
        return False

    def get_tools(self) -> List[FunctionTool]:
        r"""Get the list of tools provided by this toolkit.

        Returns:
            List[FunctionTool]: A list of function tools.
        """
        return [
            FunctionTool(self.start_bot),
            FunctionTool(self.send_message),
            FunctionTool(self.get_channel_messages),
            FunctionTool(self.get_guild_channels),
            FunctionTool(self.get_guild_members),
            FunctionTool(self.add_reaction),
            FunctionTool(self.create_channel),
            FunctionTool(self.install_app),
            FunctionTool(self.refresh_token),
            FunctionTool(self.stop_bot),
        ]
