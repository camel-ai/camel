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
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType

model = ModelFactory.create(
    model_platform=ModelPlatformType.OLLAMA,
    model_type="llava-phi3",
    model_config_dict={"temperature": 0.4},
)

agent = ChatAgent(system_message="""You are a assistant""", model=model)

# URL of the image
url = "https://raw.githubusercontent.com/camel-ai/camel/master/misc/logo_light.png"
response = requests.get(url)
image = Image.open(BytesIO(response.content))

context = "what's in the image?"
message = BaseMessage.make_user_message(
    role_name="user", content=context, image_list=[image]
)

response = agent.step(message).msgs[0]
print(response)
