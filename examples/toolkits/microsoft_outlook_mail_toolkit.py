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
import asyncio

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import OutlookMailToolkit
from camel.types import ModelPlatformType
from camel.types.enums import ModelType

# Create a model instance
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Define system message for the Outlook assistant
sys_msg = (
    "You are a helpful Microsoft Outlook assistant that can help users manage "
    "their emails. You have access to all Outlook tools including sending "
    "emails, fetching emails, managing drafts, and more."
)

# Initialize the Outlook toolkit
print("Initializing Outlook toolkit (browser may open for authentication)...")
outlook_toolkit = OutlookMailToolkit()
print("Outlook toolkit initialized!")

# Get all Outlook tools
all_tools = outlook_toolkit.get_tools()
print(f"Loaded {len(all_tools)} Outlook tools")

# Initialize a ChatAgent with all Outlook tools
outlook_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=all_tools,
)


async def main():
    print("\nExample: Sending an email")
    print("=" * 50)

    user_message = (
        "Send an email to test@example.com with subject "
        "'Hello from Outlook Toolkit' and body 'This is a test email "
        "sent using the CAMEL Outlook toolkit.'"
    )

    response = await outlook_agent.astep(user_message)
    print("Agent Response:")
    print(response.msgs[0].content)
    print("\nTool calls:")
    print(response.info['tool_calls'])


asyncio.run(main())
"""
Example: Sending an email
==================================================
Agent Response:
Done  your message has been sent to test@example.com.

Tool calls:
[ToolCallingRecord(
    tool_name='outlook_send_email',
    args={
        'to_email': ['test@example.com'],
        'subject': 'Hello from Outlook Toolkit',
        'content': 'This is a test email sent using the CAMEL toolkit.',
        'is_content_html': False,
        'attachments': None,
        'cc_recipients': None,
        'bcc_recipients': None,
        'reply_to': None,
        'save_to_sent_items': True
    },
    result={
        'status': 'success',
        'message': 'Email sent successfully',
        'recipients': ['test@example.com'],
        'subject': 'Hello from Outlook Toolkit'
    },
    tool_call_id='call_abc123',
    images=None
)]
"""
