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

import os

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType

AI71_API_KEY = os.getenv("AI71_API_KEY")

ai71_model = ModelFactory.create(
    model_platform=ModelPlatformType.AI71,
    model_type="tiiuae/falcon-180b-chat",
    url="https://api.ai71.ai/v1/",
    model_config_dict={"temperature": 0.0},
    api_key=AI71_API_KEY,
)

assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)
agent = ChatAgent(assistant_sys_msg, model=ai71_model, token_limit=8192)

user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="Say hi to CAMEL AI",
)
assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)

"""
===========================================
Hello CAMEL AI! How can I assist you today?
===========================================
"""
