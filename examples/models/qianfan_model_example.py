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

from colorama import Fore

from camel.agents import ChatAgent
from camel.configs import QianfanConfig
from camel.models import ModelFactory
from camel.societies import RolePlaying
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated

# Create ERNIE 4.5 model configuration
model = ModelFactory.create(
    model_platform=ModelPlatformType.QIANFAN,
    model_type=ModelType.QIANFAN_ERNIE_4_5_TURBO_128K,
    model_config_dict=QianfanConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
Hi, CAMEL AI! It's great to connect with an open-source community focused on 
the fascinating field of autonomous and communicative agents. Your work in 
advancing this area is truly valuable, and I'm excited to see the innovative 
solutions and insights you'll bring to the table. Keep up the amazing work!
===============================================================================
'''

# Using RolePlaying to simulate a role-playing session between a Computer
# Programmer and a Gamer with ERNIE 4.5 Turbo 128K
task_prompt = "Design a custom game using pygame"
print(Fore.YELLOW + f"Original task prompt:\n{task_prompt}\n")
role_play_session = RolePlaying(
    "Computer Programmer", "Gamer", task_prompt=task_prompt, model=model
)
print(Fore.CYAN + f"Specified task prompt:\n{role_play_session.task_prompt}\n")

chat_turn_limit, n = 50, 0
input_msg = role_play_session.init_chat()
while n < chat_turn_limit:
    n += 1
    assistant_response, user_response = role_play_session.step(input_msg)
    print_text_animated(
        Fore.BLUE + f"AI User:\n\n{user_response.msg.content}\n"
    )
    print_text_animated(
        Fore.GREEN + "AI Assistant:\n\n" f"{assistant_response.msg.content}\n"
    )

    if "CAMEL_TASK_DONE" in user_response.msg.content:
        break

    input_msg = assistant_response.msg

'''
===============================================================================
Original task prompt:
Design a custom game using pygame

Specified task prompt:
Design a 2D platformer game using Pygame where the player controls a robot 
collecting energy crystals while avoiding traps and enemies, with multiple 
levels and a boss battle at the end.

AI User:

Instruction: Set up a basic Pygame project structure with a main game file 
named `main.py`.
Input: None

AI Assistant:

Solution: To set up a basic Pygame project structure, we'll start by creating 
a directory for our project and then add a main game file named `main.py`. 
This file will initialize Pygame, set up the display window, and include a 
basic game loop. Here's how you can structure it:

1. **Create a Project Directory**: Let's name our project directory 
`RobotPlatformer`.

2. **Create `main.py`**: Inside the `RobotPlatformer` directory, create a file 
named `main.py`. This file will contain the core of our game.

Here's a basic implementation for `main.py`:

```python
import pygame
import sys

# Initialize Pygame
pygame.init()
...
===============================================================================
'''
