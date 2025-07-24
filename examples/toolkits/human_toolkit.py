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
from camel.models import ModelFactory
from camel.toolkits import MathToolkit, SearchToolkit
from camel.types import ModelPlatformType, ModelType

search_toolkit = SearchToolkit().search_wiki

math_toolkit = MathToolkit().get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(
        temperature=0.0,
    ).as_dict(),
)

# Example 1: Test Agent with the human toolkit (ask_human_via_console)
print("\nExample 1: Using ask_human_via_console through an agent")
agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
    tools=[search_toolkit, *math_toolkit],
)

response = agent.step(
    "search what is the capital of France, what is the capital of Japan, what is the capital of China, calculate 1+1, 2+2, 3+3, 4+4, 5+5, 6+6, 7+7, 8+8, 9+9, 10+10"
)

print(response.msgs[0].content)

"""
==========================================================================
What is the capital of France?
Your reply: Paris

That's correct! Paris is indeed the capital of France. Would you like to try
another one?
Your reply: yes

What is the capital of Japan?
Your reply: Tokyo

That's correct! Tokyo is the capital of Japan. Would you like to continue with
another question?
Your reply: no
==========================================================================
"""
