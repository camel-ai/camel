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

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from slack_sdk import WebClient
    from ssl import SSLContext

from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

def login_slack(slack_token: Optional[str] = None, ssl: Optional[SSLContext] = None,) -> WebClient:
    r"""Authenticate using the Slack API.
    
    Args:
        slack_token (str, optional): The Slack API token. If not provided, it
            attempts to retrieve the token from the environment variable
            SLACK_BOT_TOKEN or SLACK_USER_TOKEN.
        ssl (SSLContext, optional): SSL context for secure connections.
            Defaults to `None`.

    Returns:
        WebClient: A WebClient object for interacting with Slack API.

    Raises:
        ImportError: If slack_sdk package is not installed.
        KeyError: If SLACK_BOT_TOKEN or SLACK_USER_TOKEN environment variables
            are not set.
    """
    try:
        from slack_sdk import WebClient
    except ImportError as e:
        raise ImportError(
            "Cannot import slack_sdk. Please install the package with \
            `pip install slack_sdk`."
        ) from e
    if not slack_token:
        slack_token = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get("SLACK_USER_TOKEN")
        if not slack_token:
            raise KeyError("SLACK_BOT_TOKEN or SLACK_USER_TOKEN environment variable not set.")

    client = WebClient(token=slack_token,ssl=ssl)
    logger.info("Slack login successful.")
    return client


def get_slack_channel_information() -> str:
    r"""Retrieve Slack channels and return relevant information in JSON format.

    Returns:
        str: JSON string containing information about Slack channels.

    Raises:
        SlackApiError: If there is an error during get slack channel
            information.
    """
    try:
        slack_client = login_slack()
        result = slack_client.conversations_list()
        channels = result.get("channels", []) # type: ignore[var-annotated]
        # Filtering channels and extracting required information
        filtered_result = [
            {key: channel[key] for key in ("id", "name", "created", "num_members")}
            for channel in channels
            if all(key in channel for key in ("id", "name", "created", "num_members"))
        ]
        return json.dumps(filtered_result, ensure_ascii=False)
    except SlackApiError as e:
        return f"Error creating conversation: {e.response['error']}"

def get_slack_channel_message(
    channel_id: str) -> str:
    r"""Retrieve messages from a Slack channel.

    Args:
        channel_id (str): The ID of the Slack channel to retrieve messages
            from.

    Returns:
        str: JSON string containing filtered message data.

    Raises:
        SlackApiError: If there is an error during get slack channel message.
    """
    try:
        slack_client = login_slack()
        result = slack_client.conversations_history(channel=channel_id)
        messages = result["messages"]
        filtered_messages = [
            {key: message[key] for key in ("user", "text", "ts")}
            for message in messages
            if all(key in message for key in ("user", "text", "ts"))
        ]
        return json.dumps(filtered_messages, ensure_ascii=False)
    except SlackApiError as e:
        return f"Error retrieving messages: {e.response['error']}"

def send_slack_message(
    message: str,
    channel: str,
) -> str:
    r"""Send a message to a Slack channel.

    Args:
        message (str): The message to send.
        channel (str): The Slack channel ID or name.

    Returns:
        str: A confirmation message indicating whether the message was sent
            successfully or an error message.

    Raises:
        SlackApiError: If an error occurs while sending the message.
    """
    try:
        slack_client = login_slack()
        result = slack_client.chat_postMessage(channel=channel, text=message)
        output = f"Message sent: {result}"
        return output
    except SlackApiError as e:
        return f"Error creating conversation: {e.response['error']}"
