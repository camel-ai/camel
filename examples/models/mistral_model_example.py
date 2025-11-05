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
from io import BytesIO

import requests
from PIL import Image

from camel.agents import ChatAgent
from camel.configs import MistralConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.MISTRAL,
    model_type=ModelType.MISTRAL_8B,
    model_config_dict=MistralConfig(temperature=0.0).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Hello CAMEL AI! It's great to connect with a community dedicated to the study 
of autonomous and communicative agents. How can I assist you today?
===============================================================================
'''

model = ModelFactory.create(
    model_platform=ModelPlatformType.MISTRAL,
    model_type=ModelType.MISTRAL_PIXTRAL_12B,
    model_config_dict=MistralConfig(temperature=0.0).as_dict(),
)

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

# URL of the image
url = "https://raw.githubusercontent.com/camel-ai/camel/master/misc/logo_light.png"
response = requests.get(url)
img = Image.open(BytesIO(response.content))

user_msg = BaseMessage.make_user_message(
    role_name="User", content="""what's in the image?""", image_list=[img]
)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
The image features a logo with a purple camel illustration on the left side 
and the word "CAMEL" written in purple capital letters to the right of the 
camel.
===============================================================================
'''


model = ModelFactory.create(
    model_platform=ModelPlatformType.MISTRAL,
    model_type=ModelType.MISTRAL_MEDIUM_3_1,
    model_config_dict=MistralConfig(temperature=0.0).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
"""
===============================================================================
Hello, CAMEL AI! It's great to see an open-source community dedicated to the 
study of autonomous and communicative agents. I'm excited to learn more about 
your work and how I can assist you. How can I help you today?
===============================================================================
"""

model = ModelFactory.create(
    model_platform=ModelPlatformType.MISTRAL,
    model_type=ModelType.MISTRAL_MEDIUM_3_1,
    model_config_dict=MistralConfig(temperature=0.0).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
"""
===============================================================================
Hello, CAMEL AI! It's great to see an open-source community dedicated to the 
study of autonomous and communicative agents. I'm excited to learn more about 
your work and how I can assist you. How can I help you today?
===============================================================================
"""

model = ModelFactory.create(
    model_platform=ModelPlatformType.MISTRAL,
    model_type=ModelType.MISTRAL_SMALL_3_2,
    model_config_dict=MistralConfig(temperature=0.0).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the
    study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
"""
===============================================================================
Hello to CAMEL AI, an open-source community focused on the research of
autonomous and communicative agents!
===============================================================================
"""

# Example with Magistral Small 1.2
model = ModelFactory.create(
    model_platform=ModelPlatformType.MISTRAL,
    model_type=ModelType.MAGISTRAL_SMALL_1_2,
    model_config_dict=MistralConfig(temperature=0.0).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the
    study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
"""
===============================================================================
Hello to CAMEL AI, an open-source community focused on the research of
autonomous and communicative agents!
===============================================================================
"""

# Example with Magistral Medium 1.2
model = ModelFactory.create(
    model_platform=ModelPlatformType.MISTRAL,
    model_type=ModelType.MAGISTRAL_MEDIUM_1_2,
    model_config_dict=MistralConfig(temperature=0.0).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the
    study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
"""
===============================================================================
Hello to CAMEL AI, an open-source community focused on the research of
autonomous and communicative agents!
===============================================================================
"""
