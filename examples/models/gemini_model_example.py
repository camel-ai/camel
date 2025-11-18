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

# Example of using the gemini-3-pro-preview model
model_3_pro_pre = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_3_PRO,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)
camel_agent_pro = ChatAgent(system_message=sys_msg, model=model_3_pro_pre)
response_pro = camel_agent_pro.step(user_msg)
print(response_pro.msgs[0].content)
'''
===============================================================================
Hi CAMEL AI! 👋

It is a pleasure to greet a community so dedicated to the fascinating world of 
**autonomous and communicative agents**. Keep up the amazing work pushing the 
boundaries of multi-agent collaboration and role-playing frameworks! 🐫🤖
===============================================================================
'''


# Example of using the gemini-2.5-pro model
model_2_5_pro_pre = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_2_5_PRO,
    model_config_dict=GeminiConfig(temperature=0.2).as_dict(),
)
camel_agent_pro = ChatAgent(system_message=sys_msg, model=model_2_5_pro_pre)
response_pro = camel_agent_pro.step(user_msg)
print(response_pro.msgs[0].content)

'''
===============================================================================
Hello and a big hi to the entire CAMEL AI community!

It's fantastic to acknowledge your dedication to 
the important and fascinating study of autonomous and communicative agents. 
Open-source collaboration is the engine of innovation, 
and your work is pushing the boundaries of what's possible in AI.

Keep up the brilliant research and community building
===============================================================================
'''
