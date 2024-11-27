# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from camel.agents import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import OpenAPIToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = BaseMessage.make_assistant_message(
    role_name='Tools calling opertor', content='You are a helpful assistant'
)

# Set model config
tools = OpenAPIToolkit().get_tools()
model_config_dict = ChatGPTConfig(
    temperature=0.0,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
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
    role_name='CAMEL User', content='help me to select a basketball in klarna.'
)

# Get response information
response = camel_agent.step(usr_msg)
print(response.info['tool_calls'])
"""
===============================================================================
[FunctionCallingRecord(func_name='klarna_productsUsingGET', args={
'q_in_query': 'basketball'}, result={'products': [{'name': 'Wilson Evolution'
, 'url': 'https://www.klarna.com/us/shopping/pl/cl1220/3203801266/Basketball
/Wilson-Evolution/?utm_source=openai&ref-site=openai_plugin', 'price':
'$65.00', 'attributes': ['Color:Brown,Blue,Black,Orange', 'Ball Size:6,7',
'Area of Use:Indoors,Outdoors', 'Material:Leather,Rubber']}, {'name':
'Wilson NBA Authentic', 'url': 'https://www.klarna.com/us/shopping/pl/cl1220/
3200358202/Basketball/Wilson-NBA-Authentic/?utm_source=openai&ref-site=openai
_plugin', 'price': '$24.99', 'attributes': ['Color:Orange', 'Ball Size:6,7',
'Area of Use: Indoors,Outdoors', 'Material:Leather']},]})]
===============================================================================
"""
