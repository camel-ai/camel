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
from camel.configs import LinkupConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.LINKUP,
    model_type=ModelType.LINKUP,
    model_config_dict=LinkupConfig.as_dict(),
    api_key="d364f184-8406-4a72-b209-35d170057243",
)

# Set agent
camel_agent = ChatAgent(model=model)

user_msg = """
Can you tell me which women were awared the Physics Nobel Prize
"""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
 Hello CAMEL AI community! 🐫 I'm thrilled to connect with a group so 
 dedicated to the study of autonomous and communicative agents. Your work is 
 at the forefront of advancing AI technologies that can interact and operate 
 independently in complex environments. I look forward to learning from your 
 insights and contributing to the community in any way I can. Together, let's 
 continue to push the boundaries of what's possible in AI research and 
 development! 🚀
===============================================================================
'''
