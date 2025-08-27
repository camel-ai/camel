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

import pytest

from camel.toolkits.code_execution import CodeExecutionToolkit


# Test server configuration  
MICROSANDBOX_SERVER = "http://192.168.122.56:5555"


@pytest.fixture
def microsandbox_toolkit():
    """Create CodeExecutionToolkit with microsandbox."""
    microsandbox_config = {
        "server_url": MICROSANDBOX_SERVER,
        "namespace": "test-toolkit",
        "timeout": 30,
    }
    return CodeExecutionToolkit(
        sandbox="microsandbox",
        verbose=True,
        require_confirm=False,
        microsandbox_config=microsandbox_config,
    )


def test_toolkit_initialization():
    """Test microsandbox toolkit initialization."""
    microsandbox_config = {
        "server_url": MICROSANDBOX_SERVER,
        "namespace": "test-init",
    }
    toolkit = CodeExecutionToolkit(
        sandbox="microsandbox",
        verbose=False,
        require_confirm=False,
        microsandbox_config=microsandbox_config,
    )
    
    # Check that it's using MicrosandboxInterpreter
    from camel.interpreters import MicrosandboxInterpreter
    assert isinstance(toolkit.interpreter, MicrosandboxInterpreter)


def test_execute_code_python(microsandbox_toolkit):
    """Test executing Python code via toolkit."""
    code = "x = 10 + 5\nprint(f'Result: {x}')"
    result = microsandbox_toolkit.execute_code(code)
    
    # Should contain the expected output
    assert "Result: 15" in result
    assert "Executed the code below:" in result


def test_execute_code_javascript(microsandbox_toolkit):
    """Test executing JavaScript code via toolkit."""
    code = "console.log('Hello from JS');"
    result = microsandbox_toolkit.execute_code(code, code_type="javascript")
    
    assert "Hello from JS" in result
    assert "Executed the code below:" in result


def test_execute_command(microsandbox_toolkit):
    """Test executing shell commands via toolkit."""
    result = microsandbox_toolkit.execute_command("echo 'Toolkit test'")
    
    # Should contain either the echo output or success message
    assert "Toolkit test" in result or "executed successfully" in result


def test_get_tools(microsandbox_toolkit):
    """Test getting available tools."""
    tools = microsandbox_toolkit.get_tools()
    
    # Should have 2 tools: execute_code and execute_command
    assert len(tools) == 2
    
    tool_names = [tool.get_function_name() for tool in tools]
    assert "execute_code" in tool_names
    assert "execute_command" in tool_names


def test_python_with_output(microsandbox_toolkit):
    """Test Python code with print output."""
    code = """
numbers = [1, 2, 3, 4, 5]
total = sum(numbers)
print(f'Sum of numbers: {total}')
"""
    result = microsandbox_toolkit.execute_code(code)
    
    assert "Sum of numbers: 15" in result


def test_python_with_error(microsandbox_toolkit):
    """Test Python code with error handling."""
    code = "print(undefined_variable)"
    result = microsandbox_toolkit.execute_code(code)
    
    # Should contain error information
    assert any(keyword in result for keyword in ["Error", "NameError", "STDERR"])


def test_multiple_executions(microsandbox_toolkit):
    """Test multiple separate executions."""
    # First execution
    result1 = microsandbox_toolkit.execute_code("print('First execution')")
    assert "First execution" in result1
    
    # Second execution  
    result2 = microsandbox_toolkit.execute_code("print('Second execution')")
    assert "Second execution" in result2


if __name__ == "__main__":
    # Simple manual test
    print("Testing MicrosandboxToolkit...")
    
    toolkit = CodeExecutionToolkit(
        sandbox="microsandbox",
        verbose=True,
        require_confirm=False,
    )
    
    # Test Python execution
    result = toolkit.execute_code("print('Toolkit manual test works!')")
    print(f"Toolkit test result: {result}")
    
    print("Toolkit manual test completed!")
