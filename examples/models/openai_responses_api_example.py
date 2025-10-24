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
# Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved.
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

"""
Example: Using OpenAI's Responses API via ``OpenAIResponsesModel``.

Prerequisites
-------------

* Install the project dependencies (``make install`` or ``pip install -e .``).
* Export your OpenAI key: ``export OPENAI_API_KEY=sk-...``.
* (Optional) Set ``OPENAI_API_BASE_URL`` if you use a non-default endpoint.
* (Optional) Set ``CAMEL_OPENAI_USE_RESPONSES=true`` to let
  :func:`ModelFactory.create` auto-route O-series/OpenAI Responses-friendly
  models even when you request ``ModelPlatformType.OPENAI``.

This script shows how to:

1. Instantiate the Responses-backed model with streaming enabled.
2. Consume streaming deltas from :class:`ChatAgent`.
3. Retrieve the final :class:`CamelModelResponse` (including structured output
   parsed via a Pydantic schema and token usage).
"""

from __future__ import annotations

import os

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType, RoleType


class Summary(BaseModel):
    headline: str
    bullet_points: list[str]
    fun_fact: str


def main() -> None:
    # Ensure the API key is available before making the request.
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "Please set the OPENAI_API_KEY environment variable."
        )

    # Instantiate the backend via the factory. We pass the new platform
    # ``openai-responses`` to pick the Responses API backend.
    model_backend = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI_RESPONSES,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict={
            # Enable streaming so we can consume partial events.
            "stream": True,
            # Include token usage in the final stream chunk.
            "stream_options": {"include_usage": True},
            "temperature": 0.5,
        },
    )

    # Build a minimal chat agent around the backend.
    agent = ChatAgent(
        system_message=BaseMessage(
            role_name="System",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="You are a helpful assistant.",
        ),
        model=model_backend,
        # Emit delta fragments instead of the accumulating transcript.
        stream_accumulate=False,
    )

    # Compose a user message and send it to the agent.
    user_message = BaseMessage.make_user_message(
        role_name="User",
        content=(
            "Summarise the CAMEL framework for a newcomer. Provide headline, "
            "three concise bullet points, and a fun fact."
        ),
    )

    streaming_response = agent.step(user_message, response_format=Summary)

    print("=== Streaming response (delta chunks) ===")
    for chunk in streaming_response:
        # Each chunk is a ChatAgentResponse carrying just the delta text.
        if chunk.msgs:
            delta_content = chunk.msgs[0].content or ""
            if delta_content:
                print(delta_content, end="", flush=True)

    print("\n\n=== Final structured result ===")
    camel_response = streaming_response.camel_response

    if not camel_response:
        print("No final response captured (stream may have failed).")
        return

    # The normalized response aggregates text, parsed output, tool calls, etc.
    final_message = (
        camel_response.messages[0] if camel_response.messages else None
    )
    if final_message:
        print(f"Text: {final_message.content}")
        if isinstance(final_message.parsed, Summary):
            print("\nParsed dataclass:")
            print(final_message.parsed.model_dump())

    print("\n=== Token Usage ===")
    if camel_response and camel_response.usage:
        usage = camel_response.usage
        print(
            f"prompt={usage.prompt_tokens}, "
            f"completion={usage.completion_tokens}, "
            f"total={usage.total_tokens}"
        )
    else:
        print(
            "Usage not reported (stream_options.include_usage may be False)."
        )


if __name__ == "__main__":
    main()
