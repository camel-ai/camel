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
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import (
    ModelPlatformType,
    ModelType,
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)
agent = ChatAgent(
    model=model,
)
image_list = [
    "https://raw.githubusercontent.com/camel-ai/camel/master/misc/logo_light.png"
]

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="Please tell me what is in the image!",
    image_list=image_list,
)
assistant_response = agent.step(user_msg)
print("=" * 20 + " RESULT " + "=" * 20)
print(assistant_response.msgs[0].content)
print("=" * 48)
