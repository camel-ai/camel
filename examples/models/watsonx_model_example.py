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
from camel.configs import WatsonXConfig
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

tools = [*MathToolkit().get_tools()]

model = ModelFactory.create(
    model_platform=ModelPlatformType.WATSONX,
    model_type=ModelType.WATSONX_LLAMA_3_3_70B_INSTRUCT,
    model_config_dict=WatsonXConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model, tools=tools)

user_msg = "Assume now is 2024 in the Gregorian calendar, University of Oxford was set up in 1096, estimate the current age of University of Oxford"  # noqa: E501

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)
print(response.info['tool_calls'])

'''
==============================================================================
The University of Oxford is approximately 928 years old in the year 2024.
[ToolCallingRecord(tool_name='sub', args={'a': 2024, 'b': 1096}, result=928, 
tool_call_id='call_05f85b0fdd9241be912883')]
==============================================================================
'''
