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
from camel.configs import MistralConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, PredefinedModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.MISTRAL,
    model_type=PredefinedModelType.MISTRAL_LARGE,
    model_config_dict=MistralConfig(temperature=0.0).as_dict(),
)

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="""Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents.""",
)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Hello CAMEL AI! It's great to connect with a community dedicated to the study 
of autonomous and communicative agents. How can I assist you today?
===============================================================================
'''
