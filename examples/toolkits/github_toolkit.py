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
from camel.configs.openai_config import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import GithubToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name='Tools calling opertor', content='You are a helpful assistant'
)

# Set model config
tools = GithubToolkit(
    'camel-ai/camel', ""
).get_tools()
model_config_dict = ChatGPTConfig(
    temperature=0.0,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=model_config_dict,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

# Define a user message
usr_msg = BaseMessage.make_user_message(
    role_name="CAMEL User",
    content="""Please describe the issue of 'Add colorama dependency'""",
)

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
'''
===============================================================================
[FunctionCallingRecord(func_name='get_issue_list', args={'state': 'all'}, 
result=[{'number': 1136, 'title': 'add benchmark gorilla, nexus'}, {'number': 
1135, 'title': 'fix: broken dependency of docker on aarch64'}, {'number': 
1134, 'title': '[Research] Enhancing Knowledge-Intensive Reasoning with 
StructRAG'}, {'number': 1133, 'title': 'chore: update workforce doc and openai 
o1 example'}, {'number': 1132, 'title': '[Feature Request] Update workforce 
docs'}, {'number': 1131, 'title': '[BUG] The docker compose up command fails.
'}, {'number': 1130, 'title': '[Feature Request] Optimize loader doc'}, 
{'number': 1129, 'title': 'Add Discord OAuth Flow and Bot Public Thread with 
History Response Feature'}, {'number': 1128, 'title': 'chore: Add mock LLM for 
test purposes; Enable multiple `step()` calls in test units to enhance test 
robustness'}, {'number': 1127, 'title': '[Feature Request] integrate the 
`OpenAPIToolkit` into the `ToolkitManager`'}, {'number': 1126, 'title': 'feat: 
WolframAlpha ...
===============================================================================
'''
