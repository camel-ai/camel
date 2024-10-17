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
import threading
from queue import Queue

from camel.bots import BotAgent, SlackApp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_message(agent: BotAgent, msg_queue: Queue):
    r"""Process messages from the queue asynchronously.

    This function continuously retrieves messages from the message queue,
    processes them using the `Agent` instance, and sends the response back
    to Slack using the `say` function.

    Args:
        agent (BotAgent): An instance of the `Agent` class that handles the
            processing of the incoming message.
        msg_queue (Queue): A thread-safe queue that stores Slack event
            messages and the corresponding `say` functions for response.
    """
    while True:
        event_body, say = msg_queue.get()

        logger.info(f"Received message: {event_body.event.text}")
        user_raw_msg = event_body.event.text

        # Process the message using the agent and send response back to Slack.
        response = await agent.process(user_raw_msg)
        await say(response)
        msg_queue.task_done()


def start_async_queue_processor(agent: BotAgent, msg_queue: Queue):
    r"""Start an asynchronous queue processor in a new event loop.

    This function creates a new asyncio event loop in a separate thread to
    asynchronously process messages from the queue. It will run until all
    the messages in the queue have been processed.

    Args:
        agent (Agent): The agent responsible for processing the messages.
        msg_queue (queue.Queue): The message queue that contains Slack events
            and responses.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Schedule the asynchronous message processing task in this event loop
    loop.run_until_complete(process_message(agent, msg_queue))


if __name__ == "__main__":
    r"""Main entry point for running the Slack bot application.

    This section initializes the required components including the message 
    queue, agent, and the SlackBot instance. It also starts a separate thread 
    for asynchronous message processing to avoid blocking the Slack bot's main 
    event loop. The `slack_bot.run()` function will handle incoming Slack 
    events on the main thread, while the separate thread will handle processing
    the messages from the queue.
    """
    msg_queue = Queue()

    agent = BotAgent()

    thread = threading.Thread(
        target=start_async_queue_processor, args=(agent, msg_queue)
    )
    thread.start()

    # Initialize the SlackBot with the message queue.
    slack_bot = SlackApp(msg_queue=msg_queue)
    slack_bot.run(3000)

    thread.join()
