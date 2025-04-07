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

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType

ollama_model = ModelFactory.create(
    model_platform=ModelPlatformType.OLLAMA,
    model_type="llama3.2",
    model_config_dict={"temperature": 0.4},
)

assistant_sys_msg = "You are a helpful assistant."

agent = ChatAgent(assistant_sys_msg, model=ollama_model, token_limit=4096)

user_msg = """Say hi to CAMEL AI, one open-source community
    dedicated to the study of autonomous and communicative agents."""

assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)

"""
===============================================================================
Ollama server started on http://localhost:11434/v1 for mistral model

Hello CAMEL AI community!

It's great to connect with such a fascinating group of individuals passionate 
about autonomous and communicative agents. Your dedication to advancing 
knowledge in this field is truly commendable.

I'm here to help answer any questions, provide information, or engage in 
discussions related to AI, machine learning, and autonomous systems. Feel free 
to ask me anything!

By the way, what topics would you like to explore within the realm of 
autonomous and communicative agents?
===============================================================================
"""


class Pet(BaseModel):
    name: str
    animal: str
    age: int
    color: str | None
    favorite_toy: str | None


class PetList(BaseModel):
    pets: list[Pet]


ollama_model = ModelFactory.create(
    model_platform=ModelPlatformType.OLLAMA,
    model_type="llama3.2",
    # Ensure using ollama version >= 0.5.1 to use structured output feature
    model_config_dict={"temperature": 0, "response_format": PetList},
)

assistant_sys_msg = "You are a helpful assistant."

agent = ChatAgent(assistant_sys_msg, model=ollama_model, token_limit=4096)

user_msg = """I have two pets.A cat named Luna who is 5 years old and loves
            playing with yarn. She has grey fur. I also have a 2 year old
            black cat named Loki who loves tennis balls."""

assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)
print(assistant_response.msg.parsed)

"""
===========================================================================
[{'role': 'system', 'content': 'You are a helpful assistant.'}, {'role':
'user', 'content': 'I have two pets.A cat named Luna who is 5 years old
and loves playing with yarn. She has grey fur.I also have a 2 year old 
black cat named Loki who loves tennis balls.'}]
{ "pets": [
    {
        "age": 5,
        "animal": "cat",
        "color": "grey",
        "favorite_toy": "yarn"
    ,
    "name": "Luna"
},
{
    "age": 2,
    "animal": "cat",
    "color": "black",
    "favorite_toy": "tennis balls"
    ,
    "name": "Loki"
}]}

pets=[Pet(name='Luna', animal='cat', age=5, color='grey',
favorite_toy='yarn'), Pet(name='Loki', animal='cat', age=2,
color='black', favorite_toy='tennis balls')]
===========================================================================
"""
