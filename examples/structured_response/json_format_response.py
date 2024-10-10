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

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, PredefinedModelType

# Define system message
assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=PredefinedModelType.GPT_4O_MINI,
)

# Set agent
camel_agent = ChatAgent(assistant_sys_msg, model=model)


# pydantic basemodel as input params format
class JokeResponse(BaseModel):
    joke: str = Field(description="a joke")
    funny_level: str = Field(description="Funny level, from 1 to 10")


user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="Tell a jokes.",
)

# Get response information
response = camel_agent.step(user_msg, output_schema=JokeResponse)
print(response.msgs[0].content)
"""
{'joke': "Why couldn't the bicycle find its way home? It lost its bearings!"
, 'funny_level': '8'}
"""
