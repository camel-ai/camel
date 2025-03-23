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
from camel.types import ModelPlatformType
from camel.toolkits import FunctionTool
from camel.configs import ChatGPTConfig
from camel.types import ModelType

def add(a: float, b: float) -> float:
        r"""Adds two numbers.

        Args:
            a (float): The first number to be added.
            b (float): The second number to be added.

        Returns:
            float: The sum of the two numbers.
        """
        raise Exception("故意设置错误,来模仿工具调用失败")


def multiply(a: float, b: float, decimal_places: int = 2) -> float:
    r"""Multiplies two numbers.

    Args:
        a (float): The multiplier in the multiplication.
        b (float): The multiplicand in the multiplication.
        decimal_places (int, optional): The number of decimal
            places to round to. Defaults to 2.

    Returns:
        float: The product of the two numbers.
    """
    return round(a * b, decimal_places)

add_tool = FunctionTool(add)
multiply_tool = FunctionTool(multiply)

# 定义系统消息
sys_msg = "你是一个数学大师,擅长各种数学问题。"

toollist = [add_tool, multiply_tool]

model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)
agent = ChatAgent(
    system_message=sys_msg, 
    model=model,tools=toollist,
    output_language='中文'
)

# 定义用户消息
usr_msg = "19987+2133之后再平方是多少?"

response = agent.step(usr_msg)

print(response.msg.content)
print(response.info['tool_calls'])
"""
===============================================================================
2025-03-23 12:22:43,919 - camel.toolkits.function_tool - ERROR - Execution of
function add failed with arguments () and {'a': 19987, 'b': 2133}. 
Error: 故意设置错误,来模仿工具调用失败
...
2025-03-23 12:22:43,919 - root - ERROR - Tool 'add' failed after 3 attempts. 
Final error: Execution of function add failed with arguments () 
and {'a': 19987, 'b': 2133}. Error: 故意设置错误,来模仿工具调用失败

19987 加上 2133 得到 22120。22120 的平方(即 22120 乘以 22120)等于 489,294,400。
[ToolCallingRecord(tool_name='add', args={'a': 19987, 'b': 2133}, 
result='tool call failed', tool_call_id='call_db0bc43bf0f74a6fb5767b'), 
ToolCallingRecord(tool_name='multiply', 
args={'a': 22120, 'b': 22120, 'decimal_places': 2}, 
result=489294400, tool_call_id='call_c1577a0313d542789f54c3')]
===============================================================================
"""