# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""
Example: Using TerminalToolkit with Go and Java runtimes.

This example demonstrates how to enable additional language runtimes
(Go and Java) in the TerminalToolkit. When enabled, the toolkit
will auto-detect and, if necessary, download and install the
specified runtimes.

By default, only the Python runtime is configured. Use the
``enable_other_runtimes`` parameter to opt in to Go and/or Java
support.
"""

import os

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import TerminalToolkit
from camel.toolkits.terminal_toolkit.runtime_utils import Runtime
from camel.types import ModelPlatformType, ModelType

# ── Workspace setup ──────────────────────────────────────────────────
base_dir = os.path.dirname(os.path.abspath(__file__))
workspace_dir = os.path.join(
    os.path.dirname(os.path.dirname(base_dir)), "workspace"
)

# ── System message ───────────────────────────────────────────────────
sys_msg = (
    "You are a software engineer with access to a terminal. "
    "You can compile and run Go and Java programs, as well as "
    "Python scripts. Use the terminal tools to execute commands."
)

# ── Model setup ──────────────────────────────────────────────────────
model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)

# =====================================================================
# Example 1: Enable Go runtime only
# =====================================================================
print("=" * 60)
print("Example 1: Go runtime")
print("=" * 60)

tools = TerminalToolkit(
    working_directory=workspace_dir,
    enable_other_runtimes=[Runtime.GO],
).get_tools()

agent = ChatAgent(system_message=sys_msg, model=model, tools=tools)
agent.reset()

usr_msg = (
    "Create a Go file named 'hello.go' that prints 'Hello from Go!' "
    "and then run it using 'go run hello.go'."
)
response = agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1500])
"""
===============================================================================
Expected output (varies by environment):
The agent will:
1. Create hello.go with a simple main package that prints "Hello from Go!"
2. Run the file with `go run hello.go`
3. Display "Hello from Go!" in the output
===============================================================================
"""

# =====================================================================
# Example 2: Enable Java runtime only
# =====================================================================
print("\n" + "=" * 60)
print("Example 2: Java runtime")
print("=" * 60)

tools = TerminalToolkit(
    working_directory=workspace_dir,
    enable_other_runtimes=[Runtime.JAVA],
).get_tools()

agent = ChatAgent(system_message=sys_msg, model=model, tools=tools)
agent.reset()

usr_msg = (
    "Create a Java file named 'Hello.java' with a class 'Hello' that "
    "prints 'Hello from Java!', compile it with javac, and run it."
)
response = agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1500])
"""
===============================================================================
Expected output (varies by environment):
The agent will:
1. Create Hello.java with a public class that prints "Hello from Java!"
2. Compile it with `javac Hello.java`
3. Run it with `java Hello`
4. Display "Hello from Java!" in the output
===============================================================================
"""

# =====================================================================
# Example 3: Enable both Go and Java runtimes
# =====================================================================
print("\n" + "=" * 60)
print("Example 3: Both Go and Java runtimes")
print("=" * 60)

tools = TerminalToolkit(
    working_directory=workspace_dir,
    enable_other_runtimes=[Runtime.GO, Runtime.JAVA],
).get_tools()

agent = ChatAgent(system_message=sys_msg, model=model, tools=tools)
agent.reset()

usr_msg = "Check the installed Go and Java versions."
response = agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1500])
"""
===============================================================================
Expected output (varies by environment):
The agent will:
1. Run `go version` → e.g. "go version go1.23.6 linux/amd64"
2. Run `java -version` → e.g. 'openjdk version "21.0.x"'
===============================================================================
"""

# =====================================================================
# Example 4: Default (no extra runtimes)
# =====================================================================
print("\n" + "=" * 60)
print("Example 4: Default – Python only (no Go/Java)")
print("=" * 60)

tools = TerminalToolkit(
    working_directory=workspace_dir,
    # enable_other_runtimes is omitted → only Python is configured
).get_tools()

agent = ChatAgent(system_message=sys_msg, model=model, tools=tools)
agent.reset()

usr_msg = "Check the Python version."
response = agent.step(usr_msg)
print(str(response.info['tool_calls'])[:1500])
"""
===============================================================================
Expected output (varies by environment):
The agent will run `python --version` and display the Python version.
Go and Java are NOT installed in this configuration.
===============================================================================
"""
