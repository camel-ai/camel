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

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from camel.bots.slack.slack_application import SlackApplication
from camel.logger import get_logger

if TYPE_CHECKING:
    from ssl import SSLContext

logger = get_logger(__name__)


class SlackAdapter(SlackApplication):
    r"""An adapter class for Slack operations to handle authentication
    and event processing for Slack triggers.

    This class extends SlackApplication to provide trigger-specific functionality
    while inheriting unified authentication and Slack client management.
    """

    def __init__(
        self,
        slack_token: Optional[str] = None,
        app_token: Optional[str] = None,
        signing_secret: Optional[str] = None,
        ssl: Optional[SSLContext] = None,
    ):
        r"""Initializes a new instance of the SlackAdapter class.

        Args:
            slack_token (Optional[str]): The Slack Bot or User token.
                If not provided, attempts to retrieve from environment variables.
            app_token (Optional[str]): The Slack App-level token for Socket Mode.
                If not provided, attempts to retrieve from SLACK_APP_TOKEN.
            signing_secret (Optional[str]): The Slack signing secret for webhook verification.
                If not provided, attempts to retrieve from SLACK_SIGNING_SECRET.
            ssl (Optional[SSLContext]): SSL context for secure connections.
        """
        super().__init__(
            slack_token=slack_token,
            app_token=app_token,
            signing_secret=signing_secret,
            ssl=ssl,
        )

    def parse_webhook_event(
        self, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        r"""Parse a Slack webhook event payload.

        Args:
            payload (Dict[str, Any]): The webhook payload from Slack.

        Returns:
            Optional[Dict[str, Any]]: Parsed event data or None if invalid.
        """
        try:
            # Handle different types of Slack webhook events
            if "challenge" in payload:
                # URL verification challenge
                return {
                    "type": "url_verification",
                    "challenge": payload["challenge"],
                }

            if "event" in payload:
                # Event API payload
                event = payload["event"]
                return {
                    "type": "event_callback",
                    "event_type": event.get("type"),
                    "channel": event.get("channel"),
                    "user": event.get("user"),
                    "text": event.get("text"),
                    "ts": event.get("ts"),
                    "team_id": payload.get("team_id"),
                    "api_app_id": payload.get("api_app_id"),
                    "event_id": payload.get("event_id"),
                    "event_time": payload.get("event_time"),
                }

            if "trigger_id" in payload:
                # Interactive components or slash commands
                return {
                    "type": "interactive_component",
                    "trigger_id": payload["trigger_id"],
                    "user": payload.get("user", {}).get("id"),
                    "team": payload.get("team", {}).get("id"),
                    "channel": payload.get("channel", {}).get("id"),
                    "response_url": payload.get("response_url"),
                }

            # Generic payload
            return {
                "type": "generic",
                "payload": payload,
            }

        except Exception as e:
            logger.error(f"Error parsing Slack webhook event: {e}")
            return None
