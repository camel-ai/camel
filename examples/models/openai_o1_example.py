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
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, PredefinedModelType

o1_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=PredefinedModelType.O1_PREVIEW,  # Or ModelType.O1_MINI
    model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
)

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=o1_model)

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="""Write a bash script that takes a matrix represented as a string 
    with format '[1,2],[3,4],[5,6]' and prints the transpose in the same 
    format.""",
)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
