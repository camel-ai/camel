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

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import TerminalToolkit
from camel.types import ModelPlatformType, ModelType

tools = [
    *TerminalToolkit().get_tools(),
]

gpt_5_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_5_2,
    model_config_dict=ChatGPTConfig().as_dict(),
)

# Set agent
camel_agent = ChatAgent(model=gpt_5_model, tools=tools)

# Set user message
user_msg = """Use tool to create an interactive HTML webpage that allows users
to play with a Rubik's Cube, and saved it to local file.
"""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Created an interactive Rubik's Cube webpage and saved it locally as:

- `rubiks_cube.html`

It includes:
- 3D cube rendering (drag to orbit, wheel to zoom)
- Face turns via buttons or keyboard (U/D/L/R/F/B, Shift for prime)
- Scramble, reset, random move
- Undo/redo
- Copyable moves log

Open it by double-clicking the file or serving it locally
(recommended due to browser module/security policies):

```bash
python3 -m http.server
# then visit http://localhost:8000/rubiks_cube.html
```

If you want a **fully offline** version (no CDN usage), tell me and
I'll modify it to bundle the required libraries locally or inline them.
===============================================================================
'''
