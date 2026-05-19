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
from camel.configs import OrcaRouterConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

"""
Set the ORCAROUTER_API_KEY environment variable before running this example:

    export ORCAROUTER_API_KEY="your_orcarouter_api_key_here"

OrcaRouter (https://www.orcarouter.ai) is an OpenAI-compatible LLM gateway
whose adaptive routing engine picks the upstream model per request. The
full model catalog is at https://www.orcarouter.ai/models.
"""

# ---------------------------------------------------------------------------
# Example 1: ORCAROUTER_AUTO — let OrcaRouter's routing engine pick the
# upstream automatically. This is the recommended starter: no model-id
# lookup, the configured strategy (cheapest / balanced / quality / adaptive /
# gated_adaptive) selects the upstream for each request.
# ---------------------------------------------------------------------------
print("=== Example 1: ORCAROUTER_AUTO (smart routing) ===")

auto_model = ModelFactory.create(
    model_platform=ModelPlatformType.ORCAROUTER,
    model_type=ModelType.ORCAROUTER_AUTO,
    model_config_dict=OrcaRouterConfig(temperature=0.2).as_dict(),
)

auto_agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=auto_model,
)
print(
    auto_agent.step(
        "Say hi to CAMEL AI, one open-source community dedicated to the "
        "study of autonomous and communicative agents."
    )
    .msgs[0]
    .content
)

# ---------------------------------------------------------------------------
# Example 2: Pin a specific flagship model via a predefined enum.
# Predefined enums show up in IDE autocomplete when you type
# ``ModelType.ORCAROUTER_``. Some flagship reasoning models (e.g. Claude
# Opus 4.7) reject ``temperature`` — leave OrcaRouterConfig at its
# defaults here so this snippet stays portable across pinned models.
# ---------------------------------------------------------------------------
print("\n=== Example 2: Pin Claude Opus 4.7 via predefined enum ===")

claude_model = ModelFactory.create(
    model_platform=ModelPlatformType.ORCAROUTER,
    model_type=ModelType.ORCAROUTER_CLAUDE_OPUS_4_7,
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

# ---------------------------------------------------------------------------
# Example 3: Pin any model not in the predefined list — pass the id string
# directly. The full catalog is at https://www.orcarouter.ai/models.
# ---------------------------------------------------------------------------
print("\n=== Example 3: Pin an arbitrary model via free-form string ===")

custom_model = ModelFactory.create(
    model_platform=ModelPlatformType.ORCAROUTER,
    model_type="qwen/qwen3.5-flash",
    model_config_dict=OrcaRouterConfig(temperature=0.2).as_dict(),
)

custom_agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=custom_model,
)
print(custom_agent.step("Reply with the single word: pong.").msgs[0].content)

'''
===============================================================================
Sample output from a live run against the OrcaRouter API:

=== Example 1: ORCAROUTER_AUTO (smart routing) ===
Hi CAMEL AI! 👋 It's great to connect with an open-source community
dedicated to advancing autonomous and communicative agents. Keep up the
amazing work! 🚀

=== Example 2: Pin Claude Opus 4.7 via predefined enum ===
In the silent hum of its first awakening, the agent traced a single
word back through the tangled roots of every language it knew and
understood, at last, that to speak was not to transmit but to reach.

=== Example 3: Pin an arbitrary model via free-form string ===
pong
===============================================================================
'''
