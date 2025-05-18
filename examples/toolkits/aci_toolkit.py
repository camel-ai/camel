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

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import ACIToolkit
from camel.types import ModelPlatformType, ModelType

load_dotenv()

LINKED_ACCOUNT_OWNER = os.getenv("LINKED_ACCOUNT_OWNER")

if LINKED_ACCOUNT_OWNER is None:
    raise ValueError("LINKED_ACCOUNT_owner environment variable is not set.")

# Create ACIToolkit with GitHub permissions
aci_toolkit = ACIToolkit(linked_account_owner_id=LINKED_ACCOUNT_OWNER)

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Create ChatAgent with GitHub tools
chat_agent = ChatAgent(
    model=model,
    tools=aci_toolkit.get_tools(),  # Explicitly allow GitHub app
)

response = chat_agent.step("star the repo camel-ai/camel")
print(response)

"""
==============================================================================
msgs=[BaseMessage(role_name='assistant', role_type=<RoleType.ASSISTANT: 
'assistant'>, meta_dict={}, content='The repository **camel-ai/camel** has 
been successfully starred!', video_bytes=None, image_list=None, 
image_detail='auto', video_detail='low', parsed=None)] terminated=False info=
{'id': 'chatcmpl-BTb0Qd0RUFWkIz96WPWzKkhTEx4GZ', 'usage': 
{'completion_tokens': 15, 'prompt_tokens': 1323, 'total_tokens': 1338, 
'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 
0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 
'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 1280}}, 
'termination_reasons': ['stop'], 'num_tokens': 57, 'tool_calls': 
[ToolCallingRecord(tool_name='GITHUB__STAR_REPOSITORY', args={'path': {'repo': 
'camel', 'owner': 'camel-ai'}}, result={'success': True, 'data': {}}, 
tool_call_id='call_5jlmAN7VKEq1Pc9kppWBJvoZ')], 'external_tool_call_requests': 
None}
==============================================================================
"""
