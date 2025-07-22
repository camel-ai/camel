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

import json
import os
import re
from typing import TYPE_CHECKING, Any, List, Optional

from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer

if TYPE_CHECKING:
    from ssl import SSLContext

    from slack_sdk import WebClient

from camel.logger import get_logger
from camel.toolkits import FunctionTool

logger = get_logger(__name__)


@MCPServer()
class SlackToolkit(BaseToolkit):
    r"""A class representing a toolkit for Slack operations.

    This class provides methods for Slack operations such as creating a new
    channel, joining an existing channel, leaving a channel.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        r"""Initializes a new instance of the SlackToolkit class.

        Args:
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

    def _login_slack(
        self,
        slack_token: Optional[str] = None,
        ssl: Optional[SSLContext] = None,
    ) -> WebClient:
        r"""Authenticate using the Slack API.

        Args:
            slack_token (str, optional): The Slack API token.
                If not provided, it attempts to retrieve the token from
                the environment variable SLACK_BOT_TOKEN or SLACK_USER_TOKEN.
            ssl (SSLContext, optional): SSL context for secure connections.
                Defaults to `None`.

        Returns:
            WebClient: A WebClient object for interacting with Slack API.

        Raises:
            ImportError: If slack_sdk package is not installed.
            KeyError: If SLACK_BOT_TOKEN or SLACK_USER_TOKEN
                environment variables are not set.
        """
        try:
            from slack_sdk import WebClient
        except ImportError as e:
            raise ImportError(
                "Cannot import slack_sdk. Please install the package with \
                `pip install slack_sdk`."
            ) from e
        if not slack_token:
            slack_token = os.environ.get("SLACK_BOT_TOKEN") or os.environ.get(
                "SLACK_USER_TOKEN"
            )
            if not slack_token:
                raise KeyError(
                    "SLACK_BOT_TOKEN or SLACK_USER_TOKEN environment "
                    "variable not set."
                )

        client = WebClient(token=slack_token, ssl=ssl)
        logger.info("Slack login successful.")
        return client

    def create_slack_channel(
        self, name: str, is_private: Optional[bool] = True
    ) -> str:
        r"""Creates a new slack channel, either public or private.

        Args:
            name (str): Name of the public or private channel to create.
            is_private (bool, optional): Whether to create a private channel
                instead of a public one. Defaults to `True`.

        Returns:
            str: JSON string containing information about Slack
                channel created.

        Raises:
            SlackApiError: If there is an error during get slack channel
                information.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            response = slack_client.conversations_create(
                name=name, is_private=is_private
            )
            channel_id = response["channel"]["id"]
            response = slack_client.conversations_archive(channel=channel_id)
            return str(response)
        except SlackApiError as e:
            return f"Error creating conversation: {e.response['error']}"

    def join_slack_channel(self, channel_id: str) -> str:
        r"""Joins an existing Slack channel.

        Args:
            channel_id (str): The ID of the Slack channel to join.

        Returns:
            str: A confirmation message indicating whether join successfully
                or an error message.

        Raises:
            SlackApiError: If there is an error during get slack channel
                information.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            response = slack_client.conversations_join(channel=channel_id)
            return str(response)
        except SlackApiError as e:
            return f"Error creating conversation: {e.response['error']}"

    def leave_slack_channel(self, channel_id: str) -> str:
        r"""Leaves an existing Slack channel.

        Args:
            channel_id (str): The ID of the Slack channel to leave.

        Returns:
            str: A confirmation message indicating whether leave successfully
                or an error message.

        Raises:
            SlackApiError: If there is an error during get slack channel
                information.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            response = slack_client.conversations_leave(channel=channel_id)
            return str(response)
        except SlackApiError as e:
            return f"Error creating conversation: {e.response['error']}"

    def get_slack_channel_information(self) -> str:
        r"""Retrieve Slack channels and return relevant information in JSON
            format.

        Returns:
            str: JSON string containing information about Slack channels.

        Raises:
            SlackApiError: If there is an error during get slack channel
                information.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            response = slack_client.conversations_list()
            conversations = response["channels"]
            # Filtering conversations and extracting required information
            filtered_result = [
                {
                    key: conversation[key]
                    for key in ("id", "name", "created", "num_members")
                }
                for conversation in conversations
                if all(
                    key in conversation
                    for key in ("id", "name", "created", "num_members")
                )
            ]
            return json.dumps(filtered_result, ensure_ascii=False)
        except SlackApiError as e:
            return f"Error creating conversation: {e.response['error']}"

    def get_slack_channel_message(self, channel_id: str) -> str:
        r"""Retrieve messages from a Slack channel.

        Args:
            channel_id (str): The ID of the Slack channel to retrieve messages
                from.

        Returns:
            str: JSON string containing filtered message data.

        Raises:
            SlackApiError: If there is an error during get
                slack channel message.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
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
        self,
        message: str,
        channel_id: str,
        file_path: Optional[str] = None,
        user: Optional[str] = None,
        blocks: Optional[list[Any]] = None,
    ) -> str:
        r"""Send a message to a Slack channel.

        Args:
            message (str): The message to send.
            channel_id (str): The ID of the Slack channel to send message.
            file_path (Optional[str]): The path of the file to send.
                Defaults to `None`.
            user (Optional[str]): The user ID of the recipient.
                Defaults to `None`.
            blocks (Optional[list[Any]): JSON list of Block Kit layout blocks.

        Returns:
            str: A confirmation message indicating whether the message was sent
                successfully or an error message.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            if file_path:
                response = slack_client.files_upload_v2(
                    channel=channel_id,
                    file=file_path,
                    initial_comment=message,
                )
                return f"File sent successfully, got response: {response}"
            if user:
                response = slack_client.chat_postEphemeral(
                    channel=channel_id, text=message, user=user, blocks=blocks
                )
            else:
                response = slack_client.chat_postMessage(
                    channel=channel_id, text=message, blocks=blocks
                )
            return (
                f"Message: {message} sent successfully, "
                f"got response: {response}"
            )
        except SlackApiError as e:
            return f"Error creating conversation: {e.response['error']}"

    def make_confirm_object(
        self,
        title: dict,
        text: dict,
        confirm_text: dict,
        deny_text: dict,
        style: Optional[str] = None,
    ) -> dict[str, Any]:
        r"""Creates a confirm dialog object for Slack Block Kit.

        Args:
            title (dict): The title of the confirmation dialog.
            text (dict): The main text to display in the dialog.
            confirm_text (dict): The text for the confirmation button.
            deny_text (dict): The text for the denial button.
            style (Optional[str], optional): The style of the confirmation
                button ('primary' or 'danger'). Defaults to :obj:`None`.

        Returns:
            dict: A dictionary representing a Slack Block Kit confirm dialog
                object.

        Raises:
            ValueError: If any of the text objects are not of the correct type.
            ValueError: If the style is not 'primary' or 'danger'.
        """
        if title.get("type") != "plain_text":
            raise ValueError(
                "The title text object must be of type 'plain_text', "
                "not 'mrkdwn'."
            )
        if text.get("type") != "mrkdwn":
            raise ValueError(
                "The text object must be of type 'mrkdwn', not 'plain_text'."
            )
        if confirm_text.get("type") != "plain_text":
            raise ValueError(
                "The confirm_text text object must be of type 'plain_text', "
                "not 'mrkdwn'."
            )
        if deny_text.get("type") != "plain_text":
            raise ValueError(
                "The deny_text text object must be of type 'plain_text', "
                "not 'mrkdwn'."
            )

        # Validate style parameter
        if style is not None:
            if style not in ["primary", "danger"]:
                raise ValueError("The style must be 'primary' or 'danger'.")

        confirm_obj: dict[str, Any] = {
            "title": title,
            "text": text,
            "confirm": confirm_text,
            "deny": deny_text,
        }
        if style is not None:
            confirm_obj["style"] = style
        return confirm_obj

    def make_button(
        self,
        text: dict,
        action_id: Optional[str] = None,
        value: Optional[str] = None,
        style: Optional[str] = None,
        url: Optional[str] = None,
        confirm: Optional[dict] = None,
        accessibility_label: Optional[str] = None,
    ) -> dict:
        r"""Creates a button element for Slack Block Kit.

        Args:
            text (dict): The text to display on the button.
            action_id (Optional[str], optional): A unique identifier for the
                button action. Defaults to :obj:`None`.
            value (Optional[str], optional): The value to send when the button
                is clicked. Defaults to :obj:`None`.
            style (Optional[str], optional): The button style
                ('primary' or 'danger'). Defaults to :obj:`None`.
            url (Optional[str], optional): URL to open when the button is
                clicked. Defaults to :obj:`None`.
            confirm (Optional[dict], optional): A confirm object that describes
                an optional confirmation dialog that appears after a button is
                clicked. Defaults to :obj:`None`.
            accessibility_label (Optional[str], optional): A label for
                accessibility purposes. Defaults to :obj:`None`.

        Returns:
            dict: A dictionary representing a Slack Block Kit button element.

        Raises:
            ValueError: If the style is not 'primary' or 'danger'.
            ValueError: If the text object is not of type 'plain_text'.
            ValueError: If the button text exceeds 75 characters.
            ValueError: If the URL exceeds 3000 characters.
            ValueError: If the accessibility_label exceeds 75 characters.
        """
        if style is not None:
            if style not in ["primary", "danger"]:
                raise ValueError("The style must be 'primary' or 'danger'.")

        if text.get("type") != "plain_text":
            raise ValueError(
                "The text object must be of type 'plain_text', not 'mrkdwn'."
            )

        # Validate text length (max 75 characters for Slack button text)
        text_content = text.get("text", "")
        if len(text_content) > 75:
            raise ValueError("Button text cannot exceed 75 characters.")

        # Validate url length (max 3000 characters)
        if url is not None and len(url) > 3000:
            raise ValueError("Button url cannot exceed 3000 characters.")

        # Validate accessibility_label length (max 75 characters)
        if accessibility_label is not None and len(accessibility_label) > 75:
            raise ValueError(
                "Button accessibility_label cannot exceed 75 characters."
            )

        return {
            "type": "button",
            "text": text,
            **({"action_id": action_id} if action_id is not None else {}),
            **({"value": value} if value is not None else {}),
            **({"style": style} if style is not None else {}),
            **({"url": url} if url is not None else {}),
            **({"confirm": confirm} if confirm is not None else {}),
            **(
                {"accessibility_label": accessibility_label}
                if accessibility_label is not None
                else {}
            ),
        }

    def make_option(
        self,
        text: dict,
        value: str,
        description: Optional[dict] = None,
        url: Optional[str] = None,
    ) -> dict:
        r"""Creates an option object for Slack Block Kit select menus.

        Args:
            text (dict): The text to display for the option.
            value (str): The value sent when this option is selected.
            description (Optional[dict], optional): A description for the
                option. Defaults to :obj:`None`.
            url (Optional[str], optional): A URL to load in the user's browser
                when the option is selected. Defaults to :obj:`None`.

        Returns:
            dict: A dictionary representing a Slack Block Kit option object.

        Raises:
            ValueError: If the text, value, description, or url exceed their
                maximum allowed lengths.
            ValueError: If the text object is not a valid text object.
            ValueError: If the description object is not a valid text object.
        """
        # Validate text object
        if (
            not isinstance(text, dict)
            or "type" not in text
            or "text" not in text
        ):
            raise ValueError(
                "The text parameter must be a valid text object with 'type' "
                "and 'text' keys."
            )

        if text.get("type") not in ("plain_text", "mrkdwn"):
            raise ValueError(
                "The text object type must be either 'plain_text' or "
                "'mrkdwn'."
            )

        # Check text length
        if len(text.get("text", "")) > 75:
            raise ValueError("Option text cannot exceed 75 characters.")

        # Check value length
        if len(value) > 150:
            raise ValueError("Option value cannot exceed 150 characters.")

        option = {
            "text": text,
            "value": value,
        }

        if description:
            # Validate description object
            if (
                not isinstance(description, dict)
                or "type" not in description
                or "text" not in description
            ):
                raise ValueError(
                    "The description parameter must be a valid text object "
                    "with 'type' and 'text' keys."
                )

            if description.get("type") not in ("plain_text", "mrkdwn"):
                raise ValueError(
                    "The description object type must be either 'plain_text' "
                    "or 'mrkdwn'."
                )

            if len(description.get("text", "")) > 75:
                raise ValueError(
                    "Option description cannot exceed 75 characters."
                )
            option["description"] = description

        if url:
            if len(url) > 3000:
                raise ValueError("Option url cannot exceed 3000 characters.")
            option["url"] = url

        return option

    def make_option_group(
        self,
        label: dict,
        options: list[dict],
    ) -> dict:
        r"""Creates an option group object for Slack Block Kit select menus.

        Args:
            label (dict): The label for the option group. Must be a
                plain_text object.
            options (list[dict]): A list of option objects, each containing
                'text' and 'value' keys.

        Returns:
            dict: A dictionary representing a Slack Block Kit option group
                object.

        Raises:
            ValueError: If the label text object is not of type 'plain_text'.
            TypeError: If the options parameter is not a list of option
                objects.
            ValueError: If any option does not contain required keys or has
                an invalid 'text' object.
        """
        if label.get("type") != "plain_text":
            raise ValueError(
                "The label text object must be of type 'plain_text', "
                "not 'mrkdwn'."
            )

        # Check that options is a list
        if not isinstance(options, list):
            raise TypeError(
                "The options parameter must be a list of option objects."
            )

        for idx, option in enumerate(options):
            # Check that each option is a dict
            if not isinstance(option, dict):
                raise TypeError(f"Option at index {idx} is not a dictionary.")
            # Check required keys
            if "text" not in option or "value" not in option:
                raise ValueError(
                    f"Option at index {idx} must contain 'text' and "
                    "'value' keys."
                )
            # Check text object
            if (
                not isinstance(option["text"], dict)
                or "type" not in option["text"]
            ):
                raise ValueError(
                    f"Option at index {idx} has an invalid 'text' object."
                )

        return {
            "label": label,
            "options": options,
        }

    def make_select_menu(
        self,
        action_id: Optional[str] = None,
        options: Optional[list[dict]] = None,
        option_groups: Optional[list[dict]] = None,
        initial_option: Optional[dict] = None,
        confirm: Optional[dict] = None,
        focus_on_load: bool = False,
        placeholder: Optional[dict] = None,
    ) -> dict:
        r"""Creates a static select menu for Slack Block Kit.

        Args:
            action_id (Optional[str], optional): A unique identifier for the
                select menu action. Defaults to :obj:`None`.
            options (Optional[list[dict]], optional): List of option
                dictionaries created with make_option(). Mutually exclusive
                with option_groups. Defaults to :obj:`None`.
            option_groups (Optional[list[dict]], optional): List of option
                group dicts. Defaults to :obj:`None`.
            initial_option (Optional[dict], optional): The initially selected
                option. Defaults to :obj:`None`.
            confirm (Optional[dict], optional): A confirm object for
                confirmation dialog. Defaults to :obj:`None`.
            focus_on_load (bool): Whether to focus on load.
                Defaults to :obj:`False`.
            placeholder (Optional[dict], optional): Placeholder text to
                display when no option is selected. Defaults to :obj:`None`.

        Returns:
            dict: A dictionary representing a Slack Block Kit static select
                menu.

        Raises:
            ValueError: If both options and option_groups are provided.
            ValueError: If action_id exceeds 255 characters.
            ValueError: If options or option_groups exceed 100 items.
            ValueError: If placeholder is not a plain_text object or exceeds
                100 characters.
            ValueError: If initial_option is not a valid option object.
        """

        if action_id is not None and len(action_id) > 255:
            raise ValueError("The action_id cannot exceed 255 characters.")

        if options is not None and option_groups is not None:
            raise ValueError(
                "You must provide either 'options' or 'option_groups', "
                "not both."
            )

        if options is not None:
            if len(options) > 100:
                raise ValueError("The options list cannot exceed 100 options.")

        if option_groups is not None:
            if len(option_groups) > 100:
                raise ValueError(
                    "The option_groups list cannot exceed 100 option groups."
                )

        # Validate initial_option if provided
        if initial_option is not None:
            if not isinstance(initial_option, dict):
                raise ValueError("The initial_option must be a dictionary.")

            if "text" not in initial_option or "value" not in initial_option:
                raise ValueError(
                    "The initial_option must contain 'text' and 'value' keys."
                )

            # Validate the text object within initial_option
            text_obj = initial_option.get("text")
            if (
                not isinstance(text_obj, dict)
                or "type" not in text_obj
                or "text" not in text_obj
            ):
                raise ValueError(
                    "The initial_option text object must be a valid text "
                    "object with 'type' and 'text' keys."
                )

            if text_obj.get("type") not in ("plain_text", "mrkdwn"):
                raise ValueError(
                    "The initial_option text object type must be either "
                    "'plain_text' or 'mrkdwn'."
                )

            # Check if initial_option exists in the provided options
            # (if options are provided)
            if options is not None:
                initial_value = initial_option.get("value")
                if not any(
                    opt.get("value") == initial_value for opt in options
                ):
                    raise ValueError(
                        "The initial_option must exist in the provided "
                        "options list."
                    )

        if placeholder is not None:
            if placeholder.get("type") != "plain_text":
                raise ValueError(
                    "The placeholder text object must be of type "
                    "'plain_text', not 'mrkdwn'."
                )
            if len(placeholder.get("text", "")) > 100:
                raise ValueError(
                    "The placeholder text cannot exceed 100 characters."
                )

        select_menu = {
            "type": "static_select",
            **({"action_id": action_id} if action_id is not None else {}),
            **({"options": options} if options is not None else {}),
            **(
                {"option_groups": option_groups}
                if option_groups is not None
                else {}
            ),
            **({"placeholder": placeholder} if placeholder else {}),
            **({"initial_option": initial_option} if initial_option else {}),
            **({"confirm": confirm} if confirm else {}),
            **(
                {"focus_on_load": focus_on_load}
                if focus_on_load is not None
                else {}
            ),
        }

        return select_menu

    def make_text_object(
        self,
        text_type: str,
        text: str,
        emoji: Optional[bool] = None,
        verbatim: Optional[bool] = None,
    ) -> dict[str, Any]:
        r"""Creates a Slack Block Kit text object.

        Args:
            text_type (str): The type of text object.
            text (str): The text content.
            emoji (Optional[bool], optional): Only for plain_text. Indicates
                whether emojis in a text field should be escaped into the
                colon emoji format. Defaults to :obj:`None`.
            verbatim (Optional[bool], optional): Only for mrkdwn. When set
                to true, any markup formatting will be ignored.
                Defaults to :obj:`None`.

        Returns:
            dict: A dictionary representing a Slack Block Kit text object.
        """

        if text_type not in ("plain_text", "mrkdwn"):
            raise ValueError(
                "text_type must be either 'plain_text' or 'mrkdwn'."
            )

        if not (1 <= len(text) <= 3000):
            raise ValueError(
                "The text length must be between 1 and 3000 characters."
            )

        obj: dict[str, Any] = {
            "type": text_type,
            "text": text,
        }
        if text_type == "plain_text" and emoji is not None:
            obj["emoji"] = emoji
        if text_type == "mrkdwn" and verbatim is not None:
            obj["verbatim"] = verbatim

        return obj

    def make_plain_text_input(
        self,
        action_id: Optional[str] = None,
        multiline: bool = False,
        placeholder: Optional[dict] = None,
        initial_value: Optional[str] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        dispatch_action_config: Optional[dict] = None,
        focus_on_load: bool = False,
    ) -> dict:
        r"""Creates a plain text input field for Slack Block Kit.

        Args:
            action_id (Optional[str], optional): A unique identifier for the
                input field action. Defaults to :obj:`None`.
            multiline (bool): Whether the input field should support multiple
                lines. Defaults to :obj:`False`.
            placeholder (Optional[dict], optional): Placeholder text to
                display in the input field. Defaults to :obj:`None`.
            initial_value (Optional[str], optional): The initial value of the
                input. Defaults to :obj:`None`.
            min_length (Optional[int], optional): Minimum input length.
                Defaults to :obj:`None`.
            max_length (Optional[int], optional): Maximum input length.
                Defaults to :obj:`None`.
            dispatch_action_config (Optional[dict], optional): Dispatch action
                config. Defaults to :obj:`None`.
            focus_on_load (bool): Whether to focus on load.
                Defaults to :obj:`False`.

        Returns:
            dict: A dictionary representing a Slack Block Kit plain text input
                element.

        Raises:
            ValueError: If any of the provided arguments are invalid.
        """

        if action_id is not None and len(action_id) > 255:
            raise ValueError("The action_id cannot exceed 255 characters.")

        if placeholder is not None:
            if placeholder.get("type") != "plain_text":
                raise ValueError(
                    "The placeholder text object must be of type "
                    "'plain_text', not 'mrkdwn'."
                )
            if len(placeholder.get("text", "")) > 150:
                raise ValueError(
                    "The placeholder text cannot exceed 150 characters."
                )

        if min_length is not None:
            if not (0 <= min_length <= 3000):
                raise ValueError(
                    "The min_length must be between 0 and 3000 " "(inclusive)."
                )

        if max_length is not None:
            if not (1 <= max_length <= 3000):
                raise ValueError(
                    "The max_length must be between 1 and 3000 " "(inclusive)."
                )

        return {
            "type": "plain_text_input",
            "multiline": multiline,
            "focus_on_load": focus_on_load,
            **(
                {"placeholder": placeholder} if placeholder is not None else {}
            ),
            **({"action_id": action_id} if action_id is not None else {}),
            **(
                {"initial_value": initial_value}
                if initial_value is not None
                else {}
            ),
            **({"min_length": min_length} if min_length is not None else {}),
            **({"max_length": max_length} if max_length is not None else {}),
            **(
                {"dispatch_action_config": dispatch_action_config}
                if dispatch_action_config is not None
                else {}
            ),
        }

    def make_date_picker(
        self,
        action_id: Optional[str] = None,
        placeholder: Optional[dict] = None,
        initial_date: Optional[str] = None,
        confirm: Optional[dict] = None,
        focus_on_load: bool = False,
    ) -> dict:
        r"""Creates a date picker for Slack Block Kit.

        Args:
            action_id (Optional[str], optional): A unique identifier for the
                date picker action. Defaults to :obj:`None`.
            placeholder (Optional[dict], optional): Placeholder text to
                display when no date is selected. Defaults to :obj:`None`.
            initial_date (Optional[str], optional): The initial date to
                display (YYYY-MM-DD format). Defaults to :obj:`None`.
            confirm (Optional[dict], optional): A confirm object for
                confirmation dialog. Defaults to :obj:`None`.
            focus_on_load (bool): Whether to focus on load.
                Defaults to :obj:`False`.

        Returns:
            dict: A dictionary representing a Slack Block Kit date picker
                element.

        Raises:
            ValueError: If any of the provided arguments are invalid.
        """
        if action_id is not None and len(action_id) > 255:
            raise ValueError("The action_id cannot exceed 255 characters.")

        if placeholder is not None:
            if placeholder.get("type") != "plain_text":
                raise ValueError(
                    "The placeholder text object must be of type "
                    "'plain_text', not 'mrkdwn'."
                )
            if len(placeholder.get("text", "")) > 150:
                raise ValueError(
                    "The placeholder text cannot exceed 150 characters."
                )

        if initial_date is not None:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', initial_date):
                raise ValueError(
                    "The initial_date must be in YYYY-MM-DD format."
                )

        return {
            "type": "datepicker",
            "focus_on_load": focus_on_load,
            **({"action_id": action_id} if action_id is not None else {}),
            **(
                {"placeholder": placeholder} if placeholder is not None else {}
            ),
            **({"initial_date": initial_date} if initial_date else {}),
            **({"confirm": confirm} if confirm is not None else {}),
        }

    def make_slack_file_object(
        self,
        file_id: Optional[str] = None,
        url: Optional[str] = None,
    ) -> dict:
        r"""Creates a minimal Slack file object dictionary for use in Block
            Kit.

        Args:
            file_id (Optional[str], optional): The unique Slack file ID.
                Defaults to :obj:`None`.
            url (Optional[str], optional): The private URL to access the
                file. Defaults to :obj:`None`.

        Returns:
            dict: A dictionary representing a Slack file object.
        """
        return {
            **({"id": file_id} if file_id else {}),
            **({"url": url} if url else {}),
        }

    def make_image(
        self,
        alt_text: str,
        image_url: Optional[str] = None,
        slack_file: Optional[str] = None,
    ) -> dict:
        r"""Creates an image block for Slack Block Kit.

        Args:
            alt_text (str): Alternative text for accessibility.
            image_url (Optional[str], optional): The URL of the image to
                display. Defaults to :obj:`None`.
            slack_file (Optional[str], optional): The Slack file ID
                associated with the image. Defaults to :obj:`None`.

        Returns:
            dict: A dictionary representing a Slack Block Kit image element.

        Raises:
            ValueError: If both image_url and slack_file are provided.
            ValueError: If image_url exceeds 3000 characters.
        """
        if image_url is not None and len(image_url) > 3000:
            raise ValueError("Image URL cannot exceed 3000 characters.")

        if image_url is not None and slack_file is not None:
            raise ValueError(
                "Only one of image_url or slack_file can be provided, "
                "not both."
            )

        return {
            "type": "image",
            "alt_text": alt_text,
            **({"image_url": image_url} if image_url else {}),
            **({"slack_file": slack_file} if slack_file else {}),
        }

    def delete_slack_message(
        self,
        time_stamp: str,
        channel_id: str,
    ) -> str:
        r"""Delete a message to a Slack channel.

        Args:
            time_stamp (str): Timestamp of the message to be deleted.
            channel_id (str): The ID of the Slack channel to delete message.

        Returns:
            str: A confirmation message indicating whether the message
                was delete successfully or an error message.

        Raises:
            SlackApiError: If an error occurs while sending the message.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            response = slack_client.chat_delete(
                channel=channel_id, ts=time_stamp
            )
            return str(response)
        except SlackApiError as e:
            return f"Error creating conversation: {e.response['error']}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.create_slack_channel),
            FunctionTool(self.join_slack_channel),
            FunctionTool(self.leave_slack_channel),
            FunctionTool(self.get_slack_channel_information),
            FunctionTool(self.get_slack_channel_message),
            FunctionTool(self.send_slack_message),
            FunctionTool(self.delete_slack_message),
            FunctionTool(self.make_button),
            FunctionTool(self.make_select_menu),
            FunctionTool(self.make_plain_text_input),
            FunctionTool(self.make_date_picker),
            FunctionTool(self.make_image),
            FunctionTool(self.make_option),
            FunctionTool(self.make_confirm_object),
            FunctionTool(self.make_option_group),
            FunctionTool(self.make_text_object),
            FunctionTool(self.make_slack_file_object),
        ]
