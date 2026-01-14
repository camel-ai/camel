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

# Example 1: List all chats
print("=" * 60)
print("Example 1: List all chats the bot belongs to")
print("=" * 60)

response = agent.step("List all chats I belong to.")
print(f"Response: {response.msgs[0].content}\n")

# Example 2: Get messages from a specific chat
print("=" * 60)
print("Example 2: Get recent messages from a chat")
print("=" * 60)

response = agent.step(
    "Get the 5 most recent messages from the first chat, "
    "sorted by newest first."
)
print(f"Response: {response.msgs[0].content}\n")

# Example 3: Download a resource from a message
print("=" * 60)
print("Example 3: Download image/file from a message")
print("=" * 60)

response = agent.step(
    "If there are any images or files in the messages, "
    "get the resource key and download one of them."
)
print(f"Response: {response.msgs[0].content}\n")

# Example 4: Send a message to chat
print("=" * 60)
print("Example 4: Send a message to chat")
print("=" * 60)

response = agent.step("Say hi to my first chat ")
print(f"Response: {response.msgs[0].content}\n")

# Example 5: Direct toolkit usage (without agent)
print("=" * 60)
print("Example 5: Direct toolkit usage")
print("=" * 60)

# List chats directly
result = toolkit.lark_list_chats(page_size=10)
print(f"lark_list_chats result: {result}")
