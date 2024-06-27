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

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType

fastchat_model = ModelFactory.create(
    model_platform=ModelPlatformType.FASTCHAT,
    model_type="camelai-fs",
    url="http://192.168.11.199:1282/v1",
    model_config_dict={
        "model_name": "gpt-4",
        "api_params": {"temperature": 0.4},
    },
)

assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)
agent = ChatAgent(assistant_sys_msg, model=fastchat_model, token_limit=4096)
agent.reset()

user_msg = BaseMessage.make_user_message(
    role_name="User", content="who are you?"
)
assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)
