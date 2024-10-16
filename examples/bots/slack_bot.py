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
import queue
import threading
from typing import Optional

from slack_bolt.context.async_context import AsyncBoltContext
from slack_bolt.context.say.async_say import AsyncSay
from slack_sdk.web.async_client import AsyncWebClient

from camel.bots import SlackApp, SlackEventBody
from examples.bots.agent import Agent


class SlackBot(SlackApp):
    r"""SlackBot class that extends the SlackApp class to handle Slack events
    and integrate with a message queue for asynchronous processing.

    This class initializes the Slack app and adds a message handler to process
    Slack events, specifically for incoming messages.

    Args:
        msg_queue (queue.Queue): A thread-safe queue to communicate between
            threads.
        token (Optional[str]): Slack API token for authentication.
        scopes (Optional[str]): Slack app scopes for permissions.
        signing_secret (Optional[str]): Signing secret for verifying Slack
            requests.
        client_id (Optional[str]): Slack app client ID.
        client_secret (Optional[str]): Slack app client secret.
    """

    def __init__(
        self,
        msg_queue: queue.Queue,
        token: Optional[str] = None,
        scopes: Optional[str] = None,
        signing_secret: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        r"""Initializes the SlackBot instance with a message queue and the
        required Slack authentication details.

        Args:
            msg_queue (queue.Queue): A thread-safe queue to communicate between
                threads.
            token (Optional[str]): Slack API token for authentication.
            scopes (Optional[str]): Slack app scopes for permissions.
            signing_secret (Optional[str]): Signing secret for verifying Slack
                requests.
            client_id (Optional[str]): Slack app client ID.
            client_secret (Optional[str]): Slack app client secret.
        """
        super().__init__(
            token=token,
            scopes=scopes,
            signing_secret=signing_secret,
            client_id=client_id,
            client_secret=client_secret,
        )
        self._queue: queue.Queue = msg_queue

    async def on_message(
        self,
        context: "AsyncBoltContext",
        client: "AsyncWebClient",
        event: dict,
        body: dict,
        say: "AsyncSay",
    ):
        r"""Event handler for processing incoming Slack messages.

        This method is called when a message event is received from Slack.
        It acknowledges the message and adds the event body and say function to
        the queue for further processing.

        Args:
            context (AsyncBoltContext): Context object that contains
                information about the Slack event.
            client (AsyncWebClient): Slack Web API client for making API
                requests.
            event (dict): Event data containing details of the incoming Slack
                message.
            body (dict): Full request body from Slack.
            say (AsyncSay): A function to send a response back to the Slack
                channel.
        """
        await context.ack()
        event_body = SlackEventBody(**body)
        self._queue.put((event_body, say))


async def process_message(agent: Agent, msg_queue: queue.Queue):
    r"""Process messages from the queue asynchronously.

    This function continuously retrieves messages from the message queue,
    processes them using the `Agent` instance, and sends the response back
    to Slack using the `say` function.

    Args:
        agent (Agent): An instance of the `Agent` class that handles the
            processing of the incoming message.
        msg_queue (queue.Queue): A thread-safe queue that stores Slack event
            messages and the corresponding `say` functions for response.
    """
    while True:
        event_body, say = msg_queue.get()

        print(f"Received message: {event_body.event.text}")
        user_raw_msg = event_body.event.text

        # Process the message using the agent and send response back to Slack.
        response = await agent.process(user_raw_msg)
        await say(response)
        msg_queue.task_done()


def start_async_queue_processor(agent: Agent, msg_queue: queue.Queue):
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
    msg_queue = queue.Queue()

    agent = Agent()

    thread = threading.Thread(target=start_async_queue_processor, args=(
        agent, msg_queue
    ))
    thread.start()

    # Initialize the SlackBot with the message queue.
    slack_bot = SlackBot(msg_queue=msg_queue)
    slack_bot.run(3000)

    thread.join()
