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
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

gpt_4_1_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_1,
    model_config_dict=ChatGPTConfig().as_dict(),
)

# Set agent
camel_agent = ChatAgent(model=gpt_4_1_model)

# Set user message
user_msg = """Say hi to CAMEL AI, one open-source community 
    dedicated to the study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Hi CAMEL AI! 👋 It's great to see an open-source community dedicated to 
advancing the study of autonomous and communicative agents. Your efforts help 
push the boundaries of what's possible in AI collaboration and agentic 
systems. Looking forward to seeing the innovations and insights your community 
brings to the field! 🚀
===============================================================================
'''
