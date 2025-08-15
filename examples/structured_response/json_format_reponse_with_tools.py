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
from camel.models import ModelFactory
from camel.toolkits import (
    MathToolkit,
    SearchToolkit,
)
from camel.types import ModelPlatformType, ModelType

tools_list = [
    *MathToolkit().get_tools(),
    *SearchToolkit().get_tools(),
]

# Define system message
assistant_sys_msg = "You are a helpful assistant."

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Set agent
camel_agent = ChatAgent(
    assistant_sys_msg,
    model=model,
    tools=tools_list,
)


# pydantic basemodel as input params format
class Schema(BaseModel):
    current_age: str = Field(
        description=" the current age of University of Oxford"
    )
    calculated_age: str = Field(description="the add more years of age")


user_msg = "Assume now is 2024 in the Gregorian calendar, "
"estimate the current age of University of Oxford "
"and then add 10 more years to this age, "

# Get response information
response = camel_agent.step(user_msg, response_format=Schema)
print(response.msgs[0].content)
"""
{'current_age': '928', 'calculated_age': '938'}
"""
