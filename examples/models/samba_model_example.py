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
from camel.configs import SambaFastAPIConfig, SambaVerseAPIConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType

samba_fast_api_model = ModelFactory.create(
    model_platform=ModelPlatformType.SAMBA,
    model_type="llama3-70b",
    model_config_dict=SambaFastAPIConfig(max_tokens=800).as_dict(),
    api_key="Your Fast API Key",
    url="https://fast-api.snova.ai/v1/chat/completions",
)

sambaverse_api_model = ModelFactory.create(
    model_platform=ModelPlatformType.SAMBA,
    model_type="Mistral/Mistral-7B-Instruct-v0.2",
    model_config_dict=SambaVerseAPIConfig(max_tokens=800).as_dict(),
    api_key="Your SambaVerse API Key",
    url="https://sambaverse.sambanova.ai/api/predict",
)

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant",
    content="You are a helpful assistant.",
)

# Define user message
user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="""Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents.""",
)

# Set agent
camel_agent_fast_api = ChatAgent(
    system_message=sys_msg, model=samba_fast_api_model
)
camel_agent_sambaverse_api = ChatAgent(
    system_message=sys_msg, model=sambaverse_api_model
)

# Get response information
response = camel_agent_fast_api.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Hello CAMEL AI community!

It's great to connect with a group of innovators and researchers passionate 
about autonomous and communicative agents. Your work in this field has the 
potential to revolutionize numerous industries and improve human lives.

What exciting projects are you currently working on? Are there any specific 
challenges or areas where I can offer assistance or provide information? I'm 
here to help and support your endeavors!
===============================================================================
'''


# Get response information
response = camel_agent_sambaverse_api.step(user_msg)
print(response.msgs[0].content)

'''
===============================================================================
Hi CAMEL AI community! I'm here to help answer any questions you may have
related to autonomous and communicative agents. Let me know how I can be 
of assistance.
===============================================================================
'''
