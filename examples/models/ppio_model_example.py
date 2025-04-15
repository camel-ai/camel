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
from camel.configs import PPIOConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.PPIO,
    model_type=ModelType.PPIO_DEEPSEEK_R1,
    model_config_dict=PPIOConfig(temperature=0.2).as_dict(),
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
Hello CAMEL AI! 👋 A warm welcome to the open-source community pushing the 
boundaries of autonomous and communicative agents! Your work in exploring 
multi-agent systems, human-AI collaboration, and self-improving AI 
architectures is incredibly exciting. By fostering transparency and 
collaboration, you're empowering researchers and developers to tackle 
challenges like agent coordination, ethical alignment, and real-world 
deployment—critical steps toward responsible AI advancement.

If anyone's curious, CAMEL AI's projects often dive into simulations where AI 
agents role-play scenarios (like a negotiation between a "seller" and "buyer" 
bot), testing how they communicate, adapt, and solve problems autonomously. 
 This hands-on approach helps uncover insights into emergent behaviors and 
 scalable solutions.

Keep innovating! 🌟 The future of AI is brighter with communities like yours 
driving open, creative research.
===============================================================================
'''
