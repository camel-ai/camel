# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

import os

from camel.agents import ChatAgent
from camel.configs import AnthropicConfig
from camel.models import ModelFactory
from camel.toolkits import FunctionTool, TerminalToolkit
from camel.types import ModelPlatformType, ModelType

"""
Claude Model Example

Please set the environment variable:
export ANTHROPIC_API_KEY="your-api-key-here"
"""

# Define system message
sys_msg = "You are a helpful AI assistant"

# Get current script directory
base_dir = os.path.dirname(os.path.abspath(__file__))
# Define workspace directory for the toolkit
workspace_dir = os.path.join(
    os.path.dirname(os.path.dirname(base_dir)), "workspace"
)

# Set model config
tools = [
    *TerminalToolkit(working_directory=workspace_dir).get_tools(),
]
# Create Claude Opus 4.5 model
model_opus_4_5 = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_OPUS_4_5,
    model_config_dict=AnthropicConfig(temperature=0.2).as_dict(),
)

user_msg = """
Create an interactive HTML webpage that allows users to play with a
Rubik's Cube, and saved it to local file.
"""

camel_agent_pro = ChatAgent(
    system_message=sys_msg, model=model_opus_4_5, tools=tools
)
response_pro = camel_agent_pro.step(user_msg)
print(response_pro.msgs[0].content)
'''
===============================================================================
The interactive Rubik's Cube HTML file has been created successfully! Here's
what I built:

## 📁 File: `rubiks_cube.html` (23KB)

### Features:

🎮 **Interactive 3D Cube**
- Fully rendered 3D Rubik's Cube using CSS transforms
- Drag to rotate the view (mouse or touch)
- All 6 faces visible with proper colors

🔄 **Face Rotations**
- **F/B** - Front/Back face
- **U/D** - Up/Down face
- **L/R** - Left/Right face
- **'** versions for counter-clockwise rotations

⚡ **Actions**
- **Scramble** - Randomly mix the cube with 20 moves
- **Reset** - Return to solved state
- **Undo** - Reverse the last move

📐 **Net View**
- 2D unfolded view of all cube faces for easier tracking

⌨️ **Keyboard Support**
- Press F, B, R, L, U, D keys to rotate faces
- Hold Shift for counter-clockwise

📱 **Responsive Design**
- Works on desktop and mobile devices
- Touch support for rotating the view

### To use:
Simply open `rubiks_cube.html` in any modern web browser!

Process finished with exit code 0
===============================================================================
'''

# Create Claude Sonnet 4.5 model
model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_SONNET_4_5,
    model_config_dict=AnthropicConfig(temperature=0.2).as_dict(),
)

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
