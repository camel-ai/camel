# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import json
import os
from ssl import SSLContext
from typing import TYPE_CHECKING, List, Optional

from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer

if TYPE_CHECKING:
    from slack_sdk import WebClient

    from camel.agents import ChatAgent
    from camel.models import BaseModelBackend

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
        model: Optional["BaseModelBackend"] = None,
        timeout: Optional[float] = None,
    ):
        r"""Initializes a new instance of the SlackToolkit class.

        Args:
            model (Optional[BaseModelBackend]): The model backend to use for
                Block Kit generation. If provided, enables the advanced
                create_slack_block_kit method. (default: :obj:`None`)
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        # Initialize the agent for Block Kit generation
        # only if model is provided
        self.camel_agent: Optional["ChatAgent"]
        if model:
            from camel.agents import ChatAgent

            self.camel_agent = ChatAgent(
                system_message=self._get_system_message(),
                model=model,
            )
        else:
            self.camel_agent = None

    def _get_system_message(self) -> str:
        r"""Get the system message for the Block Kit generation agent."""
        return """You are a helpful Slack messaging assistant that
        can create Block Kit JSON.
                

    You can only use these valid block types in your Block Kit JSON:
    - button
    - checkboxes  
    - datepicker
    - datetime_picker
    - image
    - multi_select
    - overflow
    - plain_text_input
    - radio_buttons
    - select
    - timepicker
    - workflow_button

    Here are examples of how each block type should be formatted:

    1. BUTTON:
    {
    "type": "button",
    "text": {
        "type": "plain_text",
        "text": "Click me",
        "emoji": true
    },
    "action_id": "button_click",
    "value": "button_value"
    }

    2. CHECKBOXES:
    {
    "type": "checkboxes",
    "action_id": "checkboxes_action",
    "options": [
        {
        "text": {
            "type": "plain_text",
            "text": "Option 1",
            "emoji": true
        },
        "value": "option_1"
        }
    ]
    }

    3. DATEPICKER:
    {
    "type": "datepicker",
    "action_id": "date_picker",
    "placeholder": {
        "type": "plain_text",
        "text": "Select a date",
        "emoji": true
    }
    }

    4. DATETIME_PICKER:
    {
    "type": "datetime_picker",
    "action_id": "datetime_picker"
    }

    5. IMAGE:
    {
    "type": "image",
    "image_url": "https://example.com/image.jpg",
    "alt_text": "Description of image"
    }

    6. MULTI_SELECT:
    {
    "type": "multi_select",
    "action_id": "multi_select_action",
    "options": [
        {
        "text": {
            "type": "plain_text",
            "text": "Choice 1",
            "emoji": true
        },
        "value": "choice_1"
        }
    ]
    }

    7. OVERFLOW:
    {
    "type": "overflow",
    "action_id": "overflow_action",
    "options": [
        {
        "text": {
            "type": "plain_text",
            "text": "More options",
            "emoji": true
        },
        "value": "more_options"
        }
    ]
    }

    8. PLAIN_TEXT_INPUT:
    {
    "type": "plain_text_input",
    "action_id": "text_input",
    "placeholder": {
        "type": "plain_text",
        "text": "Enter text here",
        "emoji": true
    }
    }

    9. RADIO_BUTTONS:
    {
    "type": "radio_buttons",
    "action_id": "radio_action",
    "options": [
        {
        "text": {
            "type": "plain_text",
            "text": "Yes",
            "emoji": true
        },
        "value": "yes"
        }
    ]
    }

    10. SELECT:
    {
    "type": "select",
    "action_id": "select_action",
    "options": [
        {
        "text": {
            "type": "plain_text",
            "text": "Select 1",
            "emoji": true
        },
        "value": "select_1"
        }
    ]
    }

    11. TIMEPICKER:
    {
    "type": "timepicker",
    "action_id": "time_picker"
    }

    12. WORKFLOW_BUTTON:
    {
    "type": "workflow_button",
    "text": {
        "type": "plain_text",
        "text": "Start workflow",
        "emoji": true
    },
    "workflow": {
        "trigger": {
        "url": "https://example.com/workflow"
        }
    }
    }

    When sending messages, always use the proper Slack message format with
    a 'blocks' array:
    {
    "blocks": [
        // Your block objects go here
    ],
    "text": "Fallback text"
    }

    Remember: Each block must have a 'type' field and appropriate
    'action_id' fields where required.
    """

    def _login_slack(
        self,
        slack_token: Optional[str] = None,
        ssl: Optional[SSLContext] = None,
    ) -> "WebClient":
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
        r"""Joins an existing Slack channel. When use this function you must
        call `get_slack_channel_information` function first to get the
        `channel id`.

        Args:
            channel_id (str): The ID of the Slack channel to join.

        Returns:
            str: A string containing the API response from Slack.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            response = slack_client.conversations_join(channel=channel_id)
            return str(response)
        except SlackApiError as e:
            return f"Error joining channel: {e.response['error']}"

    def leave_slack_channel(self, channel_id: str) -> str:
        r"""Leaves an existing Slack channel. When use this function you must
        call `get_slack_channel_information` function first to get the
        `channel id`.

        Args:
            channel_id (str): The ID of the Slack channel to leave.

        Returns:
            str: A string containing the API response from Slack.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            response = slack_client.conversations_leave(channel=channel_id)
            return str(response)
        except SlackApiError as e:
            return f"Error leaving channel: {e.response['error']}"

    def get_slack_channel_information(self) -> str:
        r"""Retrieve a list of all public channels in the Slack workspace.

        This function is crucial for discovering available channels and their
        `channel_id`s, which are required by many other functions.

        Returns:
            str: A JSON string representing a list of channels. Each channel
                object in the list contains 'id', 'name', 'created', and
                'num_members'. Returns an error message string on failure.
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
            return f"Error retrieving channel list: {e.response['error']}"

    def get_slack_channel_message(self, channel_id: str) -> str:
        r"""Retrieve messages from a Slack channel. When use this function you
        must call `get_slack_channel_information` function first to get the
        `channel id`.

        Args:
            channel_id (str): The ID of the Slack channel to retrieve messages
                from.

        Returns:
            str: A JSON string representing a list of messages. Each message
                object contains 'user', 'text', and 'ts' (timestamp).
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
        blocks: Optional[str] = None,
    ) -> str:
        r"""Send a message to a Slack channel. When use this function you must
        call `get_slack_channel_information` function first to get the
        `channel id`. If use user, you must use `get_slack_user_list`
        function first to get the user id.

        Args:
            message (str): The message to send.
            channel_id (str): The ID of the channel to send the message to.
            file_path (Optional[str]): The local path of a file to upload
                with the message.
            user (Optional[str]): The ID of a user to send an ephemeral
                message to (visible only to that user).
            blocks (Optional[str]): A JSON string representing Slack Block Kit
                blocks for rich message formatting. The LLM should generate
                this JSON following Slack's Block Kit specification.

        Returns:
            str: A confirmation message indicating success or an error
                message.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()

            # Prepare message parameters
            message_params = {"channel": channel_id, "text": message}

            # Add blocks if provided
            if blocks:
                try:
                    blocks_data = json.loads(blocks)
                    message_params["blocks"] = blocks_data
                except json.JSONDecodeError:
                    return "Error: Invalid JSON format in blocks parameter"

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
                # Prepare parameters for chat_postMessage
                response = slack_client.chat_postMessage(
                    channel=channel_id, text=message, blocks=blocks
                )

            return (
                f"Message: {message} sent successfully, "
                f"got response: {response}"
            )
        except SlackApiError as e:
            return f"Error sending message: {e.response['error']}"

    def delete_slack_message(
        self,
        time_stamp: str,
        channel_id: str,
    ) -> str:
        r"""Delete a message from a Slack channel. When use this function you
        must call `get_slack_channel_information` function first to get the
        `channel id`.

        Args:
            time_stamp (str): The 'ts' value of the message to be deleted.
                You can get this from the `get_slack_channel_message` function.
            channel_id (str): The ID of the channel where the message is. Use
                `get_slack_channel_information` to find the `channel_id`.

        Returns:
            str: A string containing the API response from Slack.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            response = slack_client.chat_delete(
                channel=channel_id, ts=time_stamp
            )
            return str(response)
        except SlackApiError as e:
            return f"Error deleting message: {e.response['error']}"

    def create_slack_block_kit(
        self,
        message: str,
        max_retries: int = 3,
    ) -> str:
        r"""Create a Slack Block Kit JSON message based on the user's request.

        This method generates properly formatted Block Kit JSON and validates
        it. If validation fails, it retries up to max_retries times.

        Note: This method requires a model to be configured
        during initialization.

        Args:
            message (str): The user's request for creating a Block Kit
                message.
            max_retries (int, optional): Maximum number of retry attempts if
                validation fails. Defaults to 3.

        Returns:
            str: A JSON string containing the validated Block Kit blocks
                array, or an error message.
        """

        if self.camel_agent is None:
            return (
                "Error: Block Kit generation requires a model to be "
                "configured. Please initialize SlackToolkit with a model "
                "parameter."
            )

        def validate_block_kit_json(blocks_array):
            r"""Validate Block Kit JSON format using the same logic as the test
            file.

            Args:
                blocks_array: The Block Kit blocks array to validate.

            Returns:
                tuple: A tuple containing (is_valid, message) where is_valid
                    is a boolean indicating if the blocks array is valid, and
                    message is either "VALID" for valid blocks or an error
                    description for invalid blocks.
            """
            try:
                if not isinstance(blocks_array, list):
                    return False, "Blocks must be an array"

                if len(blocks_array) == 0:
                    return False, "Blocks array cannot be empty"

                errors = []

                for i, block in enumerate(blocks_array):
                    if not isinstance(block, dict):
                        errors.append(f"Block {i}: Must be an object")
                        continue

                    if 'type' not in block:
                        errors.append(
                            f"Block {i}: Missing required 'type' field"
                        )
                        continue

                    block_type = block['type']

                    # Validate based on block type
                    if block_type == 'button':
                        if 'text' not in block:
                            errors.append(
                                f"Block {i} (button): Missing required "
                                f"'text' field"
                            )
                        valid_params = {
                            'type',
                            'text',
                            'action_id',
                            'url',
                            'value',
                            'style',
                            'confirm',
                            'accessibility_label',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (button): Invalid parameters: "
                                f"{', '.join(invalid_params)}"
                            )

                    elif block_type == 'checkboxes':
                        if 'options' not in block:
                            errors.append(
                                f"Block {i} (checkboxes): Missing required "
                                f"'options' field"
                            )
                        valid_params = {
                            'type',
                            'action_id',
                            'options',
                            'initial_options',
                            'confirm',
                            'focus_on_load',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (checkboxes): Invalid parameters: "
                                f"{', '.join(invalid_params)}"
                            )

                    elif block_type == 'datepicker':
                        valid_params = {
                            'type',
                            'action_id',
                            'initial_date',
                            'confirm',
                            'focus_on_load',
                            'placeholder',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (datepicker): Invalid parameters: "
                                f"{', '.join(invalid_params)}"
                            )

                    elif block_type == 'datetime_picker':
                        valid_params = {
                            'type',
                            'action_id',
                            'initial_date_time',
                            'confirm',
                            'focus_on_load',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (datetime_picker): Invalid "
                                f"parameters: {', '.join(invalid_params)}"
                            )

                    elif block_type == 'image':
                        if 'alt_text' not in block:
                            errors.append(
                                f"Block {i} (image): Missing required "
                                f"'alt_text' field"
                            )
                        valid_params = {
                            'type',
                            'alt_text',
                            'image_url',
                            'slack_file',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (image): Invalid parameters: "
                                f"{', '.join(invalid_params)}"
                            )

                    elif block_type == 'multi_select':
                        if 'options' not in block:
                            errors.append(
                                f"Block {i} (multi_select): Missing required "
                                f"'options' field"
                            )
                        valid_params = {
                            'type',
                            'action_id',
                            'options',
                            'option_groups',
                            'initial_options',
                            'confirm',
                            'max_selected_items',
                            'focus_on_load',
                            'placeholder',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (multi_select): Invalid "
                                f"parameters: {', '.join(invalid_params)}"
                            )

                    elif block_type == 'overflow':
                        if 'options' not in block:
                            errors.append(
                                f"Block {i} (overflow): Missing required "
                                f"'options' field"
                            )
                        valid_params = {
                            'type',
                            'action_id',
                            'options',
                            'confirm',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (overflow): Invalid parameters: "
                                f"{', '.join(invalid_params)}"
                            )

                    elif block_type == 'plain_text_input':
                        valid_params = {
                            'type',
                            'action_id',
                            'initial_value',
                            'multiline',
                            'min_length',
                            'max_length',
                            'dispatch_action_config',
                            'focus_on_load',
                            'placeholder',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (plain_text_input): Invalid "
                                f"parameters: {', '.join(invalid_params)}"
                            )

                    elif block_type == 'radio_buttons':
                        if 'options' not in block:
                            errors.append(
                                f"Block {i} (radio_buttons): Missing required "
                                f"'options' field"
                            )
                        valid_params = {
                            'type',
                            'action_id',
                            'options',
                            'initial_option',
                            'confirm',
                            'focus_on_load',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (radio_buttons): Invalid "
                                f"parameters: {', '.join(invalid_params)}"
                            )

                    elif block_type == 'select':
                        if 'options' not in block:
                            errors.append(
                                f"Block {i} (select): Missing required "
                                f"'options' field"
                            )
                        valid_params = {
                            'type',
                            'action_id',
                            'options',
                            'option_groups',
                            'initial_option',
                            'confirm',
                            'focus_on_load',
                            'placeholder',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (select): Invalid parameters: "
                                f"{', '.join(invalid_params)}"
                            )

                    elif block_type == 'timepicker':
                        valid_params = {
                            'type',
                            'action_id',
                            'initial_time',
                            'confirm',
                            'focus_on_load',
                            'placeholder',
                            'timezone',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (timepicker): Invalid parameters: "
                                f"{', '.join(invalid_params)}"
                            )

                    elif block_type == 'workflow_button':
                        if 'text' not in block:
                            errors.append(
                                f"Block {i} (workflow_button): Missing "
                                f"required 'text' field"
                            )
                        if 'workflow' not in block:
                            errors.append(
                                f"Block {i} (workflow_button): Missing "
                                f"required 'workflow' field"
                            )
                        if 'action_id' not in block:
                            errors.append(
                                f"Block {i} (workflow_button): Missing "
                                f"required 'action_id' field"
                            )
                        valid_params = {
                            'type',
                            'text',
                            'workflow',
                            'action_id',
                            'style',
                            'accessibility_label',
                        }
                        invalid_params = set(block.keys()) - valid_params
                        if invalid_params:
                            errors.append(
                                f"Block {i} (workflow_button): Invalid "
                                f"parameters: {', '.join(invalid_params)}"
                            )

                if errors:
                    return False, "; ".join(errors)

                return True, "VALID"

            except Exception as e:
                return False, f"Validation error: {e!s}"

        # Reset the agent state for a fresh conversation
        self.camel_agent.reset()

        # Retry loop for generating and validating Block Kit JSON
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Attempt {attempt + 1}/{max_retries} to create Block Kit "
                    f"JSON"
                )

                # Generate Block Kit JSON using the agent
                response = self.camel_agent.step(
                    f"Create a Block Kit JSON message for: {message}. "
                    f"Return only the JSON blocks array or object with blocks "
                    f"field."
                )

                # Extract JSON from the response
                response_text = response.msg.content

                # Try to find JSON in the response
                import re

                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if not json_match:
                    logger.warning(
                        f"Attempt {attempt + 1}: No JSON found in response"
                    )
                    if attempt < max_retries - 1:
                        self.camel_agent.step(
                            "Please provide a valid JSON response with Block "
                            "Kit blocks."
                        )
                    continue

                json_str = json_match.group(0)

                # Parse the JSON
                try:
                    blocks_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Attempt {attempt + 1}: Invalid JSON format: {e}"
                    )
                    if attempt < max_retries - 1:
                        self.camel_agent.step(
                            f"The JSON format was invalid: {e}. Please "
                            f"provide valid JSON."
                        )
                    continue

                # Handle both array format and object with blocks format
                if isinstance(blocks_data, list):
                    blocks_array = blocks_data
                elif isinstance(blocks_data, dict) and 'blocks' in blocks_data:
                    blocks_array = blocks_data['blocks']
                else:
                    logger.warning(
                        f"Attempt {attempt + 1}: Unexpected JSON format"
                    )
                    if attempt < max_retries - 1:
                        self.camel_agent.step(
                            "Please provide a JSON array of blocks or an "
                            "object with a 'blocks' field."
                        )
                    continue

                # Validate the Block Kit JSON
                is_valid, validation_message = validate_block_kit_json(
                    blocks_array
                )

                if is_valid:
                    logger.info(
                        f"Block Kit JSON validated successfully on attempt "
                        f"{attempt + 1}"
                    )
                    # Return the validated JSON string
                    return json_str
                else:
                    logger.warning(
                        f"Attempt {attempt + 1}: Validation failed: "
                        f"{validation_message}"
                    )
                    if attempt < max_retries - 1:
                        # Provide feedback to the agent for the next attempt
                        self.camel_agent.step(
                            f"The previous Block Kit JSON was invalid: "
                            f"{validation_message}. "
                            f"Please fix the issues and try again."
                        )

            except Exception as e:
                logger.error(
                    f"Attempt {attempt + 1}: Error during Block Kit creation: "
                    f"{e}"
                )
                if attempt == max_retries - 1:
                    return (
                        f"Error creating Block Kit JSON after {max_retries} "
                        f"attempts: {e!s}"
                    )

        return (
            f"Failed to create valid Block Kit JSON after {max_retries} "
            f"attempts"
        )
    def get_slack_user_list(self) -> str:
        r"""Retrieve a list of all users in the Slack workspace.

        Returns:
            str: A JSON string representing a list of users. Each user
                object contains 'id', 'name'.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            response = slack_client.users_list()
            users = response["members"]
            filtered_users = [
                {
                    "id": user["id"],
                    "name": user["name"],
                }
                for user in users
            ]

            return json.dumps(filtered_users, ensure_ascii=False)
        except SlackApiError as e:
            return f"Error retrieving user list: {e.response['error']}"

    def get_slack_user_info(self, user_id: str) -> str:
        r"""Retrieve information about a specific user in the Slack workspace.
        normally, you don't need to use this method, when you need to get a
        user's detailed information, use this method. Use `get_slack_user_list`
        function first to get the user id.

        Args:
            user_id (str): The ID of the user to retrieve information about.

        Returns:
            str: A JSON string representing the user's information.
        """
        from slack_sdk.errors import SlackApiError

        try:
            slack_client = self._login_slack()
            response = slack_client.users_info(user=user_id)
            return json.dumps(response, ensure_ascii=False)
        except SlackApiError as e:
            return f"Error retrieving user info: {e.response['error']}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        tools = [
            FunctionTool(self.create_slack_channel),
            FunctionTool(self.join_slack_channel),
            FunctionTool(self.leave_slack_channel),
            FunctionTool(self.get_slack_channel_information),
            FunctionTool(self.get_slack_channel_message),
            FunctionTool(self.send_slack_message),
            FunctionTool(self.delete_slack_message),
            FunctionTool(self.get_slack_user_list),
            FunctionTool(self.get_slack_user_info),
        ]

        # Only include create_slack_block_kit if model is configured
        if self.camel_agent is not None:
            tools.append(FunctionTool(self.create_slack_block_kit))

        return tools
