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
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

math_toolkit = MathToolkit()
math_tool = math_toolkit.get_tools()

agent = ChatAgent(model=model, tools=math_tool)
prompt = (
    "use numpy to calculate the average and highest value of a list of numbers"
    "[1, 2, 3, 4, 5]"
)
response = agent.step(prompt)
print(str(response.info['tool_calls'])[:1000])
""""
===========================================================================
[ToolCallingRecord(tool_name='solve_math', args={'code': 'import numpy as 
np\n\n# List of numbers\nnumbers = [1, 2, 3, 4, 5]\n\n# Calculate average 
and highest value\naverage = np.mean(numbers)\nhighest = np.max(numbers)
\n\naverage, highest'}, result='Executed the code below:\n```py\nimport 
math\n\nimport numpy as np\n\n# List of numbers\nnumbers = [1, 2, 3, 4, 5]
\n\n# Calculate average and highest value\naverage = np.mean(numbers)\
nhighest = np.max(numbers)\n\naverage, highest\n```\n> Executed Results:
\n(3.0, 5)\n', tool_call_id='call_829rmGxmaDs4qNhEl1jpy1P9')]
===========================================================================
"""
