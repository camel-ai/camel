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
from camel.models import ModelFactory
from camel.toolkits import SymPyToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = """You are a helpful math assistant that can perform symbolic 
computations"""

# Set model config
tools = SymPyToolkit().get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)
camel_agent.reset()

# Define a user message with a complex expression
usr_msg = """Simplify the expression: (x^4 - 16)/(x^2 - 4) + sin(x)^2 + cos(x)
^2 + (x^3 + 6*x^2 + 12*x + 8)/(x + 2)"""

# Get response information
response = camel_agent.step(usr_msg)
print(response.info['tool_calls'])
'''
===============================================================================
[ToolCallingRecord(tool_name='simplify_expression', args={'expression': '(x**4 
- 16)/(x**2 - 4) + sin(x)**2 + cos(x)**2 + (x**3 + 6*x**2 + 12*x + 8)/(x + 2)
'}, result='{"status": "success", "result": "2*x**2 + 4*x + 9"}', 
tool_call_id='call_CdoZsLWeagT0yBM13RYuz09W')]
===============================================================================
'''
