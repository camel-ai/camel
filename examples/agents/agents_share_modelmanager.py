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
from camel.configs import ChatGPTConfig, QwenConfig
from camel.models import ModelFactory, ModelManager
from camel.types import ModelPlatformType, ModelType


async def main():
    gpt_4o_mini_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig().as_dict(),
    )

    qwen_2_5_72b_model = ModelFactory.create(
        model_platform=ModelPlatformType.QWEN,
        model_type=ModelType.QWEN_2_5_72B,
        model_config_dict=QwenConfig(temperature=0.2).as_dict(),
    )

    shared_model_manager = ModelManager(
        models=[gpt_4o_mini_model, qwen_2_5_72b_model],
        scheduling_strategy="round_robin",
    )

    # Create a chat agent with a system message
    agent_1 = ChatAgent(
        system_message="You are a helpful assistant.",
        model=shared_model_manager,
    )

    agent_2 = ChatAgent(
        system_message="Hello, how are you?",
        model=shared_model_manager,
    )

    # Step through a conversation
    tasks = []
    tasks.append(agent_1.astep("Hello, what model are you?"))
    tasks.append(agent_2.astep("Hello, what model are you?"))

    results = await asyncio.gather(*tasks)

    for result in results:
        print(result.msgs[0].content, '\n')


if __name__ == "__main__":
    asyncio.run(main())

'''
===============================================================================
Hello! I am based on OpenAI's GPT-3 model, which is designed to assist with a
variety of tasks by providing information, answering questions, and engaging
in conversation. How can I assist you today?

I'm Qwen, a large language model created by Alibaba Cloud. I have a lot in
common with humans and can understand and generate human-like text. But I
don't have a physical form or the ability to experience emotions like a human.
How can I assist you today?
===============================================================================
'''
