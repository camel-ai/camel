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
from camel.interpreters import DockerInterpreter
from camel.models import ModelFactory
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType

toolkit = CodeExecutionToolkit(verbose=True, sandbox="docker")
tools = toolkit.get_tools()


# Enhanced system message with explicit workflow
assistant_sys_msg = (
    "You are a programming assistant with code execution capabilities. "
    "You have access to tools for executing shell commands and running code in various programming languages.\n\n"
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
    model_type=ModelType.GEMINI_2_0_FLASH_LITE,
    model_config_dict=assistant_model_config.as_dict(),
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


# Create a DockerInterpreter instance
docker_interpreter = DockerInterpreter(require_confirm=False)


# Execute commands in the Docker container
print(
    f'System update example {docker_interpreter.execute_command("apt-get update")}'
)
print(
    f'System upgrade example {docker_interpreter.execute_command("apt-get upgrade -y")}'
)
print(f'pip example {docker_interpreter.execute_command("pip --version")}')
print(f'npm example {docker_interpreter.execute_command("npm --version")}')

# Clean up the container
docker_interpreter.cleanup()

"""System update example Hit:1 https://deb.nodesource.com/node_22.x nodistro InRelease
Hit:2 https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu jammy InRelease
Hit:3 http://archive.ubuntu.com/ubuntu jammy InRelease
Get:4 http://security.ubuntu.com/ubuntu jammy-security InRelease [129 kB]
Get:5 http://archive.ubuntu.com/ubuntu jammy-updates InRelease [128 kB]
Get:6 http://archive.ubuntu.com/ubuntu jammy-backports InRelease [127 kB]
Fetched 384 kB in 2s (174 kB/s)
Reading package lists...

System upgrade example Reading package lists...
Building dependency tree...
Reading state information...
Calculating upgrade...
The following packages will be upgraded:
  apt libapt-pkg6.0 libc-bin libgssapi-krb5-2 libk5crypto3 libkrb5-3
  libkrb5support0
7 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
Need to get 3600 kB of archives.
After this operation, 1024 B of additional disk space will be used.
Get:1 http://archive.ubuntu.com/ubuntu jammy-updates/main amd64 libc-bin amd64 2.35-0ubuntu3.10 [706 kB]  
Get:2 http://archive.ubuntu.com/ubuntu jammy-updates/main amd64 libapt-pkg6.0 amd64 2.4.14 [912 kB]       
Get:3 http://archive.ubuntu.com/ubuntu jammy-updates/main amd64 apt amd64 2.4.14 [1363 kB]
Get:4 http://archive.ubuntu.com/ubuntu jammy-updates/main amd64 libk5crypto3 amd64 1.19.2-2ubuntu0.7 [86.5 kB]
Get:5 http://archive.ubuntu.com/ubuntu jammy-updates/main amd64 libkrb5support0 amd64 1.19.2-2ubuntu0.7 [32.7 kB]
Get:6 http://archive.ubuntu.com/ubuntu jammy-updates/main amd64 libkrb5-3 amd64 1.19.2-2ubuntu0.7 [356 kB]
Get:7 http://archive.ubuntu.com/ubuntu jammy-updates/main amd64 libgssapi-krb5-2 amd64 1.19.2-2ubuntu0.7 [144 kB]
Fetched 3600 kB in 3s (1088 kB/s)
(Reading database ... 26974 files and directories currently installed.)
Preparing to unpack .../libc-bin_2.35-0ubuntu3.10_amd64.deb ...
Unpacking libc-bin (2.35-0ubuntu3.10) over (2.35-0ubuntu3.9) ...
Setting up libc-bin (2.35-0ubuntu3.10) ...
(Reading database ... 26974 files and directories currently installed.)
Preparing to unpack .../libapt-pkg6.0_2.4.14_amd64.deb ...
Unpacking libapt-pkg6.0:amd64 (2.4.14) over (2.4.13) ...
Setting up libapt-pkg6.0:amd64 (2.4.14) ...
(Reading database ... 26974 files and directories currently installed.)
Preparing to unpack .../archives/apt_2.4.14_amd64.deb ...
Unpacking apt (2.4.14) over (2.4.13) ...
Setting up apt (2.4.14) ...
(Reading database ... 26974 files and directories currently installed.)
Preparing to unpack .../libk5crypto3_1.19.2-2ubuntu0.7_amd64.deb ...
Unpacking libk5crypto3:amd64 (1.19.2-2ubuntu0.7) over (1.19.2-2ubuntu0.6) ...
Setting up libk5crypto3:amd64 (1.19.2-2ubuntu0.7) ...
(Reading database ... 26974 files and directories currently installed.)
Preparing to unpack .../libkrb5support0_1.19.2-2ubuntu0.7_amd64.deb ...
Unpacking libkrb5support0:amd64 (1.19.2-2ubuntu0.7) over (1.19.2-2ubuntu0.6) ...
Setting up libkrb5support0:amd64 (1.19.2-2ubuntu0.7) ...
(Reading database ... 26974 files and directories currently installed.)
Preparing to unpack .../libkrb5-3_1.19.2-2ubuntu0.7_amd64.deb ...
Unpacking libkrb5-3:amd64 (1.19.2-2ubuntu0.7) over (1.19.2-2ubuntu0.6) ...
Setting up libkrb5-3:amd64 (1.19.2-2ubuntu0.7) ...
(Reading database ... 26974 files and directories currently installed.)
Preparing to unpack .../libgssapi-krb5-2_1.19.2-2ubuntu0.7_amd64.deb ...
Unpacking libgssapi-krb5-2:amd64 (1.19.2-2ubuntu0.7) over (1.19.2-2ubuntu0.6) ...
Setting up libgssapi-krb5-2:amd64 (1.19.2-2ubuntu0.7) ...
Processing triggers for libc-bin (2.35-0ubuntu3.10) ...
(stderr: debconf: delaying package configuration, since apt-utils is not installed
)
pip example pip 25.1.1 from /usr/local/lib/python3.10/dist-packages/pip (python 3.10)

npm example 10.9.2"""
