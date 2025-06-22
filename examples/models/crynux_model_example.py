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
from camel.toolkits import SearchToolkit
from camel.types import ModelPlatformType, ModelType

"""
please set the below os environment:
export CRYNUX_API_KEY="your key"

We offer an API key for testing (rate limit = 0.1):
Rfx0SUNqUBovo5MZpArUbzIT3dJpm2JyEd7-6SgikW4=
"""

model = ModelFactory.create(
    model_platform=ModelPlatformType.CRYNUX,
    model_type=ModelType.CRYNUX_QWEN_2_5_7B_INSTRUCT,
    model_config_dict={"temperature": 0.0},
)

search_tool = SearchToolkit().search_duckduckgo

agent = ChatAgent(model=model, tools=[search_tool])

response_1 = agent.step("What is CAMEL-AI?")
print(response_1.msgs[0].content)
"""
CAMEL-AI is a platform designed for building and researching
 intelligent agents and multi-agent systems. This platform
 is useful for data generation, world simulation, and task
 automation. It provides tools, projects, and resources for
 creating agentic applications using large language models
 and other AI/ML technologies.
"""

response_2 = agent.step("What is the Github link to CAMEL framework?")
print(response_2.msgs[0].content)
"""
The GitHub link to the CAMEL framework is:
[https://github.com/camel-ai/camel](https://github.com/
camel-ai/camel)
"""
