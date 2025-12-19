# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import LarkToolkit
from camel.types import ModelPlatformType, ModelType

# Initialize the LarkToolkit
# (auto-authenticates using cached tokens or browser)
# Requires LARK_APP_ID and LARK_APP_SECRET environment variables
toolkit = LarkToolkit()

# Create the model
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Create a ChatAgent with the Lark toolkit tools
agent = ChatAgent(
    system_message="You are a Lark document assistant.",
    model=model,
    tools=toolkit.get_tools(),
)

# Example 1: Document operations
print("=" * 60)
print("Example 1: Document Operations")
print("=" * 60)

response = agent.step(
    "Get my root folder, create a document called 'Weekly Status Report', "
    "add a heading 'Team Status Update', and show me the final content."
)
print(f"Agent response: {response.msgs[0].content}")

# Example 2: Messaging operations
print("\n" + "=" * 60)
print("Example 2: Messaging Operations")
print("=" * 60)

response = agent.step(
    "List my available chats, then send a message saying 'Hello from CAMEL!' "
    "to the first group chat you find."
)
print(f"Agent response: {response.msgs[0].content}")

"""
==========================================================================
Example 1 output:

I've completed all the tasks. Here's a summary:

1. **Root Folder**: Retrieved your root folder token.

2. **Document Created**: Created a new document called "Weekly Status Report"
   - Document URL: https://xxx.larksuite.com/docx/xxx

3. **Heading Added**: Added the heading "Team Status Update" to the document.

4. **Final Content**: The document now contains:
   - Title: Weekly Status Report
   - Heading: Team Status Update

You can access your new document using the link above.

==========================================================================
Example 2 output:

I've completed the messaging tasks:

1. **Listed Chats**: Found 3 chats you belong to:
   - "Engineering Team" (group)
   - "Project Alpha" (group)
   - "John Doe" (p2p)

2. **Message Sent**: Successfully sent "Hello from CAMEL!"
   to "Engineering Team"
   - Message ID: om_xxx
   - Chat ID: oc_xxx

==========================================================================
"""
