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
import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType

"""
please set the below os environment:
export AZURE_OPENAI_BASE_URL=""
export AZURE_API_VERSION=""
export AZURE_OPENAI_API_KEY=""
"""

model = ModelFactory.create(
    model_platform=ModelPlatformType.AZURE,
    model_type="gpt-4.1",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    url=os.getenv("AZURE_OPENAI_BASE_URL"),
    api_version="2024-12-01-preview",
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Hello CAMEL AI! It's great to hear about your open-source community dedicated
to the study of autonomous and communicative agents. If you have any
questions or need assistance, feel free to ask!
===============================================================================
'''
