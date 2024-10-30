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
import logging
import os
import httpx
import uvicorn
from typing import TYPE_CHECKING, List, Optional
from camel.utils import dependencies_required
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse

if TYPE_CHECKING:
    from discord import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/callback"
TOKEN_URL = "https://discord.com/api/oauth2/token"
USER_URL = "https://discord.com/api/users/@me"

class DiscordOAuth:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_oauth_url(self) -> str:
        return (
            f"https://discord.com/api/oauth2/authorize?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}&response_type=code&scope=identify%20guilds"
        )

    async def exchange_code_for_token(self, code: str) -> Optional[str]:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with httpx.AsyncClient() as client:
            response = await client.post(TOKEN_URL, data=data, headers=headers)
            response_data = response.json()
            return response_data.get("access_token")

    async def get_user_info(self, access_token: str) -> dict:
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            user_response = await client.get(USER_URL, headers=headers)
            return user_response.json()

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
    def __init__(
        self,
        channel_ids: Optional[List[int]] = None,
        token: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: str = "http://localhost:8000/callback",
    ) -> None:
        r"""Initialize the DiscordApp instance by setting up the Discord client
        and event handlers.

        Args:
            channel_ids (Optional[List[int]]): A list of allowed channel IDs.
                The bot will only respond to messages in these channels if
                provided.
            token (Optional[str]): The Discord bot token for authentication.
                If not provided, the token will be retrieved from the
                environment variable `DISCORD_TOKEN`.
            client_id (Optional[str]): The client ID for Discord OAuth.
            client_secret (Optional[str]): The client secret for Discord OAuth.
            redirect_uri (str): The redirect URI for OAuth callbacks.

        Raises:
            ValueError: If the `DISCORD_TOKEN` is not found in environment
                variables.
        """
        self.token = token or os.getenv('DISCORD_TOKEN')
        self.channel_ids = channel_ids

        if not self.token:
            raise ValueError(
                "`DISCORD_TOKEN` not found in environment variables. Get it"
                " here: `https://discord.com/developers/applications`."
            )

        import discord

        intents = discord.Intents.default()
        intents.message_content = True
        self._client = discord.Client(intents=intents)

        # Register event handlers
        self._client.event(self.on_ready)
        self._client.event(self.on_message)

        # OAuth flow
        client_id = client_id or CLIENT_ID
        client_secret = client_secret or CLIENT_SECRET
        if not all([client_id, client_secret]):
            raise ValueError(
                "DISCORD_CLIENT_ID and DISCORD_CLIENT_SECRET must be set for OAuth."
            )
        self.oauth_client = DiscordOAuth(client_id, client_secret, redirect_uri)

        self.app = FastAPI()
        self.app.get("/")(self.home)
        self.app.get("/callback")(self.callback)
        self.server = None

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

    def initiate_oauth_flow(self) -> str:
        r"""Start the OAuth Server and initiate the OAuth flow by generating
            the authorization URL.

        Returns:
            str: The URL that users should visit to authorize the application.
        """
        asyncio.create_task(self.run_oauth_server())
        return self.oauth_client.get_oauth_url()

    @property
    def client(self):
        return self._client

    async def home(self):
        r"""Redirect the user to the Discord OAuth URL.

        Returns:
            RedirectResponse: A response that redirects the user to the Discord OAuth authorization page.
        """
        oauth_url = self.oauth_client.get_oauth_url()
        return RedirectResponse(oauth_url)

    async def callback(self, code: str, state: Optional[str] = None):
        r"""Endpoint to handle the OAuth callback from Discord.

        Args:
            code (str): The authorization code from Discord.
            state (Optional[str]): Optional state parameter for custom business data.

        Returns:
            dict: The user information if successful, otherwise an error message.
        """
        if not code:
            raise HTTPException(status_code=400, detail="No code returned")
        if state:
            logger.info(f"Received state: {state}")

        access_token = await self.oauth_client.exchange_code_for_token(code)
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")

        user_data = await self.oauth_client.get_user_info(access_token)
        logger.info(f"User data: {user_data}")
        await self.shutdown_oauth_server()
        return user_data

    async def run_oauth_server(self, host="127.0.0.1", port=8000):
        r"""Starts the OAuth server for handling the Discord OAuth flow.

        This method initializes and runs a FastAPI server configured with the provided host and port.
        It listens for incoming OAuth callbacks from Discord, allowing users to complete the OAuth authorization.

        Args:
            host (str): The hostname on which the OAuth server should run. Defaults to "127.0.0.1".
            port (int): The port on which the OAuth server should run. Defaults to 8000.

        Raises:
            Exception: If the server fails to start due to configuration issues or binding conflicts.
        """
        try:
            config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
            self.server = uvicorn.Server(config)
            await self.server.serve()
        except Exception as e:
            logger.error(f"Failed to start OAuth server: {e}")

    async def shutdown_oauth_server(self):
        r"""Gracefully shuts down the OAuth server after the authorization flow is complete.

        This method checks if the server is running and sets the `should_exit` flag to True,
        allowing the Uvicorn server to shut down gracefully. It is typically called after
        handling the OAuth callback to release resources and prevent the server from continuing to listen.

        Returns:
            None
        """
        if self.server and self.server.should_exit is False:
            self.server.should_exit = True
            logger.info("Shutting down the OAuth server.")