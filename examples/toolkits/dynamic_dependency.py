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


from colorama import Fore

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType

toolkit = CodeExecutionToolkit(verbose=True, sandbox="docker")
tools = toolkit.get_tools()


# Enhanced system message with explicit workflow
assistant_sys_msg = (
    "You are a programming assistant with code execution capabilities. "
    "You have access to tools for both executing shell commands and running Python code.\n\n"
    "MANDATORY WORKFLOW for code requests:\n"
    "1. FIRST: If the code requires external libraries (like numpy, torch, pandas, etc.):\n"
    "   - Use execute_command tool to install dependencies: pip install <library>\n"
    "   - Wait for successful installation\n\n"
    "2. SECOND: Use execute_code tool to run the actual Python code:\n"
    "   - Include all necessary imports\n"
    "   - Create example data to demonstrate functionality\n"
    "   - Write complete, runnable code\n\n"
    "3. THIRD: Explain the results and what the code does\n\n"
    "CRITICAL RULES:\n"
    "- NEVER just show code as text without executing it\n"
    "- ALWAYS use tools for installation and execution\n"
    "- For any external library, install it first\n"
    "- Show both installation and execution results\n\n"
    "Example workflow for numpy request:\n"
    "1. execute_command('pip install numpy')\n"
    "2. execute_code('import numpy as np\\n# your numpy code here')\n"
    "3. Explain the output\n\n"
    "You MUST use the available tools - do not provide text-only responses for code requests."
)
# ruff: noqa: E501

# Model configuration
assistant_model_config = ChatGPTConfig(
    temperature=0.0,
    tools=tools,
    tool_choice="auto",
)

# Create model
model = ModelFactory.create(
    model_platform=ModelPlatformType.GEMINI,
    model_type=ModelType.GEMINI_2_0_FLASH,
    model_config_dict=assistant_model_config.as_dict(),
)

# Create agent
agent = ChatAgent(
    system_message=assistant_sys_msg,
    model=model,
    tools=tools,
)
agent.reset()

# Test with explicit instructions
prompt = "write nump code to dot product any two matrices. "

print(Fore.YELLOW + f"User prompt:\n{prompt}\n")

# Execute and display response with detailed debugging
response = agent.step(prompt)

print(Fore.MAGENTA + f"Response object type: {type(response)}")
print(
    Fore.MAGENTA
    + f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}"
)


print(Fore.GREEN + f"Response:\n{response.msgs[0].content}\n")

'''
User prompt:
write nump code to dot product any two matrices.

pip install numpy
Executed the command below:
```sh
pip install numpy
```
> Executed Results:
Collecting numpy
  Downloading numpy-2.0.2-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (19.5 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 19.5/19.5 MB 1.7 MB/s eta 0:00:00
Installing collected packages: numpy
Successfully installed numpy-2.0.2
(stderr: WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv

[notice] A new release of pip is available: 23.0.1 -> 25.1.1
[notice] To update, run: pip install --upgrade pip
)
======stdout======
Matrix 1:
 [[1 2]
 [3 4]]
Matrix 2:
 [[5 6]
 [7 8]]
Dot product:
 [[19 22]
 [43 50]]

Matrix 3:
 [[1 2 3]
 [4 5 6]]
Matrix 4:
 [[ 7  8]
 [ 9 10]
 [11 12]]
Dot product:
 [[ 58  64]
 [139 154]]

Matrix 5:
 [[1 2]
 [3 4]]
Matrix 6:
 [[5 6]]
Dot product:
 shapes (2,2) and (1,2) not aligned: 2 (dim 1) != 1 (dim 0)

==================
Executed the code below:
```py
import numpy as np

def dot_product(matrix1, matrix2):
    try:
        result = np.dot(matrix1, matrix2)
        return result
    except ValueError as e:
        return str(e)

# Example usage
matrix1 = np.array([[1, 2], [3, 4]])
matrix2 = np.array([[5, 6], [7, 8]])

dot_product_result = dot_product(matrix1, matrix2)
print("Matrix 1:\n", matrix1)
print("Matrix 2:\n", matrix2)
print("Dot product:\n", dot_product_result)

matrix3 = np.array([[1, 2, 3], [4, 5, 6]])
matrix4 = np.array([[7, 8], [9, 10], [11, 12]])

dot_product_result2 = dot_product(matrix3, matrix4)
print("\nMatrix 3:\n", matrix3)
print("Matrix 4:\n", matrix4)
print("Dot product:\n", dot_product_result2)

matrix5 = np.array([[1, 2], [3, 4]])
matrix6 = np.array([[5, 6]])

dot_product_result3 = dot_product(matrix5, matrix6)
print("\nMatrix 5:\n", matrix5)
print("Matrix 6:\n", matrix6)
print("Dot product:\n", dot_product_result3)
```
> Executed Results:
Matrix 1:
 [[1 2]
 [3 4]]
Matrix 2:
 [[5 6]
 [7 8]]
Dot product:
 [[19 22]
 [43 50]]

Matrix 3:
 [[1 2 3]
 [4 5 6]]
Matrix 4:
 [[ 7  8]
 [ 9 10]
 [11 12]]
Dot product:
 [[ 58  64]
 [139 154]]

Matrix 5:
 [[1 2]
 [3 4]]
Matrix 6:
 [[5 6]]
Dot product:
 shapes (2,2) and (1,2) not aligned: 2 (dim 1) != 1 (dim 0)

Response object type: <class 'camel.responses.agent_responses.ChatAgentResponse'>
Response attributes: ['construct', 'copy', 'dict', 'from_orm', 'info', 'json', 'model_computed_fields', 'model_config', 'model_construct', 'model_copy', 'model_dump', 'model_dump_json', 'model_extra', 'model_fields', 'model_fields_set', 'model_json_schema', 'model_parametrized_name', 'model_post_init', 'model_rebuild', 'model_validate', 'model_validate_json', 'model_validate_strings', 'msg', 'msgs', 'parse_file', 'parse_obj', 'parse_raw', 'schema', 'schema_json', 'terminated', 'update_forward_refs', 'validate']
Response:
The code defines a function `dot_product` that takes two matrices as input and calculates their dot product using `np.dot()`. It includes error handling to catch `ValueError` exceptions, which occur when the matrices have incompatible shapes for dot product. The code then demonstrates the function with three examples, printing the input matrices and the resulting dot product (or the error message if the shapes are incompatible).


'''
# ruff: noqa: E501
