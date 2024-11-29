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
from camel.configs import (
    SambaCloudAPIConfig,
    SambaVerseAPIConfig,
)
from camel.models import ModelFactory
from camel.types import ModelPlatformType

# Define system message
sys_msg = "You are a helpful assistant."

# Define user message
user_msg = """Say hi to CAMEL AI, one open-source community dedicated to the 
    study of autonomous and communicative agents."""


# Use Samba Cloud model
samba_cloud_api_model = ModelFactory.create(
    model_platform=ModelPlatformType.SAMBA,
    model_type="Meta-Llama-3.1-405B-Instruct",
    model_config_dict=SambaCloudAPIConfig(max_tokens=800).as_dict(),
    api_key="Your SambaNova Cloud API Key",
    url="https://api.sambanova.ai/v1",
)

# Set agent
camel_agent_samba_cloud_api = ChatAgent(
    system_message=sys_msg, model=samba_cloud_api_model
)

# Get response information
response = camel_agent_samba_cloud_api.step(user_msg)
print(response.msgs[0].content)
'''
===============================================================================
Hello to the CAMEL AI community.  It's great to see open-source communities 
like yours working on autonomous and communicative agents, as this field has 
the potential to revolutionize many areas of our lives, from customer service 
to healthcare and beyond.

What specific projects or initiatives is the CAMEL AI community currently 
working on? Are there any exciting developments or breakthroughs that you'd 
like to share? I'm all ears (or rather, all text) and happy to learn more 
about your work!
===============================================================================
'''

# Use Samba Verse model
sambaverse_api_model = ModelFactory.create(
    model_platform=ModelPlatformType.SAMBA,
    model_type="Mistral/Mistral-7B-Instruct-v0.2",
    model_config_dict=SambaVerseAPIConfig(max_tokens=800).as_dict(),
    api_key="Your SambaVerse API Key",
    url="https://sambaverse.sambanova.ai/api/predict",
)

# Set agent
camel_agent_sambaverse_api = ChatAgent(
    system_message=sys_msg, model=sambaverse_api_model
)

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
