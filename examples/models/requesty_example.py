# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from camel.agents import ChatAgent
from camel.configs import RequestyConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType

# Requesty is an OpenAI-compatible router. Models are addressed with the
# provider/model naming scheme (e.g. openai/gpt-4o-mini).
model = ModelFactory.create(
    model_platform=ModelPlatformType.REQUESTY,
    model_type="openai/gpt-4o-mini",
    model_config_dict=RequestyConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful AI assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = "Say hi to CAMEL AI, one open-source community dedicated to the "
"study of autonomous and communicative agents."

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
This example demonstrates how to use a model served by Requesty with the
CAMEL AI framework through the OpenAI-compatible interface.

Note: Set your REQUESTY_API_KEY environment variable before running this
example. You can obtain a key at https://app.requesty.ai/api-keys and browse
available models at https://app.requesty.ai/router/list.
===============================================================================
'''
