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
from camel.toolkits import NotionToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name="Tools calling opertor", content="You are a helpful assistant"
)

# Set model config
tools = NotionToolkit().get_tools()
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
    content="Lists all pages in the Notion workspace",
)

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
==========================================================================
[FunctionCallingRecord(func_name='list_all_pages', args={}, result=[{'id': 
'12684f56-4caa-8080-be91-d7fb1a5834e3', 'title': 'test page'}, 
{'id': '47a4fb54-e34b-4b45-9928-aa2802982eb8', 'title': 'Aigentbot'}])]
"""

usr_msg = BaseMessage.make_user_message(
    role_name="CAMEL User",
    content="Lists all pages in the Notion workspace",
)

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
==========================================================================
[FunctionCallingRecord(func_name='list_all_pages', args={}, result=[{'id': 
'12684f56-4caa-8080-be91-d7fb1a5834e3', 'title': 'test page'}, 
{'id': '47a4fb54-e34b-4b45-9928-aa2802982eb8', 'title': 'Aigentbot'}])]
"""

usr_msg = BaseMessage.make_user_message(
    role_name="CAMEL User",
    content="Retrieves the text content of a Notion block which id is"
    + "'12684f56-4caa-8080-be91-d7fb1a5834e3'",
)

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1000])
"""
==========================================================================
[FunctionCallingRecord(func_name='get_notion_block_text_content', args=
{'block_id': '12684f56-4caa-8080-be91-d7fb1a5834e3'}, result='hellonihao 
buhao this is a test par [Needs case added] another par [Needs case added]
A cute cat: https://www.google.com/imgres?q=cat&imgurl=https%3A%2F%2Fi.
natgeofe.com%2Fn%2F548467d8-c5f1-4551-9f58-6817a8d2c45e%2FNationalGeographic
_2572187_square.jpg&imgrefurl=https%3A%2F%2Fwww.nationalgeographic.com%2F
animals%2Fmammals%2Ffacts%2Fdomestic-cat&docid=K6Qd9XWnQFQCoM&tbnid=eAP24
4UcF5wdYM&vet=12ahUKEwir9rf3oKGJAxVsFTQIHYsrMYkQM3oECBkQAA..i&w=3072&h=307
2&hcb=2&ved=2ahUKEwir9rf3oKGJAxVsFTQIHYsrMYkQM3oECBkQAA')]
"""
