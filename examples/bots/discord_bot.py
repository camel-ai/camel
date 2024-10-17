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

from discord import Message

from camel.bots import BotAgent, DiscordApp


async def process_message(agent: BotAgent, msg_queue: asyncio.Queue):
    r"""Continuously processes messages from the queue and sends responses.

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
    r"""Main function to initialize and run the Discord bot and message
    processor.

    This function initializes the message queue, creates an `Agent` instance
    for processing messages, and starts both the Discord bot and the
    message-processing loop asynchronously.
    """
    msg_queue = asyncio.Queue()

    agent = BotAgent()

    # Initialize the DiscordBot with the message queue
    discord_bot = DiscordApp(msg_queue=msg_queue)
    await asyncio.gather(
        discord_bot.start(), process_message(agent, msg_queue)
    )


if __name__ == "__main__":
    asyncio.run(main())
