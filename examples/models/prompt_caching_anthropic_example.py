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

"""Anthropic prompt caching demo."""

import os

from camel.agents import ChatAgent
from camel.configs import AnthropicConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from examples.models.prompt_caching_common import (
    ask_with_agent,
    build_long_shared_context,
    get_questions,
    get_system_message,
)


def run_anthropic_demo(shared_context: str, questions: list) -> None:
    r"""Demonstrate Anthropic Claude prompt caching."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Skipping Anthropic demo: ANTHROPIC_API_KEY not set")
        return

    print("\n" + "=" * 70)
    print("ANTHROPIC CLAUDE - Prompt Caching Demo")
    print("=" * 70)
    print("Using cache_control='5m' for 5-minute cache TTL")
    print()

    system_message = get_system_message()

    # Without cache_control
    print(">>> Without cache_control:")
    model_no_cache = ModelFactory.create(
        model_platform=ModelPlatformType.ANTHROPIC,
        model_type=ModelType.CLAUDE_SONNET_4_5,
        model_config_dict=AnthropicConfig(
            temperature=0.2,
            max_tokens=256,
        ).as_dict(),
    )
    agent_no_cache = ChatAgent(
        system_message=system_message, model=model_no_cache
    )

    for i, q in enumerate(questions[:2], 1):
        agent_no_cache.reset()
        ask_with_agent(agent_no_cache, shared_context, q, i)

    # With cache_control
    print("\n>>> With cache_control='5m':")
    model_with_cache = ModelFactory.create(
        model_platform=ModelPlatformType.ANTHROPIC,
        model_type=ModelType.CLAUDE_SONNET_4_5,
        model_config_dict=AnthropicConfig(
            temperature=0.2,
            max_tokens=256,
            cache_control="5m",
        ).as_dict(),
    )
    agent_with_cache = ChatAgent(
        system_message=system_message, model=model_with_cache
    )

    for i, q in enumerate(questions, 1):
        agent_with_cache.reset()
        ask_with_agent(agent_with_cache, shared_context, q, i)


def main() -> None:
    shared_context = build_long_shared_context()
    questions = get_questions()

    print("=" * 70)
    print("PROMPT CACHING DEMO")
    print("=" * 70)
    print(f"Context size: ~{len(shared_context.split())} words")

    run_anthropic_demo(shared_context, questions)


if __name__ == "__main__":
    main()
