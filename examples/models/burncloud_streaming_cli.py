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
"""Terminal-based BurnCloud streaming demo.

Sample use cases:
1. Connectivity check - verify ``BURNCLOUD_API_KEY`` works.
2. Observe token streaming - BurnCloud mirrors OpenAI Chat Completions.
3. Switch regions - point ``BURNCLOUD_API_BASE_URL`` to EU or on-prem hosts.

Before running:

```bash
export BURNCLOUD_API_KEY="your_burncloud_api_key"
# Optional: export BURNCLOUD_API_BASE_URL="https://eu-ai.burncloud.com/v1"
```
"""

from __future__ import annotations

from camel.agents import ChatAgent
from camel.configs import BurnCloudConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def build_streaming_agent() -> ChatAgent:
    """Create a BurnCloud ChatAgent with streaming enabled."""

    config = BurnCloudConfig(temperature=0.3, stream=True).as_dict()
    # OpenAI-compatible option that returns usage stats in the final chunk.
    config["stream_options"] = {"include_usage": True}

    model = ModelFactory.create(
        model_platform=ModelPlatformType.BURNCLOUD,
        model_type=ModelType.GPT_4O,
        model_config_dict=config,
    )

    return ChatAgent(
        system_message=(
            "You are a concise writing assistant. Use bullet points when "
            "they improve clarity."
        ),
        model=model,
        stream_accumulate=False,  # Print deltas; set True to auto-accumulate.
    )


def main() -> None:
    agent = build_streaming_agent()

    print("BurnCloud Streaming CLI ready.")
    print("Type a prompt and press Enter. Use 'exit' or Ctrl+D to quit.\n")

    while True:
        try:
            user_msg = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_msg:
            continue
        if user_msg.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        print("BurnCloud>", end=" ", flush=True)
        response_stream = agent.step(user_msg)

        final_usage = None
        for chunk in response_stream:
            chunk_content = chunk.msgs[0].content
            if chunk_content:
                print(chunk_content, end="", flush=True)

            if chunk.info and chunk.info.get("usage"):
                final_usage = chunk.info["usage"]

        if final_usage:
            prompt = final_usage.get("prompt_tokens", "-")
            completion = final_usage.get("completion_tokens", "-")
            total = final_usage.get("total_tokens", "-")
            print(
                "\n[usage] prompt="
                f"{prompt}, completion={completion}, total={total}"
            )

        print()  # Separate from the next prompt


if __name__ == "__main__":
    main()
