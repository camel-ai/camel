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
prompt = "use CVXPY and solves a least-squares problem"
response = agent.step(prompt)
print(str(response.info['tool_calls'])[:1000])
""""
===========================================================================
[ToolCallingRecord(tool_name='install_math_packages', args={'packages': 
['cvxpy', 'numpy', 'scipy']}, result='Successfully installed packages:
math, cvxpy, numpy, scipy', tool_call_id='call_DsoLEqvT8ajy2Evim77u4OEy'), 
ToolCallingRecord(tool_name='solve_math_with_code', args={'code': 'import 
cvxpy as cp\nimport numpy as np\n\n# Generate some data for the least-squares
problem\nnp.random.seed(0)  # For reproducibility\nA = np.random.randn(100, 3)
\nb = np.random.randn(100)\n\n# Define the variable\nx = cp.Variable(3)\n\n# 
Define the least-squares objective\nobjective = cp.Minimize(cp.sum_squares
(A @ x - b))\n\n# Define the problem\nproblem = cp.Problem(objective)\n\n#
Solve the problem\nproblem.solve()\n\n# Get the results\nx_value = x.value
\nobjective_value = problem.value\nx_value, objective_value'}, result='
Executed the code below:\n```py\nimport math\nimport cvxpy\nimport numpy
\nimport scipy\n\nimport cvxpy as cp\nimport numpy as np\n\n#
===========================================================================
"""
