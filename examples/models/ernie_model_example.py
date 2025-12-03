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

"""
ERNIE Model Examples for CAMEL AI

This module demonstrates how to use Baidu Qianfan Platform's ERNIE models
within the CAMEL AI framework, including:
1. Single agent with ERNIE 5.0 Thinking model (reasoning capabilities)
2. Vision model with ERNIE 4.5 VL (image understanding)

Prerequisites:
    - Install CAMEL AI: pip install camel-ai
    - Set environment variable: export QIANFAN_API_KEY="Your Qianfan Key"
    - Get API key from: https://console.bce.baidu.com/qianfan/overview
"""

from camel.agents import ChatAgent
from camel.configs import QianfanConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# ============================================================================
# Example 1: Single Agent with ERNIE 5.0 Thinking Model (Reasoning)
# ============================================================================
# ERNIE 5.0 Thinking is a reasoning model that provides both the thinking
# process (reasoning_content) and the final response (content).

print("=" * 60)
print("Example 1: Single Agent with ERNIE 5.0 Thinking Model")
print("=" * 60)

# Create ERNIE 5.0 Thinking model configuration
model = ModelFactory.create(
    model_platform=ModelPlatformType.QIANFAN,
    model_type=ModelType.ERNIE_5_0_THINKING,
    model_config_dict=QianfanConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = "Explain how Generative AI works."

# Get response information
response = camel_agent.step(user_msg)

# For reasoning models, access both reasoning process and final response
print("\n--- Reasoning Process ---")
print(response.msgs[0].reasoning_content)
print("\n--- Final Response ---")
print(response.msgs[0].content)


# ============================================================================
# Example 2: Vision Model with ERNIE 4.5 VL
# ============================================================================
# ERNIE 4.5 VL is a vision-language model capable of understanding
# and describing images.

print("\n" + "=" * 60)
print("Example 2: Vision Model with ERNIE 4.5 VL")
print("=" * 60)

# Create ERNIE 4.5 VL model configuration
model = ModelFactory.create(
    model_platform=ModelPlatformType.QIANFAN,
    model_type=ModelType.ERNIE_4_5_TURBO_VL,
    model_config_dict=QianfanConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

# Prepare image URLs
image_list = [
    "https://raw.githubusercontent.com/camel-ai/camel/master/misc/logo_light.png"
]

# Create user message with image
user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="Please tell me what is in the image!",
    image_list=image_list,
)

# Get response information
response = camel_agent.step(user_msg)

print("\n--- Image Description ---")
print(response.msgs[0].content)
