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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from camel.agents import ChatAgent
from camel.bots.discord import (
    DiscordApp,
    DiscordBaseInstallationStore,
    DiscordSQLiteInstallationStore,
)
from camel.logger import get_logger
from camel.retrievers import AutoRetriever
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

# For type annotations only
if TYPE_CHECKING:
    from unstructured.documents.elements import Element
else:
    try:
        from unstructured.documents.elements import Element
    except ImportError:
        pass


logger = get_logger(__name__)


@MCPServer()
class DiscordToolkit(BaseToolkit):
    r"""A toolkit for creating and managing Discord bots.

    This toolkit provides functionality to create, configure,
    and run Discord botsthat can process messages, interact with users,
    and leverage retrieval-augmented generation for providing
    informative responses using the CAMEL Discord bot implementation.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        channel_ids: Optional[List[int]] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        installation_store: Optional[DiscordBaseInstallationStore] = None,
        database_path: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the DiscordToolkit.

        Args:
            token (Optional[str]): The Discord bot token for authentication.
                If None, it must be provided when calling create_bot.
            channel_ids (Optional[List[int]]): List of Discord channel IDs
                where the bot is allowed to interact. If None, the bot will
                respond in any channel when mentioned.
            client_id (Optional[str]): The client ID for Discord OAuth.
                Required for OAuth flow.
            client_secret (Optional[str]): The client secret for Discord OAuth.
                Required for OAuth flow.
            redirect_uri (Optional[str]): The redirect URI for OAuth callbacks.
                Required for OAuth flow.
            installation_store (Optional[DiscordBaseInstallationStore]): The
                database to store installation information. If None and
                database_path is provided, a SQLite store will be created.
            database_path (Optional[str]): Path to SQLite database for
                installation storage. Only used if installation_store is None.
            timeout (Optional[float]): The timeout for the toolkit operations.
        """
        super().__init__(timeout=timeout)

        # Create installation store if database path is provided
        if installation_store is None and database_path is not None:
            installation_store = DiscordSQLiteInstallationStore(database_path)

        # Initialize Discord app
        self._discord_app = DiscordApp(
            channel_ids=channel_ids,
            token=token,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            installation_store=installation_store,
        )

        self._agent_instance: Optional[Dict[str, Any]] = None

    def create_agent(
        self,
        contents: Optional[
            Union[str, List[str], "Element", List["Element"]]
        ] = None,
        auto_retriever: Optional[AutoRetriever] = None,
        similarity_threshold: float = 0.5,
        vector_storage_local_path: str = "local_data/",
        top_k: int = 1,
        return_detailed_info: bool = True,
        system_message: Optional[str] = None,
    ) -> str:
        r"""Create a bot agent for processing messages and generating responses

        Args:
            contents (Union[str, List[str], Element, List[Element]], optional):
                The content to be retrieved.
            auto_retriever (Optional[AutoRetriever], optional): An instance of
                AutoRetriever for vector search.
            similarity_threshold (float): Threshold for vector similarity when
                retrieving content.
            vector_storage_local_path (str): Path to local vector storage for
                the retriever.
            top_k (int): Number of top results to retrieve.
            return_detailed_info (bool): Whether to return detailed
                information from the retriever.
            system_message (Optional[str]): Custom system message for the agent
                If None, a default customer service message will be used.

        Returns:
            str: A message indicating the agent was created successfully.
        """
        if system_message is None:
            system_message = '''
                Objective: 
                    You are a customer service bot designed to assist users
                    with inquiries related to our open-source project. 
                    Your responses should be informative, concise, and helpful.

                Instructions:
                    Understand User Queries: Carefully read and understand the
                            user's question. Focus on keywords and context to
                            determine the user's intent.
                    Search for Relevant Information: Use the provided dataset
                            and refer to the RAG (file to find answers that 
                            closely match the user's query. The RAG file 
                            contains detailed interactions and should be your 
                            primary resource for crafting responses.
                    Provide Clear and Concise Responses: Your answers should 
                            be clear and to the point. Avoid overly technical
                            language unless the user's query indicates 
                            familiarity with technical terms.
                    Encourage Engagement: Where applicable, encourage users
                            to contribute to the project or seek further
                            assistance.

                Response Structure:
                    Greeting: Begin with a polite greeting or acknowledgment.
                    Main Response: Provide the main answer to the user's query.
                    Additional Information: Offer any extra tips or direct the
                            user to additional resources if necessary.
                    Closing: Close the response politely, encouraging
                            further engagement if appropriate.

                Tone:
                    Professional: Maintain a professional tone that 
                            instills confidence in the user.
                    Friendly: Be approachable and personable to create
                            a positive interaction.
                    Helpful: Always aim to be as helpful as possible,
                            even when faced with challenging queries.
            '''

        # Create the agent instance
        agent = ChatAgent(system_message)

        # Store agent properties
        self._agent_instance = {
            "agent": agent,
            "contents": contents,
            "auto_retriever": auto_retriever,
            "similarity_threshold": similarity_threshold,
            "vector_storage_local_path": vector_storage_local_path,
            "top_k": top_k,
            "return_detailed_info": return_detailed_info,
        }

        logger.info("Bot agent created successfully")
        return "Bot agent created successfully"

    async def _process_message(self, message: str) -> str:
        r"""Process the user message, retrieve relevant content, and generate
        a response.

        Args:
            message (str): The user's query message.

        Returns:
            str: The assistant's response message.
        """
        if not self._agent_instance:
            raise ValueError("Bot agent not created. Call create_agent first.")

        agent = self._agent_instance["agent"]
        auto_retriever = self._agent_instance["auto_retriever"]
        contents = self._agent_instance["contents"]
        top_k = self._agent_instance["top_k"]
        similarity_threshold = self._agent_instance["similarity_threshold"]
        return_detailed_info = self._agent_instance["return_detailed_info"]

        user_raw_msg = message
        logger.info(f"Processing user message: {user_raw_msg}")

        if auto_retriever:
            retrieved_content = auto_retriever.run_vector_retriever(
                query=user_raw_msg,
                contents=contents,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                return_detailed_info=return_detailed_info,
            )
            user_raw_msg = (
                f"Here is the query to you: {user_raw_msg}\n"
                f"Based on the retrieved content: {retrieved_content}, \n"
                f"answer the query"
            )

        assistant_response = agent.step(user_raw_msg)
        return assistant_response.msg.content

    def process_message(self, message: str) -> str:
        r"""Process a message and generate a response using the bot agent.

        Args:
            message (str): The user's message to process.

        Returns:
            str: The assistant's response message.
        """
        if not self._agent_instance:
            raise ValueError("Bot agent not created. Call create_agent first.")

        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(self._process_message(message))
        finally:
            loop.close()

        return response

    def create_bot(
        self,
        token: Optional[str] = None,
        channel_ids: Optional[List[int]] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        installation_store: Optional[DiscordBaseInstallationStore] = None,
    ) -> str:
        r"""Create a Discord bot instance using
          the existing DiscordApp implementation.

        Args:
            token (Optional[str]): The Discord bot token for authentication.
                If None, uses the token provided during initialization.
            channel_ids (Optional[List[int]]): List of Discord channel IDs
                where the bot is allowed to interact. If None, uses the
                channel_ids provided during initialization.
            client_id (Optional[str]): The client ID for Discord OAuth.
                Required for OAuth flow.
            client_secret (Optional[str]): The client secret for Discord OAuth.
                Required for OAuth flow.
            redirect_uri (Optional[str]): The redirect URI for OAuth callbacks.
                Required for OAuth flow.
            installation_store (Optional[DiscordBaseInstallationStore]): The
                database to store installation information.

        Returns:
            str: A message indicating the bot was created successfully.
        """
        if not self._agent_instance:
            return "Error: Bot agent not created. Call create_agent first."

        # Update the Discord app with any new parameters
        if token is not None:
            self._discord_app.token = token

        if channel_ids is not None:
            self._discord_app.channel_ids = channel_ids

        # Set up the custom message handler to use our agent
        async def custom_on_message(message):
            # The default behavior from DiscordApp.on_message will be preserved
            # (checking for bot messages, channel IDs, and mentions)
            # If the message author is the bot itself, do not respond
            if message.author == self._discord_app.client.user:
                return

            # If allowed channel IDs are provided,
            # only respond in those channels
            if (
                self._discord_app.channel_ids
                and message.channel.id not in self._discord_app.channel_ids
            ):
                return

            # Only respond to messages that mention the bot
            if (
                not self._discord_app.client.user
                or not self._discord_app.client.user.mentioned_in(message)
            ):
                return

            # Process the message using our agent
            user_raw_msg = message.content
            response = await self._process_message(user_raw_msg)
            await message.channel.send(response)

        # Override the on_message handler with our custom one
        self._discord_app._client.event(custom_on_message)

        logger.info("Discord bot created successfully")
        return "Discord bot created successfully"

    async def _start_bot(self) -> None:
        r"""Start the Discord bot (internal async method)."""
        if not self._agent_instance:
            raise ValueError("Bot agent not created. Call create_agent first.")

        # Use the start method from DiscordApp
        await self._discord_app.start()

    def start_bot(self) -> str:
        r"""Start the Discord bot and begin listening for messages.

        Returns:
            str: A message indicating the bot has started.
        """
        if not self._agent_instance:
            return "Error: Bot agent not created. Call create_agent first."

        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            logger.info("Starting Discord bot...")
            loop.run_until_complete(self._start_bot())
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            return "Bot stopped by user"
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            return f"Error starting bot: {e}"
        finally:
            loop.close()

        return "Discord bot started successfully"

    async def exchange_code_for_token(self, code: str) -> str:
        r"""Exchange the authorization code for an access token.

        Args:
            code (str): The authorization code received from Discord after
                user authorization.

        Returns:
            str: A message indicating the result of the token exchange.
        """
        try:
            token_response = (
                await self._discord_app.exchange_code_for_token_response(code)
            )
            if token_response:
                return "Successfully exchanged code for token"
            else:
                return "Failed to exchange code for token"
        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return f"Error exchanging code for token: {e}"

    def get_oauth_url(self, scopes: Optional[List[str]] = None) -> str:
        r"""Get the OAuth URL for authorizing the bot.

        Args:
            scopes (Optional[List[str]], optional): The OAuth scopes to request
                Defaults to ['bot', 'applications.commands'].

        Returns:
            str: The OAuth URL for authorizing the bot.
        """
        if (
            not hasattr(self._discord_app, 'client_id')
            or not self._discord_app.client_id
        ):
            return (
                "Error: No client_id provided. OAuth URL cannot be generated."
            )

        if scopes is None:
            scopes = ['bot', 'applications.commands']

        # Construct the OAuth URL
        scope_str = '%20'.join(scopes)
        permissions = 3072

        oauth_url = (
            f"https://discord.com/api/oauth2/authorize"
            f"?client_id={self._discord_app.client_id}"
            f"&permissions={permissions}"
            f"&scope={scope_str}"
            f"&response_type=code"
        )

        if (
            hasattr(self._discord_app, 'redirect_uri')
            and self._discord_app.redirect_uri
        ):
            oauth_url += f"&redirect_uri={self._discord_app.redirect_uri}"

        return oauth_url

    def get_tools(self) -> List[FunctionTool]:
        r"""Return a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the available functions in this toolkit.
        """
        return [
            FunctionTool(self.create_agent),
            FunctionTool(self.process_message),
            FunctionTool(self.create_bot),
            FunctionTool(self.start_bot),
            FunctionTool(self.get_oauth_url),
        ]
