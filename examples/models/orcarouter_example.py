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
from camel.types import ModelPlatformType

# Create a model via OrcaRouter. The model_type is a free-form string that
# OrcaRouter routes to the cheapest or fastest upstream provider (OpenAI,
# Anthropic, Google, DeepSeek, etc.).
model = ModelFactory.create(
    model_platform=ModelPlatformType.ORCAROUTER,
    model_type="gpt-4o-mini",
    model_config_dict=OrcaRouterConfig(temperature=0.7).as_dict(),
)

# Define system message
sys_msg = "You are a helpful AI assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = "Say hi in one short sentence."

# Get response
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
This example demonstrates how to use OrcaRouter with the CAMEL framework.

OrcaRouter (https://orcarouter.ai) is an OpenAI-compatible LLM gateway that
sits between your application and 40+ upstream model providers. Each request
is routed to the cheapest or fastest provider that can serve the requested
model.

Before running this example, set the ORCAROUTER_API_KEY environment variable
with an API key from https://orcarouter.ai.
===============================================================================
'''
