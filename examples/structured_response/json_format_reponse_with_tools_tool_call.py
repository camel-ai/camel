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

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

tools_list = [
    *MathToolkit().get_tools(),
]
assistant_model_config = ChatGPTConfig(
    temperature=0.0,
)

# Define system message
assistant_sys_msg = "You are a helpful assistant."

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=assistant_model_config.as_dict(),
)

# Set agent
camel_agent = ChatAgent(
    assistant_sys_msg,
    model=model,
    tools=tools_list,
)


# pydantic basemodel as input params format
class Schema(BaseModel):
    entity_name: str = Field(description=" the entity name")
    calculated_age: str = Field(description="the add more years of age")


user_msg = """Assume the current age of University of Oxford is 200 and then 
add 10 more years to this age, you must use tools to get the answer."""

# Get response information
response = camel_agent.step(
    user_msg, response_format=Schema, tool_call_based_structured_output=True
)
print(response.msgs[0].content)
"""
{'entity_name': 'University of Oxford', 'calculated_age': '210'}
"""
