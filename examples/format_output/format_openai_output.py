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

import ast

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


# Define the output schema
class JokeResponse(BaseModel):
    joke: str = Field(description="a joke")
    funny_level: str = Field(description="Funny level, from 1 to 10")


# Define system message
assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict=ChatGPTConfig().__dict__,
)

# Set agent
camel_agent = ChatAgent(
    assistant_sys_msg, model=model, output_schema=JokeResponse
)


user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="Tell a jokes.",
)

# Get response information
response = camel_agent.step(user_msg)
json_output_response = ast.literal_eval(
    response.choices[0].message.tool_calls[0].function.arguments
)
print(json_output_response)
"""
===============================================================================
Title: "Survival in the Snow: A Bison's Battle Against Wolves" 
Description:
Witness the raw power of nature in this gripping video showcasing a dramatic 
encounter between a lone bison and a pack of wolves in a snowy wilderness. As 
the harsh winter blankets the landscape, the struggle for survival 
intensifies. Watch as the bison, isolated from its herd, faces the relentless
pursuit of hungry wolves. The tension escalates as the wolves coordinate 
their attack, attempting to overcome the bison with their numbers and 
strategic movements. Experience the breathtaking and brutal moments of this 
wildlife interaction, where every second is a fight for survival. This video 
captures the fierce beauty and the stark realities of life in the wild. Join 
us in observing these incredible animals and the instinctual battles that 
unfold in the heart of winter's grasp.
===============================================================================
"""
