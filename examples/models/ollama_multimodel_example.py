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
url = "https://raw.githubusercontent.com/zjrwtx/testimages/refs/heads/main/01.jpg"
response = requests.get(url)
image = Image.open(BytesIO(response.content))

context = "what's in the image?"
message = BaseMessage.make_user_message(
    role_name="user", content=context, image_list=[image]
)

response = agent.step(message).msgs[0]
print(response.content)


"""
===============================================================================
Ollama server started on http://localhost:11434/v1 for llava-phi3 model.
2025-03-02 14:57:26,048 - root - WARNING - Invalid or missing `max_tokens` 
in `model_config_dict`. Defaulting to 999_999_999 tokens.

In the center of this image, there's an adorable
white stuffed animal with glasses and a beanie.
The stuffed animal is sitting on its hind legs, 
as if it's engaged in reading or studying 
from an open book that's placed right next to it.
In front of the book, there's a red apple with a green leaf attached to it, 
adding a touch of color and whimsy to the scene.
The entire setup is on a wooden bench, 
which provides a natural and rustic backdrop for this charming tableau.
The stuffed animal appears to be in deep thought or concentration,
creating an image that's both endearing and amusing.
===============================================================================
"""
