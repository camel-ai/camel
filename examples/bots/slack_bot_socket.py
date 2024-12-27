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

import asyncio

from camel.agents import ChatAgent
from camel.bots.slack.slack_app import SlackApp
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

slack_bot = SlackApp(
    token="please input your slack token",
    app_token="please input your slack app token",
    socket_mode=True,
)

o1_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
)
agent = ChatAgent(
    system_message="you are a helpful assistant",
    message_window_size=10,
    model=o1_model,
)


def custom_handler(message: str) -> str:
    response = agent.step(message)
    return response.msg.content


slack_bot.set_custom_handler(custom_handler)

asyncio.run(slack_bot.start())
