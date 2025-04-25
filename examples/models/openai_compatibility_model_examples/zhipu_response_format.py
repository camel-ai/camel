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


class ResponseFormat(BaseModel):
    question: str
    reasoning: str
    answer: str


# Take calling model from DashScope as an example
# Refer: https://dashscope.console.aliyun.com/overview
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="glm-4",
    api_key="fb75bxxxxx",
    url="https://open.bigmodel.cn/api/paas/v4/",
    model_config_dict={"temperature": 0.4},
)

assistant_sys_msg = "You are a helpful assistant."

agent = ChatAgent(assistant_sys_msg, model=model, token_limit=4096)

user_msg = """Say hi to CAMEL AI, one open-source community 
    dedicated to the study of autonomous and communicative agents."""

assistant_response = agent.step(user_msg, response_format=ResponseFormat)
print(assistant_response.msg.content)

# ruff: noqa: E501
"""
===============================================================================
{
  "question": "Say hi to CAMEL AI, one open-source community dedicated to the study of autonomous and communicative agents.",
  "reasoning": "This is a greeting and recognition of CAMEL AI's focus on autonomous and communicative agents.",
  "answer": "Hello CAMEL AI!"
}
===============================================================================
"""
