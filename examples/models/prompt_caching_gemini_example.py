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

"""Gemini prompt caching demo."""

import os

from camel.agents import ChatAgent
from camel.configs import GeminiConfig
from camel.models import GeminiModel
from camel.types import ModelType
from examples.models.prompt_caching_common import (
    ask_with_agent,
    build_long_shared_context,
    get_questions,
    get_system_message,
)


def run_gemini_demo(shared_context: str, questions: list) -> None:
    r"""Demonstrate Google Gemini explicit context caching.

    Gemini uses explicit caching where you create a cache with TTL,
    then reference it in subsequent requests. This is different from
    Anthropic/OpenAI's implicit caching approach.

    Available cache management methods:
    - create_cache(): Create a new cache with contents and TTL
    - list_caches(): List all existing caches
    - get_cache(): Get details of a specific cache
    - update_cache(): Update the TTL of an existing cache
    - delete_cache(): Delete a cache
    - cached_content property: Set/get the cache to use for requests
    """
    if not os.getenv("GEMINI_API_KEY"):
        print("Skipping Gemini demo: GEMINI_API_KEY not set")
        return

    print("\n" + "=" * 70)
    print("GOOGLE GEMINI - Explicit Context Caching Demo")
    print("=" * 70)
    print("Gemini uses explicit caching: create cache with TTL, then use it")
    print("Minimum token thresholds vary by model; check current docs")
    print()

    system_message = get_system_message()

    # Create a GeminiModel directly for cache management
    model = GeminiModel(
        model_type=ModelType.GEMINI_2_5_FLASH,
        model_config_dict=GeminiConfig(
            temperature=0.2,
            max_tokens=256,
        ).as_dict(),
    )

    # Create cache with the shared context
    # Note: Contents must be in Gemini's native format for caching
    cache_contents = [
        {
            "role": "user",
            "parts": [{"text": shared_context}],
        }
    ]

    try:
        # Step 1: Create cache
        print(">>> Step 1: Create cache with TTL")
        cache_name = model.create_cache(
            contents=cache_contents,
            ttl="300s",  # 5 minutes
            display_name="camel-demo-cache",
            system_instruction=system_message,
        )
        print(f"Created cache: {cache_name}")

        # Step 2: List and inspect caches
        print("\n>>> Step 2: List and inspect caches")
        caches = model.list_caches()
        print(f"Total caches: {len(caches)}")

        cache_info = model.get_cache(cache_name)
        print(f"Cache model: {cache_info.model}")
        print(f"Cache expire_time: {cache_info.expire_time}")

        # Step 3: Update cache TTL
        print("\n>>> Step 3: Update cache TTL")
        updated_cache = model.update_cache(cache_name, ttl="600s")
        print(f"Updated TTL, new expire_time: {updated_cache.expire_time}")

        # Step 4: Use cache for requests
        print("\n>>> Step 4: Use cache for requests")
        model.cached_content = cache_name

        # When cached_content is set, Gemini rejects requests that still send
        # system_instruction. Keep system prompt only in the cache.
        agent = ChatAgent(system_message=None, model=model)

        for i, q in enumerate(questions, 1):
            agent.reset()
            # With cached_content set, we don't resend the context
            ask_with_agent(agent, "", q, i)

        # Step 5: Switch cache at runtime (if you have multiple caches)
        print("\n>>> Step 5: Demonstrate runtime cache switching")
        print(f"Current cache: {model.cached_content}")
        model.cached_content = None  # Disable caching
        print(f"Cache disabled: {model.cached_content}")
        model.cached_content = cache_name  # Re-enable
        print(f"Cache re-enabled: {model.cached_content}")

        # Step 6: Clean up
        print("\n>>> Step 6: Clean up")
        model.delete_cache(cache_name)
        model.cached_content = None
        print(f"Deleted cache: {cache_name}")

    except Exception as e:
        print(f"Cache operation failed: {e}")
        print("Note: Explicit caching has model-specific minimum token limits")


def main() -> None:
    shared_context = build_long_shared_context()
    questions = get_questions()

    print("=" * 70)
    print("PROMPT CACHING DEMO")
    print("=" * 70)
    print(f"Context size: ~{len(shared_context.split())} words")

    run_gemini_demo(shared_context, questions)


if __name__ == "__main__":
    main()
