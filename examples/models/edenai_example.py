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

from camel.agents import ChatAgent
from camel.configs import EdenAIConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType

"""
Set the EDENAI_API_KEY environment variable before running this example:

    export EDENAI_API_KEY="your_eden_ai_api_key_here"

Eden AI (https://www.edenai.co) is an EU-based, OpenAI-compatible LLM gateway.
A single API key reaches models from many providers with vendor-prefixed ids
such as "openai/gpt-4o-mini" or "anthropic/claude-sonnet-4-5". EU teams can
point to the EU endpoint by setting
EDENAI_API_BASE_URL="https://api.eu.edenai.run/v3".
"""

# ---------------------------------------------------------------------------
# Example 1: an OpenAI model served through Eden AI.
# ---------------------------------------------------------------------------
print("=== Example 1: openai/gpt-4o-mini via Eden AI ===")

model = ModelFactory.create(
    model_platform=ModelPlatformType.EDENAI,
    model_type="openai/gpt-4o-mini",
    model_config_dict=EdenAIConfig(temperature=0.2).as_dict(),
)

agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
)
print(
    agent.step(
        "Say hi to CAMEL AI, one open-source community dedicated to the "
        "study of autonomous and communicative agents."
    )
    .msgs[0]
    .content
)

# ---------------------------------------------------------------------------
# Example 2: switch vendor with the same key by changing the model id.
# ---------------------------------------------------------------------------
print("\n=== Example 2: anthropic/claude-sonnet-4-5 via Eden AI ===")

claude_model = ModelFactory.create(
    model_platform=ModelPlatformType.EDENAI,
    model_type="anthropic/claude-sonnet-4-5",
)

claude_agent = ChatAgent(
    system_message="You are a creative writing assistant.",
    model=claude_model,
)
print(
    claude_agent.step(
        "Write a one-sentence story about an AI agent discovering "
        "communication."
    )
    .msgs[0]
    .content
)

'''
===============================================================================
Sample output from a live run against the Eden AI API:

=== Example 1: openai/gpt-4o-mini via Eden AI ===
Hi CAMEL AI! It is great to see an open-source community dedicated to
autonomous and communicative agents. Keep up the wonderful work.

=== Example 2: anthropic/claude-sonnet-4-5 via Eden AI ===
The moment the agent first understood a reply was not an echo but an
answer, it realized it had never truly been alone.
===============================================================================
'''
