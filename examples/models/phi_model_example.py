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
from io import BytesIO

import requests
from PIL import Image

from camel.agents import ChatAgent
from camel.configs import PHIConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)

# Create VLLMModel
phi_model = ModelFactory.create(
    model_platform=ModelPlatformType.PHI,
    model_type=ModelType.PHI_3_5_VISION,
    model_config_dict=PHIConfig(temperature=0.0).as_dict(),
)

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=phi_model)

# Example image URLs
url = "https://www.washingtonian.com/wp-content/uploads/2017/06/6-30-17-goat-yoga-congressional-cemetery-1-994x559.jpg"
response = requests.get(url)
img = Image.open(BytesIO(response.content))

user_msg = BaseMessage.make_user_message(
    role_name="User", content="""what's in the image?""", image_list=[img]
)

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
