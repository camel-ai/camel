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

toolkit = CodeExecutionToolkit(verbose=True)
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


prompt = "write numpy code to dot product [[1, 2], [3, 4]] and [[5, 6]]  . "

print(Fore.YELLOW + f"User prompt:\n{prompt}\n")

# Execute and display response with detailed debugging
response = agent.step(prompt)


print(Fore.GREEN + f"Response:\n{response.msgs[0].content}\n")

'''
User prompt:
write numpy code to dot product [[1, 2], [3, 4]] and [[5, 6]]  .

pip install numpy
======stdout======
Collecting numpy
  Downloading numpy-2.2.6-cp311-cp311-win_amd64.whl.metadata (60 kB)
Downloading numpy-2.2.6-cp311-cp311-win_amd64.whl (12.9 MB)
   ---------------------------------------- 12.9/12.9 MB 9.5 MB/s eta 0:00:00
Installing collected packages: numpy
Successfully installed numpy-2.2.6

==================
======stderr======
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
tensorflow-intel 2.17.1 requires numpy<2.0.0,>=1.23.5; python_version <= "3.11", but you have numpy 2.2.6 which is incompatible.
tensorflow-intel 2.17.1 requires protobuf!=4.21.0,!=4.21.1,!=4.21.2,!=4.21.3,!=4.21.4,!=4.21.5,<5.0.0dev,>=3.20.3, but you have protobuf 6.31.0rc1 which is incompatible.

==================
Executed the command below:
```sh
pip install numpy
```
> Executed Results:
Collecting numpy
  Downloading numpy-2.2.6-cp311-cp311-win_amd64.whl.metadata (60 kB)
Downloading numpy-2.2.6-cp311-cp311-win_amd64.whl (12.9 MB)
   ---------------------------------------- 12.9/12.9 MB 9.5 MB/s eta 0:00:00
Installing collected packages: numpy
Successfully installed numpy-2.2.6
(stderr: ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
tensorflow-intel 2.17.1 requires numpy<2.0.0,>=1.23.5; python_version <= "3.11", but you have numpy 2.2.6 which is incompatible.
tensorflow-intel 2.17.1 requires protobuf!=4.21.0,!=4.21.1,!=4.21.2,!=4.21.3,!=4.21.4,!=4.21.5,<5.0.0dev,>=3.20.3, but you have protobuf 6.31.0rc1 which is incompatible.
)
======stdout======
[[17]
 [39]]

==================
Executed the code below:
```py
import numpy as np
matrix1 = np.array([[1, 2], [3, 4]])
matrix2 = np.array([[5, 6]])

result = np.dot(matrix1, matrix2.T)
print(result)
```
> Executed Results:
[[17]
 [39]]

Response:
The code calculates the dot product of two NumPy arrays. First, it initializes `matrix1` as a 2x2 array and `matrix2` as a 1x2 array. Then, it computes the dot product of `matrix1` and the transpose of `matrix2` (using `.T`). The result is a 2x1 array, where each element is the sum of the products of the corresponding elements from the rows of `matrix1` and the (transposed) column of `matrix2`.
'''
