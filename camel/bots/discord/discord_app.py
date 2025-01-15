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
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional

import discord
import httpx
from fastapi import FastAPI

from camel.bots.discord.discord_installation import DiscordInstallation
from camel.logger import get_logger
from camel.utils import api_keys_required, dependencies_required

from .discord_store import DiscordBaseInstallationStore

if TYPE_CHECKING:
    from discord import Message

logger = get_logger(__name__)

TOKEN_URL = "https://discord.com/api/oauth2/token"
USER_URL = "https://discord.com/api/users/@me"


class DiscordApp:
    r"""A class representing a Discord app that uses the `discord.py` library
    to interact with Discord servers.

    This bot can respond to messages in specific channels and only reacts to
    messages that mention the bot.

    Attributes:
        channel_ids (Optional[List[int]]): A list of allowed channel IDs. If
            provided, the bot will only respond to messages in these channels.
        token (Optional[str]): The Discord bot token used for authentication.
    """

    @dependencies_required('discord')
    @api_keys_required(
        [
            ("token", "DISCORD_BOT_TOKEN"),
        ]
    )
    def __init__(
        self,
        channel_ids: Optional[List[int]] = None,
        token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        installation_store: Optional[DiscordBaseInstallationStore] = None,
        intents: Optional[discord.Intents] = None,
    ) -> None:
        r"""Initialize the DiscordApp instance by setting up the Discord client
        and event handlers.

        Args:
            channel_ids (Optional[List[int]]): A list of allowed channel IDs.
                The bot will only respond to messages in these channels if
                provided. (default: :obj:`None`)
            token (Optional[str]): The Discord bot token for authentication.
                If not provided, the token will be retrieved from the
                environment variable `DISCORD_TOKEN`. (default: :obj:`None`)
            client_id (str, optional): The client ID for Discord OAuth.
                (default: :obj:`None`)
            client_secret (Optional[str]): The client secret for Discord OAuth.
                (default: :obj:`None`)
            redirect_uri (str): The redirect URI for OAuth callbacks.
                (default: :obj:`None`)
            installation_store (DiscordAsyncInstallationStore): The database
                stores all information of all installations.
                (default: :obj:`None`)
            intents (discord.Intents): The Discord intents of this app.
                (default: :obj:`None`)

        Raises:
            ValueError: If the `DISCORD_BOT_TOKEN` is not found in environment
                variables.
        """
        self.token = token or os.getenv("DISCORD_BOT_TOKEN")
        self.channel_ids = channel_ids
        self.installation_store = installation_store

        if not intents:
            intents = discord.Intents.all()
            intents.message_content = True
            intents.guilds = True

        self._client = discord.Client(intents=intents)

        # Register event handlers
        self._client.event(self.on_ready)
        self._client.event(self.on_message)

        # OAuth flow
        self.client_id = client_id or os.getenv("DISCORD_CLIENT_ID")
        self.client_secret = client_secret or os.getenv(
            "DISCORD_CLIENT_SECRET"
        )
        self.redirect_uri = redirect_uri

        self.oauth_flow = bool(
            self.client_id
            and self.client_secret
            and self.redirect_uri
            and self.installation_store
        )

        self.app = FastAPI()

    async def start(self):
        r"""Asynchronously start the Discord bot using its token.

        This method starts the bot and logs into Discord asynchronously using
        the provided token. It should be awaited when used in an async
        environment.
        """
        await self._client.start(self.token)

    def run(self) -> None:
        r"""Start the Discord bot using its token.

        This method starts the bot and logs into Discord synchronously using
        the provided token. It blocks execution and keeps the bot running.
        """
        self._client.run(self.token)  # type: ignore[arg-type]

    async def exchange_code_for_token_response(
        self, code: str
    ) -> Optional[str]:
        r"""Exchange the authorization code for an access token.

        Args:
            code (str): The authorization code received from Discord after
                user authorization.

        Returns:
            Optional[str]: The access token if successful, otherwise None.

        Raises:
            ValueError: If OAuth configuration is incomplete or invalid.
            httpx.RequestError: If there is a network issue during the request.
        """
        if not self.oauth_flow:
            logger.warning(
                "OAuth is not enabled. Missing client_id, "
                "client_secret, or redirect_uri."
            )
            return None
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    TOKEN_URL, data=data, headers=headers
                )
                if response.status_code != 200:
                    logger.error(f"Failed to exchange code: {response.text}")
                    return None
                response_data = response.json()

                return response_data
        except (httpx.RequestError, ValueError) as e:
            logger.error(f"Error during token fetch: {e}")
            return None

    async def get_user_info(self, access_token: str) -> Optional[dict]:
        r"""Retrieve user information using the access token.

        Args:
            access_token (str): The access token received from Discord.

        Returns:
            dict: The user information retrieved from Discord.
        """
        if not self.oauth_flow:
            logger.warning(
                "OAuth is not enabled. Missing client_id, "
                "client_secret, or redirect_uri."
            )
            return None
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            user_response = await client.get(USER_URL, headers=headers)
            return user_response.json()

    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        r"""Refresh the access token using a refresh token.

        Args:
            refresh_token (str): The refresh token issued by Discord that
                can be used to obtain a new access token.

        Returns:
            Optional[str]: The new access token if successful, otherwise None.
        """
        if not self.oauth_flow:
            logger.warning(
                "OAuth is not enabled. Missing client_id, "
                "client_secret, or redirect_uri."
            )
            return None
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with httpx.AsyncClient() as client:
            response = await client.post(TOKEN_URL, data=data, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to refresh token: {response.text}")
                return None
            response_data = response.json()
            return response_data.get("access_token")

    async def get_valid_access_token(self, guild_id: str) -> Optional[str]:
        r"""Retrieve a valid access token for the specified guild.

        This method attempts to retrieve an access token for a specific guild.
        If the current access token is expired, it will refresh the token using
        the refresh token.

        Args:
            guild_id (str): The ID of the guild to retrieve the access
                token for.

        Returns:
            Optional[str]: The valid access token if successful,
                otherwise None.
        """
        if not self.oauth_flow:
            logger.warning(
                "OAuth is not enabled. Missing client_id, "
                "client_secret, or redirect_uri."
            )
            return None
        assert self.installation_store is not None
        installation = await self.installation_store.find_by_guild(
            guild_id=guild_id
        )
        if not installation:
            logger.error(f"No installation found for guild: {guild_id}")
            return None

        if (
            installation.token_expires_at
            and datetime.now() >= installation.token_expires_at
        ):
            logger.info(
                f"Access token expired for guild: {guild_id}, "
                f"refreshing token..."
            )
            new_access_token = await self.refresh_access_token(
                installation.refresh_token
            )
            if new_access_token:
                installation.access_token = new_access_token
                installation.token_expires_at = datetime.now() + timedelta(
                    seconds=3600
                )
                await self.installation_store.save(installation)
                return new_access_token
            else:
                logger.error(
                    f"Failed to refresh access token for guild: {guild_id}"
                )
                return None

        return installation.access_token

    async def save_installation(
        self,
        guild_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ):
        r"""Save the installation information for a given guild.

        Args:
            guild_id (str): The ID of the guild where the bot is installed.
            access_token (str): The access token for the guild.
            refresh_token (str): The refresh token for the guild.
            expires_in: (int): The expiration time of the
                access token.
        """
        if not self.oauth_flow:
            logger.warning(
                "OAuth is not enabled. Missing client_id, "
                "client_secret, or redirect_uri."
            )
            return None
        assert self.installation_store is not None
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        installation = DiscordInstallation(
            guild_id=guild_id,
            access_token=access_token,
            refresh_token=refresh_token,
            installed_at=datetime.now(),
            token_expires_at=expires_at,
        )
        await self.installation_store.save(installation)
        logger.info(f"Installation saved for guild: {guild_id}")

    async def remove_installation(self, guild: discord.Guild):
        r"""Remove the installation for a given guild.

        Args:
            guild (discord.Guild): The guild from which the bot is
                being removed.
        """
        if not self.oauth_flow:
            logger.warning(
                "OAuth is not enabled. Missing client_id, "
                "client_secret, or redirect_uri."
            )
            return None
        assert self.installation_store is not None
        await self.installation_store.delete(guild_id=str(guild.id))
        print(f"Bot removed from guild: {guild.id}")

    async def on_ready(self) -> None:
        r"""Event handler that is called when the bot has successfully
        connected to the Discord server.

        When the bot is ready and logged into Discord, it prints a message
        displaying the bot's username.
        """
        logger.info(f'We have logged in as {self._client.user}')

    async def on_message(self, message: 'Message') -> None:
        r"""Event handler for processing incoming messages.

        This method is called whenever a new message is received by the bot. It
        will ignore messages sent by the bot itself, only respond to messages
        in allowed channels (if specified), and only to messages that mention
        the bot.

        Args:
            message (discord.Message): The message object received from
                Discord.
        """
        # If the message author is the bot itself,
        # do not respond to this message
        if message.author == self._client.user:
            return

        # If allowed channel IDs are provided,
        # only respond to messages in those channels
        if self.channel_ids and message.channel.id not in self.channel_ids:
            return

        # Only respond to messages that mention the bot
        if not self._client.user or not self._client.user.mentioned_in(
            message
        ):
            return

        logger.info(f"Received message: {message.content}")

    @property
    def client(self):
        return self._client
