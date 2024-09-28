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
from typing import TYPE_CHECKING, List, Optional, Union

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.retrievers import AutoRetriever
from camel.utils import dependencies_required

try:
    from unstructured.documents.elements import Element
except ImportError:
    Element = None

if TYPE_CHECKING:
    from discord import Message


class DiscordBot:
    r"""Represents a Discord bot that is powered by a CAMEL `ChatAgent`.

    Attributes:
        chat_agent (ChatAgent): Chat agent that will power the bot.
        channel_ids (List[int], optional): The channel IDs that the bot will
            listen to.
        discord_token (str, optional): The bot token.
        auto_retriever (AutoRetriever): AutoRetriever instance for RAG.
        vector_storage_local_path (Union[str, List[str]]): The paths to the
            contents for RAG.
        top_k (int): Top choice for the RAG response.
        return_detailed_info (bool): If show detailed info of the RAG response.
        contents (Union[str, List[str], Element, List[Element]], optional):
            Local file paths, remote URLs, string contents or Element objects.
    """

    @dependencies_required('discord')
    def __init__(
        self,
        chat_agent: ChatAgent,
        contents: Union[str, List[str], Element, List[Element]] = None,
        channel_ids: Optional[List[int]] = None,
        discord_token: Optional[str] = None,
        auto_retriever: Optional[AutoRetriever] = None,
        vector_storage_local_path: Union[str, List[str]] = "",
        top_k: int = 1,
        return_detailed_info: bool = True,
    ) -> None:
        self.chat_agent = chat_agent
        self.token = discord_token or os.getenv('DISCORD_TOKEN')
        self.channel_ids = channel_ids
        self.auto_retriever = auto_retriever
        self.vector_storage_local_path = vector_storage_local_path
        self.top_k = top_k
        self.return_detailed_info = return_detailed_info
        self.contents = contents

        if not self.token:
            raise ValueError(
                "`DISCORD_TOKEN` not found in environment variables. Get it"
                " here: `https://discord.com/developers/applications`."
            )

        import discord

        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)

        # Register event handlers
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

    def run(self) -> None:
        r"""Start the Discord bot using its token.

        This method starts the Discord bot by running the client with the
        provided token.
        """
        self.client.run(self.token)  # type: ignore[arg-type]

    async def on_ready(self) -> None:
        r"""This method is called when the bot has successfully connected to
        the Discord server.

        It prints a message indicating that the bot has logged in and displays
        the username of the bot.
        """
        print(f'We have logged in as {self.client.user}')

    async def on_message(self, message: 'Message') -> None:
        r"""Event handler for when a message is received.

        Args:
            message (discord.Message): The message object received.
        """

        # If the message author is the bot itself,
        # do not respond to this message
        if message.author == self.client.user:
            return

        # If allowed channel IDs are provided,
        # only respond to messages in those channels
        if self.channel_ids and message.channel.id not in self.channel_ids:
            return

        # Only respond to messages that mention the bot
        if not self.client.user or not self.client.user.mentioned_in(message):
            return

        user_raw_msg = message.content

        if self.auto_retriever:
            retrieved_content = self.auto_retriever.run_vector_retriever(
                query=user_raw_msg,
                contents=self.contents,
                top_k=self.top_k,
                return_detailed_info=self.return_detailed_info,
            )
            user_raw_msg = (
                f"Here is the query to you: {user_raw_msg}\n"
                f"Based on the retrieved content: {retrieved_content}, \n"
                f"answer the query from {message.author.name}"
            )

        user_msg = BaseMessage.make_user_message(
            role_name="User", content=user_raw_msg
        )
        assistant_response = self.chat_agent.step(user_msg)
        await message.channel.send(assistant_response.msg.content)


if __name__ == "__main__":
    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content='''
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
                        closely match the user's query. The RAG file contains
                        detailed interactions and should be your primary 
                        resource for crafting responses.
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
            bd
            Tone:
                Professional: Maintain a professional tone that 
                        instills confidence in the user.
                Friendly: Be approachable and friendly to make users 
                        feel comfortable.
                Helpful: Always aim to be as helpful as possible,
                        guiding users to solutions.        
        ''',
    )

    agent = ChatAgent(
        assistant_sys_msg,
        message_window_size=10,
    )
    # Uncommented the folowing code and offer storage information
    # for RAG functionality

    # auto_retriever = AutoRetriever(
    #     vector_storage_local_path="examples/bots",
    #     storage_type=StorageType.QDRANT,
    # )

    bot = DiscordBot(
        agent,
        # auto_retriever=auto_retriever,
        # vector_storage_local_path=["local_data/"],
    )
    bot.run()
