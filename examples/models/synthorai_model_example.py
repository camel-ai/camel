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
from camel.configs import SynthoraiConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

"""
Set the SYNTHORAI_API_KEY environment variable before running this example:

    export SYNTHORAI_API_KEY="your_synthorai_api_key_here"

Synthorai (https://synthorai.io) is an OpenAI-compatible LLM gateway that
routes to models from several upstream providers behind one base URL and key.
The catalog is at https://synthorai.io/models/.

Note that ``/v1/models`` returns the models a given key is permitted to use,
which is narrower than the full catalog — so if a model below is missing for
you, check that key's model permissions rather than the catalog.
"""

# ---------------------------------------------------------------------------
# Example 1: a predefined enum. These show up in IDE autocomplete when you
# type ``ModelType.SYNTHORAI_``.
# ---------------------------------------------------------------------------
print("=== Example 1: predefined enum ===")

model = ModelFactory.create(
    model_platform=ModelPlatformType.SYNTHORAI,
    model_type=ModelType.SYNTHORAI_CLAUDE_OPUS_5,
    model_config_dict=SynthoraiConfig(temperature=0.2).as_dict(),
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
# Example 2: another predefined enum, across a different upstream.
#
# Any catalog id also works as a free-form string, since Synthorai ids carry no
# vendor prefix. Note that a free-form id CAMEL does not know falls back to a
# 999_999_999 token limit with a warning, so prefer a predefined enum where one
# exists.
# ---------------------------------------------------------------------------
print("\n=== Example 2: a different upstream ===")

string_model = ModelFactory.create(
    model_platform=ModelPlatformType.SYNTHORAI,
    model_type=ModelType.SYNTHORAI_GPT_5_6_SOL,
    model_config_dict=SynthoraiConfig(temperature=0.2).as_dict(),
)

string_agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=string_model,
)
print(string_agent.step("Which model are you?").msgs[0].content)

"""
===============================================================================
=== Example 1: predefined enum ===
Hi CAMEL AI 🐫

Good to meet a community working in the open on autonomous and communicative
agents. The multi-agent role-playing work and the datasets that came out of it
have been useful reference points for a lot of people building agent systems —
nice to see that kind of research shared rather than kept behind closed doors.

If you ever want a hand with something concrete — CAMEL integrations, agent
orchestration patterns, or just poking at a tricky bit of code — I'm around.

=== Example 2: a different upstream ===
I'm Kiro, an AI-powered development assistant. The specific underlying
model/version isn't exposed to me.
===============================================================================
"""
