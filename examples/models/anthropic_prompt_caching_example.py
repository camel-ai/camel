# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

"""
Anthropic Prompt Caching Example

This example demonstrates how to use Anthropic's prompt caching (via the
`cache_control` parameter) in CAMEL, and how it can reduce prompt token
usage and latency when you repeatedly send a large shared context.

Usage:
    export ANTHROPIC_API_KEY="your-api-key-here"
    python -m examples.models.anthropic_prompt_caching_example
"""

import textwrap
import time

from camel.agents import ChatAgent
from camel.configs import AnthropicConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def build_long_shared_context() -> str:
    r"""Build a relatively long shared context to better observe
    prompt caching effects.

    In real use cases you would put a long document here, such as
    a product spec, API reference, or knowledge base article.
    """
    base_paragraph = textwrap.dedent(
        """
        CAMEL-AI is an open-source framework for building autonomous,
        communicative AI agents and multi-agent systems. It provides
        abstractions for agents, tools, memories, environments, and
        workflows, making it easy to prototype and deploy complex AI
        systems in production.

        In this example we simulate a long reference document by
        repeating this paragraph multiple times. This makes the prompt
        large enough that Anthropic's prompt caching can have a
        noticeable impact on prompt token usage and latency when the
        same context is reused across multiple requests.
        """
    ).strip()

    # Repeat the paragraph to simulate a large document.
    return "\n\n".join(f"[Section {i+1}]\n{base_paragraph}" for i in range(20))


def ask_with_agent(
    agent: ChatAgent,
    shared_context: str,
    question: str,
) -> None:
    r"""Send one question with the shared context and print usage stats."""
    user_msg = f"Question: {question}"

    start_time = time.time()
    response = agent.step(shared_context)
    response = agent.step(user_msg)
    elapsed = time.time() - start_time

    usage = response.info.get("usage", {}) or {}

    print("-" * 80)
    print(f"Question: {question}")
    print(f"Latency: {elapsed:.2f}s")
    print(f"Usage: {usage}")
    print("Assistant:", response.msgs[0].content[:300], "...\n")


def main() -> None:
    # Please set the environment variable:
    # export ANTHROPIC_API_KEY="your-api-key-here"

    shared_context = build_long_shared_context()
    system_message = "You are a helpful assistant that provides detailed and informative responses."  # noqa: E501

    # Common model config
    model_config = AnthropicConfig(
        temperature=0.2,
        max_tokens=512,
    ).as_dict()

    # Model WITHOUT prompt caching
    model_no_cache = ModelFactory.create(
        model_platform=ModelPlatformType.ANTHROPIC,
        model_type=ModelType.CLAUDE_SONNET_4_5,
        model_config_dict=model_config,
    )

    # Model WITH prompt caching enabled (cache shared context for 5 minutes)
    model_with_cache = ModelFactory.create(
        model_platform=ModelPlatformType.ANTHROPIC,
        model_type=ModelType.CLAUDE_SONNET_4_5,
        model_config_dict=model_config,
        cache_control="5m",
    )

    agent_no_cache = ChatAgent(
        system_message=system_message,
        model=model_no_cache,
    )
    agent_with_cache = ChatAgent(
        system_message=system_message,
        model=model_with_cache,
    )

    questions = [
        "Summarize the core objectives and main functionalities of this document.",  # noqa: E501
        "List three typical use cases for CAMEL-AI based on the document content.",  # noqa: E501
        "What are the things I need to pay attention to if I want to deploy a multi-agent system in a production environment based on this document?",  # noqa: E501
    ]

    print("=" * 80)
    print("Anthropic Prompt Caching Demo (WITHOUT cache_control)")
    print("=" * 80)
    for q in questions:
        agent_no_cache.reset()
        ask_with_agent(agent_no_cache, shared_context, q)

    print("\n" + "=" * 80)
    print("Anthropic Prompt Caching Demo (WITH cache_control='5m')")
    print("=" * 80)
    for q in questions:
        agent_with_cache.reset()
        ask_with_agent(agent_with_cache, shared_context, q)

    print(
        "\nExplanation:\n"
        "- The first group of calls does not enable prompt caching, so each time the full length of the document's prompt tokens is counted.\n"  # noqa: E501
        "- The second group of calls enables Anthropic's prompt caching by `cache_control='5m'`.\n"  # noqa: E501
        "  In the case of repeated use of the same long document, you should see that the `prompt_tokens` and latency (Latency) of the latter requests are significantly lower than the first group.\n"  # noqa: E501
    )


if __name__ == "__main__":
    main()
