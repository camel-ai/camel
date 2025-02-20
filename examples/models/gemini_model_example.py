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

model = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_1_5_PRO,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
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
Hi CAMEL AI! 👋

It's great to see a community dedicated to the fascinating field of autonomous 
and communicative agents. I'm excited to see what groundbreaking work you're 
doing in this area. Keep up the great work! 🤖 
===============================================================================
'''


# Example of using the Gemini-Exp-1114 model
model_exp = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_EXP_1114,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)
camel_agent_exp = ChatAgent(system_message=sys_msg, model=model_exp)
response_exp = camel_agent_exp.step(user_msg)
print(response_exp.msgs[0].content)

'''
===============================================================================
Hi CAMEL AI! It's great to connect with you, an open-source community 
dedicated to the fascinating study of autonomous and communicative agents. 

Your work sounds incredibly exciting and important. The potential of 
autonomous agents to collaborate and communicate effectively is truly 
transformative. I'm eager to see the advancements and breakthroughs that come 
from your community.

Keep up the fantastic work!  If there's anything I can assist with, please 
don't hesitate to ask. Perhaps I can help with brainstorming ideas, 
summarizing information, or even generating creative content related to your 
research. 

Let me know how I can be of service!
===============================================================================
'''

# Example of using the gemini-2.0-flash-exp model
model_2_0_flash = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_2_0_FLASH,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)
camel_agent_exp = ChatAgent(system_message=sys_msg, model=model_2_0_flash)
response_exp = camel_agent_exp.step(user_msg)
print(response_exp.msgs[0].content)

'''
===============================================================================
Hello! I'm happy to say hi to CAMEL AI, one open-source community dedicated to 
the study of autonomous and communicative agents. It sounds like a fascinating 
community!
===============================================================================
'''
