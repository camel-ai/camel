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

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.toolkits import SlackToolkit
from camel.types import ModelPlatformType, ModelType

# Initialize logger
logger = get_logger(__name__)

# Define system message
sys_msg = """You are a helpful Slack messaging assistant that can create 
interactive Block Kit messages and send them to Slack channels."""

# Set model config
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Initialize SlackToolkit with the model
slack_toolkit = SlackToolkit(model=model)
tools = slack_toolkit.get_tools()

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

usr_msg_1 = "Create a feedback form with a text input field, radio buttons for rating, checkboxes for categories, and a submit button"

response_1 = camel_agent.step(usr_msg_1)
logger.info("=== Block Kit Creation Response ===")
logger.info(response_1.info['tool_calls'])
logger.info("=" * 50)

# ruff: noqa: E501
"""
===============================================================================
=== Block Kit Creation Response ===
[
    ToolCallingRecord(
        tool_name='create_slack_block_kit',
        args={
            'message': 'Create a feedback form with a text input field, radio buttons for rating, checkboxes for categories, and a submit button'
        },
        result='''{
            "blocks": [
                {
                    "type": "plain_text_input",
                    "action_id": "feedback_text",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Please share your feedback here...",
                        "emoji": true
                    },
                    "multiline": true
                },
                {
                    "type": "radio_buttons",
                    "action_id": "rating",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Excellent",
                                "emoji": true
                            },
                            "value": "excellent"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Good",
                                "emoji": true
                            },
                            "value": "good"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Fair",
                                "emoji": true
                            },
                            "value": "fair"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Poor",
                                "emoji": true
                            },
                            "value": "poor"
                        }
                    ]
                },
                {
                    "type": "checkboxes",
                    "action_id": "categories",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "User Experience",
                                "emoji": true
                            },
                            "value": "ux"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Performance",
                                "emoji": true
                            },
                            "value": "performance"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Features",
                                "emoji": true
                            },
                            "value": "features"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Documentation",
                                "emoji": true
                            },
                            "value": "documentation"
                        }
                    ]
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Submit Feedback",
                        "emoji": true
                    },
                    "style": "primary",
                    "action_id": "submit_feedback"
                }
            ]
        }''',
        tool_call_id='call_abc123'
    )
]

==================================================

=== Send Slack Message Example ===
Channel Info: [
    ToolCallingRecord(
        tool_name='get_slack_channel_information',
        args={},
        result='''Available channels: [
            {
                "id": "C1234567890",
                "name": "general",
                "is_private": false
            },
            {
                "id": "C0987654321",
                "name": "random",
                "is_private": false
            }
        ]''',
        tool_call_id='call_def456'
    )
]

Send Response: [
    ToolCallingRecord(
        tool_name='send_slack_message',
        args={
            'channel_id': 'C1234567890',
            'blocks': '''[
                {
                    "type": "plain_text_input",
                    "action_id": "feedback_text",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Please share your feedback here...",
                        "emoji": true
                    },
                    "multiline": true
                },
                {
                    "type": "radio_buttons",
                    "action_id": "rating",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Excellent",
                                "emoji": true
                            },
                            "value": "excellent"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Good",
                                "emoji": true
                            },
                            "value": "good"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Fair",
                                "emoji": true
                            },
                            "value": "fair"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Poor",
                                "emoji": true
                            },
                            "value": "poor"
                        }
                    ]
                },
                {
                    "type": "checkboxes",
                    "action_id": "categories",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "User Experience",
                                "emoji": true
                            },
                            "value": "ux"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Performance",
                                "emoji": true
                            },
                            "value": "performance"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Features",
                                "emoji": true
                            },
                            "value": "features"
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Documentation",
                                "emoji": true
                            },
                            "value": "documentation"
                        }
                    ]
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Submit Feedback",
                        "emoji": true
                    },
                    "style": "primary",
                    "action_id": "submit_feedback"
                }
            ]''',
            'fallback_text': 'Feedback Form'
        },
        result=(
            'Message sent successfully to channel C1234567890. '
            'Message timestamp: 1703123456.789'
        ),
        tool_call_id='call_ghi789'
    )
]

The Slack message has been successfully sent to the #general channel with 
the interactive feedback form containing text input, radio buttons, checkboxes, and a submit button.
===============================================================================
"""
