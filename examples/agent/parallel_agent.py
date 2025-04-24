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
import asyncio

from camel.agents import ChatAgent
from camel.agents.parallel_agent import ParallelAgent
from camel.models import ModelFactory
from camel.toolkits import FunctionTool, SearchToolkit
from camel.types import ModelPlatformType, ModelType


def make_agent(name, prompt, tools=None):
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_2_0_FLASH,
    )
    return ChatAgent(prompt, model, tools=tools)


chat_agent1 = make_agent("Agent 1", "you are a helpful agent")
chat_agent2 = make_agent("Agent 2", "you are a helpful agent")
chat_agent3 = make_agent(
    "Web Agent",
    "you are a browser search agent for user queries",
    tools=[FunctionTool(SearchToolkit().search_brave)],
)

parallel_agent = ParallelAgent(
    {"Web Agent": chat_agent3, "Agent 2": chat_agent2, "Agent 1": chat_agent1}
)
parallel_agent.reset()


async def main():
    # Run the parallel agent with a sample input message
    respond = await parallel_agent.step("what is camel-ai")
    print(respond)


if __name__ == "__main__":
    asyncio.run(main())
