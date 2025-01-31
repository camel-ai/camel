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
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import MinerUToolkit
from camel.types import ModelPlatformType, ModelType

# Initialize the MinerUToolkit
mineru_toolkit = MinerUToolkit()

# Example 1: Direct toolkit usage
print("Example 1: Direct toolkit usage")
batch_id = mineru_toolkit.submit_batch_extraction(
    urls=[
        "https://www.camel-ai.org/about",
        "https://en.wikipedia.org/wiki/Autonomous_agent",
    ]
)
print(f"Batch ID: {batch_id}")

status = mineru_toolkit.get_batch_status(batch_id=batch_id)
print(f"Batch Status: {status}")

# Example 2: Using with ChatAgent
print("\nExample 2: Using with ChatAgent")

# Set up the agent
sys_msg = BaseMessage.make_assistant_message(
    role_name="Document Extractor",
    content=(
        "You are a helpful assistant that can extract text from documents."
    ),
)
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
)

agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=mineru_toolkit.get_tools(),
)

# Example extraction request
usr_msg = BaseMessage.make_user_message(
    role_name="User",
    content="""Please extract text from this document: https://www.camel-ai.org/about
    and tell me what it's about.""",
)

response = agent.step(usr_msg)
print("\nAgent Response:")
print(response.msg.content)

"""

"""
