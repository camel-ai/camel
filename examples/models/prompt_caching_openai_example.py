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

"""OpenAI prompt caching demo."""

import json
import os
from typing import Any, Optional

from camel.agents import ChatAgent
from camel.agents._utils import safe_model_dump
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from examples.models.prompt_caching_common import (
    ask_with_agent,
    build_long_shared_context,
    get_questions,
    get_system_message,
)


class RawChatAgent(ChatAgent):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.last_raw_response: Optional[Any] = None

    def _get_model_response(self, *args: Any, **kwargs: Any):  # type: ignore[override]
        model_response = super()._get_model_response(*args, **kwargs)
        self.last_raw_response = model_response.response
        return model_response


def _print_raw_response(agent: RawChatAgent) -> None:
    raw = agent.last_raw_response
    if raw is None:
        print("Raw response: <empty>")
        return

    try:
        raw_dict = safe_model_dump(raw)
    except Exception:
        raw_dict = str(raw)

    _print_cached_tokens(raw_dict)
    print("Raw response:")
    print(json.dumps(raw_dict, indent=2, ensure_ascii=False))


def _print_cached_tokens(raw_dict: Any) -> None:
    if not isinstance(raw_dict, dict):
        print("cached_tokens: N/A")
        return

    usage = raw_dict.get("usage", {})
    prompt_details = usage.get("prompt_tokens_details", {})
    cached_tokens = prompt_details.get("cached_tokens")
    if cached_tokens is None:
        print("cached_tokens: 0 (or not returned by model)")
        return

    print(f"cached_tokens: {cached_tokens}")


def run_openai_demo(shared_context: str, questions: list) -> None:
    r"""Demonstrate OpenAI prompt caching."""
    if not os.getenv("OPENAI_API_KEY"):
        print("Skipping OpenAI demo: OPENAI_API_KEY not set")
        return

    print("\n" + "=" * 70)
    print("OPENAI - Prompt Caching Demo")
    print("=" * 70)
    print("OpenAI caching is automatic for prompts with 1024+ tokens")
    print("Using prompt_cache_key for optimized cache routing")
    print()

    system_message = get_system_message()

    # Without prompt_cache_key (automatic caching still works)
    print(">>> Without prompt_cache_key (automatic):")
    model_auto = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=ChatGPTConfig(
            temperature=0.2,
            max_tokens=256,
        ).as_dict(),
    )
    agent_auto = RawChatAgent(system_message=system_message, model=model_auto)

    for i, q in enumerate(questions[:2], 1):
        agent_auto.reset()
        ask_with_agent(agent_auto, shared_context, q, i)
        _print_raw_response(agent_auto)

    # With prompt_cache_key
    print("\n>>> With prompt_cache_key='camel-docs-v1':")
    model_with_key = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict=ChatGPTConfig(
            temperature=0.2,
            max_tokens=256,
            prompt_cache_key="camel-docs-v1",
        ).as_dict(),
    )
    agent_with_key = RawChatAgent(
        system_message=system_message, model=model_with_key
    )

    for i, q in enumerate(questions, 1):
        agent_with_key.reset()
        ask_with_agent(agent_with_key, shared_context, q, i)
        _print_raw_response(agent_with_key)


def main() -> None:
    shared_context = build_long_shared_context()
    questions = get_questions()

    print("=" * 70)
    print("PROMPT CACHING DEMO")
    print("=" * 70)
    print(f"Context size: ~{len(shared_context.split())} words")

    run_openai_demo(shared_context, questions)


if __name__ == "__main__":
    main()
