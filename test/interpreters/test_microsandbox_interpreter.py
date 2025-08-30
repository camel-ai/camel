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

from camel.interpreters import InterpreterError, MicrosandboxInterpreter

# Test server configuration
MICROSANDBOX_SERVER = "http://192.168.122.56:5555"


@pytest.fixture
def interpreter():
    """Create a MicrosandboxInterpreter for testing."""
    return MicrosandboxInterpreter(
        require_confirm=False,
        server_url=MICROSANDBOX_SERVER,
        namespace="test",
        timeout=30,
    )


def test_initialization():
    """Test basic initialization."""
    interpreter = MicrosandboxInterpreter(
        require_confirm=False,
        server_url=MICROSANDBOX_SERVER,
        namespace="test-init",
        timeout=60,
    )

    assert interpreter.require_confirm is False
    assert interpreter.server_url == MICROSANDBOX_SERVER
    assert interpreter.namespace == "test-init"
    assert interpreter.timeout == 60


def test_supported_code_types():
    """Test supported code types."""
    interpreter = MicrosandboxInterpreter(require_confirm=False)
    supported_types = interpreter.supported_code_types()

    # Check basic types are supported
    assert "python" in supported_types
    assert "javascript" in supported_types
    assert "bash" in supported_types


def test_python_execution(interpreter):
    """Test Python code execution."""
    code = "print('Hello Python')"
    result = interpreter.run(code, "python")

    assert "Hello Python" in result


def test_python_math(interpreter):
    """Test Python math operations."""
    code = """
x = 10 + 5
print(f"Result: {x}")
"""
    result = interpreter.run(code, "python")

    assert "Result: 15" in result


def test_javascript_execution(interpreter):
    """Test JavaScript code execution."""
    code = "console.log('Hello JavaScript');"
    result = interpreter.run(code, "javascript")

    assert "Hello JavaScript" in result


def test_shell_execution(interpreter):
    """Test shell command execution."""
    result = interpreter.run("echo 'Hello Shell'", "bash")

    assert "Hello Shell" in result


def test_execute_command(interpreter):
    """Test execute_command method."""
    result = interpreter.execute_command("echo test")

    # Should return something (either output or success message)
    assert result is not None
    assert len(result) > 0
    # Accept both successful execution and actual output
    assert "executed successfully" in result or "test" in result


def test_unsupported_language(interpreter):
    """Test unsupported language raises error."""
    with pytest.raises(InterpreterError):
        interpreter.run("test", "unsupported_language")


def test_python_error_handling(interpreter):
    """Test Python error handling."""
    code = "x = 1 / 0"  # Division by zero
    result = interpreter.run(code, "python")

    # Should contain error information
    assert any(
        keyword in result
        for keyword in ["Error", "Exception", "ZeroDivisionError"]
    )


def test_variable_persistence(interpreter):
    """Test variables within single execution."""
    # Set and use variable in same execution
    code = """
x = 100
print(f'x = {x}')
"""
    result = interpreter.run(code, "python")
    assert "x = 100" in result


if __name__ == "__main__":
    # Simple manual test
    print("Testing MicrosandboxInterpreter...")

    interp = MicrosandboxInterpreter(
        require_confirm=False,
        server_url=MICROSANDBOX_SERVER,
        namespace="manual-test",
    )

    # Test Python
    result = interp.run("print('Manual test works!')", "python")
    print(f"Python test: {result}")

    print("Manual test completed!")

"""
================================== test session starts ===================================
platform linux -- Python 3.11.7, pytest-8.4.1, pluggy-1.6.0 -- /home/lyz/Camel/camel/.camel/bin/python3
cachedir: .pytest_cache
rootdir: /home/lyz/Camel/camel
configfile: pyproject.toml
plugins: anyio-4.10.0
collected 10 items                                                                       

test/interpreters/test_microsandbox_interpreter.py::test_initialization PASSED     [ 10%]
test/interpreters/test_microsandbox_interpreter.py::test_supported_code_types PASSED [ 20%]
test/interpreters/test_microsandbox_interpreter.py::test_python_execution PASSED   [ 30%]
test/interpreters/test_microsandbox_interpreter.py::test_python_math PASSED        [ 40%]
test/interpreters/test_microsandbox_interpreter.py::test_javascript_execution PASSED [ 50%]
test/interpreters/test_microsandbox_interpreter.py::test_shell_execution PASSED    [ 60%]
test/interpreters/test_microsandbox_interpreter.py::test_execute_command PASSED    [ 70%]
test/interpreters/test_microsandbox_interpreter.py::test_unsupported_language PASSED [ 80%]
test/interpreters/test_microsandbox_interpreter.py::test_python_error_handling PASSED [ 90%]
test/interpreters/test_microsandbox_interpreter.py::test_variable_persistence PASSED [100%]

================================== 10 passed in 33.76s ===================================
"""  # noqa: E501
