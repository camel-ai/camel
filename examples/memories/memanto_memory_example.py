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

from camel.memories import (
    ChatHistoryMemory,
    MemoryRecord,
    ScoreBasedContextCreator,
)
from camel.messages import BaseMessage
from camel.storages import MemantoStorage
from camel.types import ModelType, OpenAIBackendRole
from camel.utils import OpenAITokenCounter


def run_memanto_memory_example() -> None:
    r"""Demonstrates ChatHistoryMemory backed by Memanto storage.

    Prerequisites:
        1. Install Memanto: ``pip install memanto``
        2. Start the server: ``memanto serve``
        3. Create the agent once: ``memanto agent create my-camel-agent``
    """
    memory = ChatHistoryMemory(
        context_creator=ScoreBasedContextCreator(
            token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
            token_limit=1024,
        ),
        storage=MemantoStorage(
            agent_id="my-camel-agent",
            base_url="http://localhost:8000",
        ),
        agent_id="my-camel-agent",
    )

    records = [
        MemoryRecord(
            message=BaseMessage.make_user_message(
                role_name="User",
                meta_dict=None,
                content="What is CAMEL AI?",
            ),
            role_at_backend=OpenAIBackendRole.USER,
        ),
        MemoryRecord(
            message=BaseMessage.make_assistant_message(
                role_name="Agent",
                meta_dict=None,
                content=(
                    "CAMEL-AI.org is the 1st LLM multi-agent framework and "
                    "an open-source community dedicated to finding the "
                    "scaling law of agents."
                ),
            ),
            role_at_backend=OpenAIBackendRole.ASSISTANT,
        ),
    ]
    memory.write_records(records)

    context, token_count = memory.get_context()
    print(f"Retrieved context (token count: {token_count}):")
    for message in context:
        print(message)


if __name__ == "__main__":
    run_memanto_memory_example()
