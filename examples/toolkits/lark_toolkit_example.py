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
# Requires LARK_APP_ID and LARK_APP_SECRET environment variables
# Set use_feishu=True if using Feishu (China) instead of Lark (International)
toolkit = LarkToolkit()

# Create the model
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Create a ChatAgent with the Lark toolkit tools
agent = ChatAgent(
    system_message="You are a Lark messaging assistant.",
    model=model,
    tools=toolkit.get_tools(),
)

# Example: Chat and message operations
print("=" * 60)
print("Lark Toolkit Example: Chat and Message Operations")
print("=" * 60)

response = agent.step(
    "List all chats I belong to, get the recent messages from the first chat, "
    "and if there are any images or files, download one of them."
)
print(f"Agent response: {response.msgs[0].content}")

"""
==========================================================================
Example output:

I've completed the Lark messaging tasks. Here's a summary:

1. **Listed Chats**: Found 3 chats you belong to:
   - "Engineering Team" (group) - Chat ID: oc_xxx
   - "Project Alpha" (group) - Chat ID: oc_yyy
   - "John Doe" (p2p) - Chat ID: oc_zzz

2. **Retrieved Messages**: Got recent messages from "Engineering Team":
   - Found 15 messages in the chat
   - Messages include text discussions and file attachments

3. **Downloaded Resource**: Found and downloaded an image:
   - Message ID: om_xxx
   - File Key: img_v2_xxx
   - Content Type: image/png
   - Saved to: ./workspace/lark_file/img_v2_xxx

==========================================================================
"""
