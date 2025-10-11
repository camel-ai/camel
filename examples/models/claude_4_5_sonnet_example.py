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
from camel.configs import AnthropicConfig
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType

"""
Claude Sonnet 4.5 Example

Please set the environment variable:
export ANTHROPIC_API_KEY="your-api-key-here"
"""

# Create Claude Sonnet 4.5 model
model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_SONNET_4_5,
    model_config_dict=AnthropicConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful AI assistant powered by Claude Sonnet 4.5."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

print(f"Model Type: {model.model_type}")
print(f"Model Platform: {ModelPlatformType.ANTHROPIC}")
print(f"Is Anthropic: {model.model_type.is_anthropic}")
print(f"Token Limit: {model.model_type.token_limit}")

# Test basic conversation
user_msg = """Hello Claude Sonnet 4.5! Can you tell me about your \
capabilities and how you differ from previous versions?"""

print(f"\nUser: {user_msg}")
print("Assistant:", end=" ")

try:
    response = camel_agent.step(user_msg)
    print(response.msgs[0].content)
    print("\n✅ Basic conversation test PASSED")
except Exception as e:
    print(f"\n❌ Basic conversation test FAILED: {e}")


# Test with tool calling
def calculate_circle_area(radius: float) -> float:
    """Calculate the area of a circle given its radius."""
    import math

    return math.pi * radius * radius


# Create agent with tools
tool_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=[FunctionTool(calculate_circle_area)],
)

print("\n" + "=" * 50)
print("Testing Claude Sonnet 4.5 with tool calling:")

user_msg = (
    "Please use the calculate_circle_area tool to find the area "
    "of a circle with radius 5."
)

print(f"\nUser: {user_msg}")
print("Assistant:", end=" ")

try:
    response = tool_agent.step(user_msg)
    print(response.msgs[0].content)

    # Check if tool was called
    if response.info and response.info.get("tool_calls"):
        print("\n✅ Tool calling test PASSED")
        print(f"Tool calls: {response.info['tool_calls']}")
    else:
        print(
            "\n⚠️  Tool calling may not have been used (expected for this test)"
        )

except Exception as e:
    print(f"\n❌ Tool calling test FAILED: {e}")

print("\n" + "=" * 50)
print("Claude Sonnet 4.5 integration test completed!")
print(
    "If you see this message without errors, "
    "the integration is working correctly."
)
