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

import os
import tempfile

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import DocumentToolkit
from camel.types import ModelPlatformType, ModelType

#Initialise the toolkit
doc_toolkit = DocumentToolkit()

# Create a model using OpenAI
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
)

# Create a chat agent with the Document toolkit
agent = ChatAgent(
    system_message=(
        "You are a helpful assistant that can read arbitrary documents. "
        "Use the provided DocumentToolkit to extract text."
    ),
    model=model,
    tools=[*doc_toolkit.get_tools()],
)

# Example: Ask the agent to extract the content
response = agent.step(
    f"Extract content in the document located at https://arxiv.org/pdf/1706.03762."
)

print(response.msgs[0].content)
