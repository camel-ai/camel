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
from camel.interpreters import DockerInterpreter
from camel.models import ModelFactory
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType

toolkit = CodeExecutionToolkit(verbose=True, sandbox="docker")
tools = toolkit.get_tools()


# Enhanced system message with explicit workflow
assistant_sys_msg = (
    "You are a programming assistant with code execution capabilities. "
    "You have access to tools for executing shell commands and running "
    "code in various programming languages.\n\n"
    "MANDATORY WORKFLOW for code requests:\n"
    "1. FIRST: If the code requires external dependencies:\n"
    "   - Use execute_command tool to install required packages/libraries\n"
    "   - For Python: pip install <package>\n"
    "   - For Node.js: npm install <package>\n"
    "   - For other languages: use appropriate package manager\n"
    "   - Wait for successful installation\n\n"
    "2. SECOND: Use execute_code tool to run the code:\n"
    "   - Include all necessary imports/requires\n"
    "   - Create example data to demonstrate functionality\n"
    "   - Write complete, runnable code in the requested language\n\n"
    "3. THIRD: Explain the results and what the code does\n\n"
    "CRITICAL RULES:\n"
    "- NEVER just show code as text without executing it\n"
    "- ALWAYS use tools for installation and execution\n"
    "- For any external dependency, install it first\n"
    "- Show both installation and execution results\n"
    "- Support any programming language requested\n\n"
    "Example workflow for a JavaScript request:\n"
    "1. execute_command('npm install <package>')\n"
    "2. execute_code('// your JavaScript code here')\n"
    "3. Explain the output\n\n"
    "You MUST use the available tools - do not provide text-only "
    "responses for code requests."
)

# Create model
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Create agent
agent = ChatAgent(
    system_message=assistant_sys_msg,
    model=model,
    tools=tools,
)
agent.reset()


prompt = (
    "write javascript code to dot product [[1, 2], [3, 4]] and [[5, 6]]  . "
)

print(Fore.YELLOW + f"User prompt:\n{prompt}\n")

# Execute and display response with detailed debugging
response = agent.step(prompt)


print(Fore.GREEN + f"Response:\n{response.msgs[0].content}\n")

'''
User prompt:
write javascript code to dot product [[1, 2], [3, 4]] and [[5, 6]]  .

======stdout======
[ 17, 39 ]

==================
Executed the code below:
```javascript

function dotProduct(matrix1, matrix2) {
  if (!matrix1 || !matrix2 || matrix1.length === 0 || matrix2.length === 0) {
    return "Invalid input: Matrices cannot be empty or null.";
  }

  if (matrix1[0].length !== matrix2.length) {
    return "Invalid input: Incompatible matrix dimensions for dot product.";
  }

  const result = [];
  for (let i = 0; i < matrix1.length; i++) {
    let sum = 0;
    for (let j = 0; j < matrix2.length; j++) {
      # Assuming matrix2 is a column vector
      sum += matrix1[i][j] * matrix2[j][0];
    }
    result.push(sum);
  }
  return result;
}

const matrix1 = [[1, 2], [3, 4]];
const matrix2 = [[5], [6]]; # Corrected to be a column vector

const product = dotProduct(matrix1, matrix2);
console.log(product);

```
> Executed Results:
[ 17, 39 ]

Response:
The JavaScript code calculates the dot product of two matrices. 
The `dotProduct` function takes two matrices as input and returns a new matrix
representing their dot product. The code first checks for invalid inputs
(empty or null matrices, or incompatible dimensions). Then, it iterates through
the rows of the first matrix and the columns of the second matrix, computing 
the sum of the products of the corresponding elements. The example uses 
matrices `[[1, 2], [3, 4]]` and `[[5], [6]]` and the output is `[17, 39]`.
'''


# Create a DockerInterpreter instance
docker_interpreter = DockerInterpreter(require_confirm=False)


# Execute commands in the Docker container
print(
    f'System update example '
    f'{docker_interpreter.execute_command("apt-get update")}'
)
print(
    f'System upgrade example '
    f'{docker_interpreter.execute_command("apt-get upgrade -y")}'
)
print(f'pip example {docker_interpreter.execute_command("pip --version")}')
print(f'npm example {docker_interpreter.execute_command("npm --version")}')
print(f'uv example {docker_interpreter.execute_command("uv --version")}')

# Clean up the container
docker_interpreter.cleanup()

"""System update example Hit:1 https://deb.nodesource.com/node_22.x nodistro 
InRelease
Get:2 http://security.ubuntu.com/ubuntu jammy-security InRelease [129 kB]
Hit:3 http://archive.ubuntu.com/ubuntu jammy InRelease
Hit:4 https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu jammy InRelease
Get:5 http://archive.ubuntu.com/ubuntu jammy-updates InRelease [128 kB]
Get:6 http://security.ubuntu.com/ubuntu jammy-security/universe amd64 
Packages [1245 kB]
Get:7 http://archive.ubuntu.com/ubuntu jammy-backports InRelease [127 kB]
Get:8 http://archive.ubuntu.com/ubuntu jammy-updates/main amd64 
Packages [3295 kB]
Get:9 http://security.ubuntu.com/ubuntu jammy-security/restricted amd64 
Packages [4468 kB]
Get:10 http://security.ubuntu.com/ubuntu jammy-security/main amd64 
Packages [2979 kB]
Get:11 http://archive.ubuntu.com/ubuntu jammy-updates/restricted amd64 
Packages [4630 kB]
Get:12 http://archive.ubuntu.com/ubuntu jammy-updates/universe amd64 
Packages [1553 kB]
Fetched 18.6 MB in 3s (5312 kB/s)
Reading package lists...

System upgrade example Reading package lists...
Building dependency tree...
Reading state information...
Calculating upgrade...
0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.

pip example pip 25.1.1 from /usr/local/lib/python3.10/dist-packages/pip 
(python 3.10)

npm example 10.9.2

uv example uv 0.7.10
"""
