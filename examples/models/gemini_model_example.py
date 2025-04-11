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
from camel.configs import GeminiConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = "You are a helpful assistant."

# User message
user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents."""

# Example of using the gemini-2.5-pro-exp model
model_2_5_pro_exp = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_2_5_PRO_EXP,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)
camel_agent_pro = ChatAgent(system_message=sys_msg, model=model_2_5_pro_exp)
response_pro = camel_agent_pro.step(user_msg)
print(response_pro.msgs[0].content)
'''
===============================================================================
Hello CAMEL AI! 👋

It's great to acknowledge your open-source community and your important 
dedication to the study of autonomous and communicative agents. That's a 
fascinating and crucial area of research! Wishing you all the best in your 
endeavors.
===============================================================================
'''

# Example of using the gemini-1.5-pro model
model = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_1_5_PRO,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Hi CAMEL AI! 👋

It's great to see a community dedicated to the fascinating field of autonomous 
and communicative agents. I'm excited to see what groundbreaking work you're 
doing in this area. Keep up the great work! 🤖 
===============================================================================
'''

# Example of using the gemini-2.0-flash-exp model
model_2_0_flash = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_2_0_FLASH,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)
camel_agent_flash = ChatAgent(system_message=sys_msg, model=model_2_0_flash)
response_flash = camel_agent_flash.step(user_msg)
print(response_flash.msgs[0].content)

'''
===============================================================================
Hello! I'm happy to say hi to CAMEL AI, one open-source community dedicated to 
the study of autonomous and communicative agents. It sounds like a fascinating 
community!
===============================================================================
'''

# Example of using the gemini-2.0-flash-thinking model
model_2_0_flash_thinking = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_2_0_FLASH_THINKING,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)
camel_agent_thinking = ChatAgent(
    system_message=sys_msg, model=model_2_0_flash_thinking
)
response_thinking = camel_agent_thinking.step(
    "How many rs are there in 'starrary'?"
)
print(response_thinking.msgs[0].content)
'''
===============================================================================
Let's count them out!

s - no r
t - no r
a - no r
r - yes, that's one!
r - yes, that's two!
a - no r
r - yes, that's three!
y - no r

There are **three** rs in "starrary".
===============================================================================
'''


# Example of using the gemini-2.0-pro model
model_2_0_pro = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_2_0_PRO_EXP,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)
camel_agent_pro = ChatAgent(system_message=sys_msg, model=model_2_0_pro)
response_pro = camel_agent_pro.step(user_msg)
print(response_pro.msgs[0].content)
'''
===============================================================================
Hello CAMEL AI! It's great to connect with an open-source community focused on 
the exciting field of autonomous and communicative agents. I'm very interested 
in learning more about your work and contributions to this area of research. 
Best of luck with your endeavors!
===============================================================================
'''
