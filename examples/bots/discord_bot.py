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
from typing import TYPE_CHECKING, Optional

from camel.bots import DiscordApp
from examples.bots.agent import Agent

if TYPE_CHECKING:
    from discord import Message


class DiscordBot(DiscordApp):
    """A Discord bot that listens for messages, adds them to a queue,
    and processes them asynchronously.

    This class extends the functionality of `DiscordApp` and adds message
    handling by pushing messages into a queue for further processing.

    Args:
        msg_queue (asyncio.Queue): A queue used to store incoming messages for
            processing.
        token (Optional[str]): The token used to authenticate the bot with
            Discord.
        channel_ids (Optional[list[int]]): A list of Discord channel IDs where
            the bot is allowed to interact.
    """

    def __init__(
        self,
        msg_queue: asyncio.Queue,
        token: Optional[str] = None,
        channel_ids: Optional[list[int]] = None,
    ):
        super().__init__(token=token, channel_ids=channel_ids)
        self._queue: asyncio.Queue = msg_queue

    async def on_message(self, message: 'Message') -> None:
        """Event handler for received messages. This method processes incoming
        messages, checks whether the message is from the bot itself, and
        determines whether the bot should respond based on channel ID and
        mentions.

        Args:
            message (discord.Message): The received message object.
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

        await self._queue.put(message)


async def process_message(agent: Agent, msg_queue: asyncio.Queue):
    """Continuously processes messages from the queue and sends responses.

    This function waits for new messages in the queue, processes each message
    using the `Agent` instance, and sends the response back to Discord.

    Args:
        agent (Agent): An instance of `Agent` that processes the received
            messages.
        msg_queue (asyncio.Queue): The queue from which messages are retrieved
            for processing.
    """
    while True:
        message: "Message" = await msg_queue.get()
        user_raw_msg = message.content

        # Process the message using the agent and get the response
        response = await agent.process(user_raw_msg)
        # message.reply(response)
        await message.channel.send(response)
        msg_queue.task_done()


async def main():
    """Main function to initialize and run the Discord bot and message
    processor.

    This function initializes the message queue, creates an `Agent` instance
    for processing messages, and starts both the Discord bot and the
    message-processing loop asynchronously.
    """
    msg_queue = asyncio.Queue()

    agent = Agent()

    # Initialize the DiscordBot with the message queue
    discord_bot = DiscordBot(msg_queue=msg_queue)
    await asyncio.gather(
        discord_bot.start(), process_message(agent, msg_queue)
    )


if __name__ == "__main__":
    asyncio.run(main())
