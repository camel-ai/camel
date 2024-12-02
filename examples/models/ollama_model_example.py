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
