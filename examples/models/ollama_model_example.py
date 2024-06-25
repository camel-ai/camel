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

ollama_model = ModelFactory.create(
    model_platform=ModelPlatformType.OLLAMA,
    model_type="camelai-llama3",
    url="http://localhost:11434/v1",
    model_config_dict={"temperature": 0.4},
)

assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)
agent = ChatAgent(assistant_sys_msg, model=ollama_model, token_limit=4096)
agent.reset()

user_msg = BaseMessage.make_user_message(
    role_name="User", content="say hi to me"
)
assistant_response = agent.step(user_msg)
print(assistant_response.msg.content)

""" Content in Llama3ModelFile:
===============================================================================
FROM llama3

# Set parameters

PARAMETER temperature 0.8
PARAMETER stop Result

# Sets a custom system message to specify the behavior of the chat assistant

# Leaving it blank for now.

SYSTEM """ """
===============================================================================
"""


""" Content in .sh file:
===============================================================================
#!/bin/zsh

# variables
model_name="llama3"
custom_model_name="camel-llama3"

#get the base model
ollama pull $model_name

#create the model file
ollama create $custom_model_name -f ./Llama3ModelFile
===============================================================================
"""
