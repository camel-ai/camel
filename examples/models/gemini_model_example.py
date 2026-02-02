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
import os

from camel.agents import ChatAgent
from camel.configs import GeminiConfig
from camel.models import ModelFactory
from camel.toolkits import TerminalToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = "You are a helpful assistant."


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
# Example of using the gemini-3-pro-preview model
model_3_pro_pre = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_3_PRO,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)

user_msg = """
Create an interactive HTML webpage that allows users to play with a
Rubik's Cube, and saved it to local file.
"""

camel_agent_pro = ChatAgent(
    system_message=sys_msg, model=model_3_pro_pre, tools=tools
)
response_pro = camel_agent_pro.step(user_msg)
print(response_pro.msgs[0].content)

'''
===============================================================================
I have created an interactive HTML webpage for playing with a Rubik's Cube.

The file is saved as: **`rubiks_cube_interactive.html`**

You can open this file in any modern web browser to play. It features:
*   **3D Rendering:** Uses Three.js for a 3D view of the cube.
*   **Controls:**
    *   **Rotate View:** Left-click and drag.
    *   **Rotate Layers:** Use the on-screen buttons (R, L, U, D, F, B).
    *   **Scramble:** A button to randomly scramble the cube.
    *   **Reset:** A button to solve/reset the cube instantly.
===============================================================================
'''


# Example of using the gemini-3-flash model
model_3_flash = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_3_FLASH,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)
camel_agent_flash = ChatAgent(system_message=sys_msg, model=model_3_flash)
user_msg = """
Explain how Generative AI works in short language.
"""
response_flash = camel_agent_flash.step(user_msg)
print(response_flash.msgs[0].content)

'''
===============================================================================
Generative AI works in three simple steps:

1.  **Training:** It "reads" or "looks at" massive amounts of existing data
(like books, code, or images) to learn patterns, styles, and structures.
2.  **Prediction:** When you give it a prompt, it doesn't "think"—it
calculates probability. It predicts what word, pixel, or note should come next
based on the patterns it learned.
3.  **Creation:** By repeating these predictions millions of times per second,
it generates entirely new content that looks or sounds like it was made by a
human.

**In short:** It is a super-powered version of **autocomplete** that uses math
to guess the most likely next piece of information.
===============================================================================
'''
