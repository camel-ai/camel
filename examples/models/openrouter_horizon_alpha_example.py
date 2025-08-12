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
from camel.configs import OpenRouterConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Create Horizon Alpha model
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENROUTER,
    model_type=ModelType.OPENROUTER_HORIZON_ALPHA,
    model_config_dict=OpenRouterConfig(temperature=0.7).as_dict(),
)

# Define system message
sys_msg = "You are a helpful AI assistant powered by Horizon Alpha model."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Tell me about your capabilities and what makes you unique 
    as the Horizon Alpha model."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
This example demonstrates how to use the Horizon Alpha model from OpenRouter
with CAMEL AI framework. The Horizon Alpha model is a cloaked model provided 
for community feedback with 256,000 context tokens support.

Note: During the testing period, this model is free to use. Make sure to set
your OPENROUTER_API_KEY environment variable before running this example.
===============================================================================
'''
