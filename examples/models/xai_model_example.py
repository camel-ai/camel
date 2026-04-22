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

"""
xAI Native SDK Model Example
==============================
pip install xai-sdk
export XAI_API_KEY="your_api_key"
python examples/models/xai_model_example.py
"""

from camel.agents import ChatAgent
from camel.configs import XAIConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType

model = ModelFactory.create(
    model_platform=ModelPlatformType.XAI,
    model_type="grok-4.20-reasoning",
    model_config_dict=XAIConfig(use_encrypted_content=True).as_dict(),
)

agent = ChatAgent(
    system_message="You are a helpful assistant. Be concise.",
    model=model,
)

print("=" * 60)
print("Turn 1")
print("=" * 60)
r1 = agent.step("What is the integral of x^2 * e^x dx?")
print(r1.msgs[0].content)

print()
print("=" * 60)
print("Turn 2")
print("=" * 60)
r2 = agent.step("Evaluate that from 0 to 1.")
print(r2.msgs[0].content)

print()
print("=" * 60)
print("Turn 3")
print("=" * 60)
r3 = agent.step("Is the result exactly e - 2? Verify.")
print(r3.msgs[0].content)
