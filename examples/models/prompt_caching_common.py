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

"""Shared helpers for prompt caching examples."""

import textwrap
import time
from typing import List

from camel.agents import ChatAgent


def build_long_shared_context() -> str:
    r"""Build a long shared context to observe prompt caching effects.

    Different providers have different minimum token requirements:
    - Anthropic: Varies by model (1024-4096 tokens)
    - OpenAI: 1024 tokens minimum
    - Azure OpenAI: 1024 tokens minimum
    """
    base_paragraph = textwrap.dedent(
        """
        CAMEL-AI is an open-source framework for building autonomous,
        communicative AI agents and multi-agent systems. It provides
        comprehensive abstractions for agents, tools, memories, environments,
        and workflows, making it straightforward to prototype and deploy
        complex AI systems in production environments.

        The framework supports multiple LLM backends including OpenAI,
        Azure OpenAI, Anthropic Claude, Google Gemini, and many more.
        This flexibility allows developers to choose the best model for
        their specific use case while maintaining a consistent API.

        Key features include multi-agent conversation systems, tool use
        and function calling, memory and context management, workflow
        orchestration, and an extensible architecture that adapts to
        various use cases from simple chatbots to complex autonomous agents.
        """
    ).strip()

    # Repeat to create context large enough for provider cache thresholds.
    # Some Gemini models require >=4096 tokens for explicit caching.
    return "\n\n".join(f"[Section {i+1}]\n{base_paragraph}" for i in range(32))


def get_questions() -> List[str]:
    return [
        "What is CAMEL-AI and what are its main features?",
        "Which LLM backends does CAMEL-AI support?",
        "How can CAMEL-AI help with multi-agent systems?",
    ]


def get_system_message() -> str:
    return (
        "You are a helpful assistant. Provide concise responses "
        "based on the provided context."
    )


def ask_with_agent(
    agent: ChatAgent,
    shared_context: str,
    question: str,
    request_num: int,
) -> None:
    r"""Send a question with shared context and display caching statistics."""
    user_msg = f"Question: {question}"

    start_time = time.time()
    response = agent.step(shared_context + "\n\n" + user_msg)
    elapsed = time.time() - start_time

    usage = response.info.get("usage", {}) or {}

    print("-" * 70)
    print(f"Request #{request_num}: {question[:50]}...")
    print(f"Latency: {elapsed:.2f}s")
    print(f"Usage: {usage}")
    print(f"Response: {response.msgs[0].content[:150]}...")
