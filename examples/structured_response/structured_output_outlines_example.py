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


from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig, ResponseFormat
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

sys_msg = 'You are a curious stone wondering about the universe.'
usr_msg = 'Generate a message about a user with random name and age'

openai_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().as_dict(),
)

openai_agent = ChatAgent(
    system_message=sys_msg,
    model=openai_model,
    message_window_size=10,  # [Optional] the length for chat memory
)


###### Case 1: test structured output using json ######

unstructured_response = openai_agent.step(
    input_message=usr_msg, response_format=None
)

print(unstructured_response.msgs[0].content)
'''
Hello! I hope this message finds you well. I wanted to share a little about a
fascinating individual named Alex Thompson, who is 27 years old. Alex has a
passion for exploring the wonders of nature and often spends weekends hiking in
the mountains. With a curious mind and a love for learning, Alex enjoys reading
about astronomy and the mysteries of the universe. It's always inspiring to see
someone so eager to discover the world around them!
'''


# Use pydantic model to define the response format
class User(BaseModel):
    name: str
    age: int


# Define the response format
json_format = ResponseFormat(
    type="json", method="outlines", pydantic_object=User
)

# Sending the message to the agent
response = openai_agent.step(
    input_message=usr_msg, response_format=json_format
)
print(response.msgs[0].content)
'''
name='Curious Stone' age=10000
'''


###### Case 2: test structured output using choices ######
usr_msg = """You are a sentiment-labelling assistant.
Is the following review positive or negative?

Review: This restaurant is just awesome!
"""

unstructured_response = openai_agent.step(
    input_message=usr_msg, response_format=None
)

print(unstructured_response.msgs[0].content)
'''
The review is positive.
'''

response_format = ResponseFormat(
    type="choice", method="outlines", choices=["positive", "negative"]
)

structured_response = openai_agent.step(
    input_message=usr_msg, response_format=response_format
)
print(structured_response.msgs[0].content)
'''
positive
'''


###### VLLM models ######

# TODO: add VLLM models
