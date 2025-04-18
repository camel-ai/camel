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
from camel.configs import UpstageConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.UPSTAGE,
    model_type=ModelType.UPSTAGE_SOLAR_MINI_10B,
    model_config_dict=UpstageConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community 
    dedicated to the study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
Hello CAMEL AI community! I'm delighted to connect with a group of individuals
who share a passion for autonomous and communicative agents. Your dedication 
to open-source research and development is truly commendable. I'm here to 
assist in any way I can, whether it's answering questions, providing resources,
or discussing the latest advancements in the field. Let's work together to 
push the boundaries of what's possible with AI!
===============================================================================
'''
