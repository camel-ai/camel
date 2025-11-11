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
from camel.models import ModelFactory
from camel.toolkits import GmailToolkit
from camel.types import ModelPlatformType
from camel.types.enums import ModelType

# Create a model instance
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Define system message for the Gmail assistant
sys_msg = (
    "You are a helpful Gmail assistant that can help users manage their "
    "emails. You have access to all Gmail tools including sending emails, "
    "fetching emails, managing labels, and more."
)

# Initialize the Gmail toolkit
print("🔐 Initializing Gmail toolkit (browser may open for authentication)...")
gmail_toolkit = GmailToolkit()
print("✓ Gmail toolkit initialized!")

# Get all Gmail tools
all_tools = gmail_toolkit.get_tools()
print(f"✓ Loaded {len(all_tools)} Gmail tools")

# Initialize a ChatAgent with all Gmail tools
gmail_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=all_tools,
)

# Example: Send an email
print("\nExample: Sending an email")
print("=" * 50)

user_message = (
    "Send an email to test@example.com with subject 'Hello from Gmail "
    "Toolkit' and body 'This is a test email sent using the CAMEL Gmail "
    "toolkit.'"
)

response = gmail_agent.step(user_message)
print("Agent Response:")
print(response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])

"""
Example: Sending an email
==================================================
Agent Response:
Done — your message has been sent to test@example.com. Message ID: 
1998015e3157fdee.

Tool calls:
[ToolCallingRecord(
    tool_name='send_email', 
    args={
        'to': 'test@example.com', 
        'subject': 'Hello from Gmail Toolkit', 
        'body': 'This is a test email sent using the CAMEL Gmail toolkit.', 
        'cc': None, 
        'bcc': None, 
        'attachments': None, 
        'is_html': False
    }, 
    result={
        'success': True, 
        'message_id': '1998015e3157fdee', 
        'thread_id': '1998015e3157fdee',
        'message': 'Email sent successfully'
    }, 
    tool_call_id='call_4VzMM1JkKjGN8J5rfT4wH2sF',
    images=None
)]
"""
