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
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Create a streaming-capable model backend
streaming_model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict={
        "stream": True,
        "stream_options": {"include_usage": True},
    },
)

agent_accumulated = ChatAgent(
    system_message="You are a helpful assistant that provides detailed "
    "and informative responses.",
    model=streaming_model,
)

# Example user message
user_message = "How many Rs are there in the word 'strawberry'?"

# Accumulated streaming mode (default)
streaming_response = agent_accumulated.step(user_message)

for chunk_response in streaming_response:
    message = chunk_response.msgs[0]
    reasoning_text = message.reasoning_content
    if reasoning_text:
        print(reasoning_text, end="", flush=True)

    content_text = message.content
    if content_text:
        print(content_text, end="", flush=True)
usage = streaming_response.info.get("usage", {})
print(
    f"\n\nUsage: prompt={usage.get('prompt_tokens')}, "
    f"completion={usage.get('completion_tokens')}, "
    f"total={usage.get('total_tokens')}"
)
print("\n\n---\nDelta streaming mode (stream_accumulate=False):\n")

# Delta streaming mode (only new content per chunk)
agent_delta = ChatAgent(
    system_message="You are a helpful assistant that provides concise "
    "and informative responses.",
    model=streaming_model,
    stream_accumulate=False,
)

streaming_response_delta = agent_delta.step(user_message)

for chunk_response in streaming_response_delta:
    message = chunk_response.msgs[0]
    reasoning_delta = message.reasoning_content or ""
    if reasoning_delta:
        print(reasoning_delta, end="", flush=True)

    if message.content:
        print(message.content, end="", flush=True)
usage = streaming_response.info.get("usage", {})
print(
    f"\n\nUsage: prompt={usage.get('prompt_tokens')}, "
    f"completion={usage.get('completion_tokens')}, "
    f"total={usage.get('total_tokens')}"
)
