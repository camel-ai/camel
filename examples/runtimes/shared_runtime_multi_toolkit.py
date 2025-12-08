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
"""
Example: Shared Runtime with Multiple Toolkits

This example demonstrates how to run multiple toolkits (TerminalToolkit,
CodeExecutionToolkit, BrowserToolkit) in a single shared Docker container.
All toolkits share the same filesystem, enabling workflows where one toolkit
can operate on files created by another.

Prerequisites:
    Build the multi-toolkit Docker image first:
    ```
    docker build -f camel/runtimes/Dockerfile.multi-toolkit \
        -t camel-multi-toolkit:latest .
    ```

Usage:
    python examples/runtimes/shared_runtime_multi_toolkit.py
    python examples/runtimes/shared_runtime_multi_toolkit.py --with-browser
"""

import argparse

import requests

from camel.runtimes import DockerRuntime
from camel.toolkits import CodeExecutionToolkit, TerminalToolkit


def test_terminal_and_code(runtime):
    """Test TerminalToolkit and CodeExecutionToolkit sharing filesystem."""
    # check the health endpoint to see loaded toolkits
    health = requests.get(f"http://localhost:{runtime.port}/health")
    print(f"\nHealth check: {health.json()}")

    # get all tools from the runtime
    tools = runtime.get_tools()
    print(f"\nAvailable tools: {[t.get_function_name() for t in tools]}")

    # find specific tools
    shell_exec = next(
        (t for t in tools if t.get_function_name() == "shell_exec"), None
    )
    execute_code = next(
        (t for t in tools if t.get_function_name() == "execute_code"), None
    )

    if not shell_exec or not execute_code:
        print("ERROR: Could not find required tools")
        return False

    # test 1: use terminal to create a file
    print("\n--- Test 1: Create file using TerminalToolkit ---")
    result = shell_exec.func(
        id="test1",
        command="echo 'Hello from shared runtime!' > /workspace/test.txt",
        block=True,
    )
    print(f"Terminal result: {result}")

    # test 2: use terminal to verify file exists
    print("\n--- Test 2: Verify file with TerminalToolkit ---")
    result = shell_exec.func(
        id="test2",
        command="cat /workspace/test.txt",
        block=True,
    )
    print(f"File contents: {result}")

    # test 3: use code execution to read the same file
    print("\n--- Test 3: Read file using CodeExecutionToolkit ---")
    code = """
with open('/workspace/test.txt', 'r') as f:
    content = f.read()
print(f"Read from Python: {content}")
"""
    result = execute_code.func(code=code)
    print(f"Code execution result: {result}")

    # test 4: use code execution to create another file
    print("\n--- Test 4: Create file using CodeExecutionToolkit ---")
    code = """
with open('/workspace/from_python.txt', 'w') as f:
    f.write('Created by CodeExecutionToolkit!')
print('File created successfully')
"""
    result = execute_code.func(code=code)
    print(f"Code execution result: {result}")

    # test 5: use terminal to read the file created by code execution
    print("\n--- Test 5: Read Python-created file with TerminalToolkit ---")
    result = shell_exec.func(
        id="test5",
        command="cat /workspace/from_python.txt",
        block=True,
    )
    print(f"File contents: {result}")

    return True


def test_with_browser(runtime):
    """Test BrowserToolkit in the shared runtime."""
    tools = runtime.get_tools()

    # find browser tool
    browse_url = next(
        (t for t in tools if t.get_function_name() == "browse_url"), None
    )

    if not browse_url:
        print("ERROR: Could not find browse_url tool")
        return False

    print("\n--- Test Browser: Fetch a webpage ---")
    result = browse_url.func(url="https://example.com")
    print(f"Browser result (truncated): {str(result)[:500]}...")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Test shared runtime with multiple toolkits"
    )
    parser.add_argument(
        "--with-browser",
        action="store_true",
        help="Include BrowserToolkit in the test",
    )
    args = parser.parse_args()

    # create toolkits (they will auto-detect CAMEL_RUNTIME inside container)
    terminal_toolkit = TerminalToolkit()
    code_toolkit = CodeExecutionToolkit(verbose=True)

    # build runtime configuration
    print("Creating shared runtime with TerminalToolkit and CodeExecution...")
    runtime = DockerRuntime("camel-multi-toolkit:latest", port=8000)
    runtime = runtime.add(
        terminal_toolkit.get_tools(),
        "camel.toolkits.TerminalToolkit",
    )
    runtime = runtime.add(
        code_toolkit.get_tools(),
        "camel.toolkits.CodeExecutionToolkit",
        {"verbose": True},
    )

    if args.with_browser:
        from camel.toolkits import BrowserToolkit

        print("Adding BrowserToolkit...")
        browser_toolkit = BrowserToolkit()
        runtime = runtime.add(
            browser_toolkit.get_tools(),
            "camel.toolkits.BrowserToolkit",
            {"headless": True},
        )

    runtime = runtime.build()

    with runtime:
        # wait for the API server to be ready
        print("Waiting for runtime to be ready...")
        if not runtime.wait(timeout=30):
            print("ERROR: Runtime failed to start")
            return

        print("Runtime is ready!")

        # run terminal and code tests
        success = test_terminal_and_code(runtime)

        # run browser tests if requested
        if args.with_browser and success:
            success = test_with_browser(runtime)

        if success:
            print("\n--- All tests completed successfully! ---")
            print("All toolkits successfully shared the same runtime.")
        else:
            print("\n--- Some tests failed ---")


if __name__ == "__main__":
    main()

"""
Creating shared runtime with TerminalToolkit and CodeExecution...
Waiting for runtime to be ready...
Runtime is ready!

Health check: {'status': 'ok', 'toolkits': [...], 'endpoints': [...]}

Available tools: ['shell_exec', 'shell_view', 'shell_write_to_process', ...]

--- Test 1: Create file using TerminalToolkit ---
Terminal result: Command executed successfully (no output).

--- Test 2: Verify file with TerminalToolkit ---
File contents: Hello from shared runtime!

--- Test 3: Read file using CodeExecutionToolkit ---
Code execution result: Executed the code below:
```python
with open('/workspace/test.txt', 'r') as f:
    content = f.read()
print(f"Read from Python: {content}")
```
> Executed Results:
Read from Python: Hello from shared runtime!

--- Test 4: Create file using CodeExecutionToolkit ---
Code execution result: Executed the code below:
```python
with open('/workspace/from_python.txt', 'w') as f:
    f.write('Created by CodeExecutionToolkit!')
print('File created successfully')
```
> Executed Results:
File created successfully

--- Test 5: Read Python-created file with TerminalToolkit ---
File contents: Created by CodeExecutionToolkit!

--- All tests completed successfully! ---
All toolkits successfully shared the same runtime.
"""
