# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType

# Take calling google/gemma-2-9b-it model as an example
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="google/gemma-2-9b-it",
    api_key="nvapi-xx",
    url="https://integrate.api.nvidia.com/v1",
    model_config_dict={"max_tokens": 4096},
)

agent = ChatAgent(model=model)

user_msg = """Say hi to CAMEL AI, one open-source community 
    dedicated to the study of autonomous and communicative agents."""

assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)

"""
===============================================================================
Hi CAMEL AI! 👋

It's great to hear about your open-source community dedicated to the study of 
autonomous and communicative agents. That's a fascinating field with so much 
potential! 

I'm excited to see what you all accomplish.  

Is there anything specific you'd like to tell me about your work or 
community?  I'm always eager to learn more about other AI projects. 😊
===============================================================================
"""
