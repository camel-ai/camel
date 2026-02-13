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

"""Azure OpenAI prompt caching demo."""

import json
import os
from typing import Any, Optional

from camel.agents import ChatAgent
from camel.agents._utils import safe_model_dump
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType
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


def run_azure_demo(shared_context: str, questions: list) -> None:
    r"""Demonstrate Azure OpenAI prompt caching."""
    required = ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_BASE_URL"]
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print(f"Skipping Azure demo: {missing} not set")
        return

    print("\n" + "=" * 70)
    print("AZURE OPENAI - Prompt Caching Demo")
    print("=" * 70)
    print("Azure OpenAI caching is automatic for GPT-4o+ models")
    print("Using prompt_cache_key for optimized cache routing")
    print()

    system_message = get_system_message()

    deployment_name = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o")
    api_version = os.getenv("AZURE_API_VERSION", "2024-12-01-preview")

    # Without prompt_cache_key
    print(">>> Without prompt_cache_key (automatic):")
    model_auto = ModelFactory.create(
        model_platform=ModelPlatformType.AZURE,
        model_type=deployment_name,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        url=os.getenv("AZURE_OPENAI_BASE_URL"),
        api_version=api_version,
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
        model_platform=ModelPlatformType.AZURE,
        model_type=deployment_name,
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        url=os.getenv("AZURE_OPENAI_BASE_URL"),
        api_version=api_version,
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

    run_azure_demo(shared_context, questions)


if __name__ == "__main__":
    main()
