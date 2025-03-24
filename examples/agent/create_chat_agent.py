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
from camel.types import ModelPlatformType, ModelType

# Method 1: Initialize the agent with just a string (model name)
# This uses the default platform (OpenAI)
agent_1 = ChatAgent("You are a helpful assistant.", model="gpt-4o-mini")

# Method 2: Initialize with just a `enum` for model type.
agent_2 = ChatAgent(
    "You are a helpful assistant.",
    model=ModelType.GPT_4O_MINI,
)

# Method 3: Initialize the agent with a tuple (platform, model)
agent_3 = ChatAgent(
    "You are a helpful assistant.",
    model=("anthropic", "claude-3-5-sonnet-latest"),
)

# Method 4: Initialize the agent with a `tuple` of `enum`
agent_4 = ChatAgent(
    "You are a helpful assistant.",
    model=(ModelPlatformType.ANTHROPIC, ModelType.CLAUDE_3_5_SONNET),
)

# Method 5: Default model when none is specified.
agent_5 = ChatAgent("You are a helpful assistant.")

# Method 6: Initialize with a pre-created model (original approach)
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,  # Using enum
    model_type=ModelType.GPT_4O_MINI,  # Using enum
)
agent_6 = ChatAgent("You are a helpful assistant.", model=model)

# Method 7: Initialize with a pre-created model using strings
model = ModelFactory.create(
    model_platform="openai",  # Using string
    model_type="gpt-4o-mini",  # Using string
)
agent_7 = ChatAgent("You are a helpful assistant.", model=model)


# Test with a simple question with agent3(Anthropic, claude-3-5-sonnet-latest)
user_msg = "Which model are you?"

# Get the response from one of the agents
response = agent_3.step(user_msg)
print("Response from agent3:")
print(response.msgs[0].content)
"""
Response from agent3:
I am Claude, an AI assistant created by Anthropic. I aim to be direct and honest about what I am.
"""  # noqa: E501
