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
from camel.memories import MemantoMemory, ScoreBasedContextCreator
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


def run_memanto_memory_example() -> None:
    r"""Use Memanto as automatic long-term memory for a ChatAgent.

    Prerequisites:
        1. Install Memanto: ``pip install memanto``.
        2. Start the server: ``memanto serve``.
        3. Create an agent: ``memanto agent create my-camel-agent``.
        4. Set OPENAI_API_KEY for the default ChatAgent model.
    """
    memory = MemantoMemory(
        context_creator=ScoreBasedContextCreator(
            token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
            token_limit=4096,
        ),
        agent_id="my-camel-agent",
        base_url="http://localhost:8000",
        retrieve_limit=3,
    )
    try:
        agent = ChatAgent(
            system_message="You are a helpful assistant.",
            agent_id="my-camel-agent",
            memory=memory,
        )
        response = agent.step("I prefer concise Python examples.")
        print(response.msgs[0].content)

        # Current chat history is reset; Memanto's archive remains available.
        agent.reset()
        response = agent.step("What coding examples do I prefer?")
        print(response.msgs[0].content)
    finally:
        memory.close()


if __name__ == "__main__":
    run_memanto_memory_example()
