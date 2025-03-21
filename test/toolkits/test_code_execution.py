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
from camel.utils import is_docker_running


@pytest.fixture
def code_execution_toolkit():
    return CodeExecutionToolkit()


@pytest.fixture
def jupyter_code_execution_toolkit():
    return CodeExecutionToolkit(
        sandbox="jupyter",
        verbose=True,
        require_confirm=False,
    )


@pytest.fixture
def docker_code_execution_toolkit():
    if not is_docker_running():
        pytest.skip("Docker is not running")
    return CodeExecutionToolkit(
        sandbox="docker",
        verbose=True,
        require_confirm=False,
    )


@pytest.fixture
def subprocess_code_execution_toolkit():
    return CodeExecutionToolkit(
        sandbox="subprocess",
        verbose=True,
        require_confirm=False,
    )


def test_execute_code(code_execution_toolkit):
    code = "x = 'a'\ny = 'b'\nx + y"
    result = code_execution_toolkit.execute_code(code)

    # ruff: noqa: E501
    expected_result = f"Executed the code below:\n```py\n{code}\n```\n> Executed Results:\n'ab'\n"
    assert expected_result == result


def test_jupyter_execute_code(jupyter_code_execution_toolkit):
    code = """
def add(a, b):
    return a + b
    
result = add(10, 20)
print(result)
"""
    result = jupyter_code_execution_toolkit.execute_code(code)
    assert "30" in result


def test_jupyter_execute_code_error(jupyter_code_execution_toolkit):
    code = """
def divide(a, b):
    return a / b
    
result = divide(10, 0)
print(result)
"""
    result = jupyter_code_execution_toolkit.execute_code(code)
    assert "ZeroDivisionError: division by zero" in result


def test_docker_execute_code(docker_code_execution_toolkit):
    code = """
def multiply(a, b):
    return a * b
    
result = multiply(6, 7)
print(result)
"""
    result = docker_code_execution_toolkit.execute_code(code)
    assert "42" in result


def test_docker_execute_code_error(docker_code_execution_toolkit):
    code = """
import nonexistent_module
"""
    result = docker_code_execution_toolkit.execute_code(code)
    assert (
        "ModuleNotFoundError: No module named 'nonexistent_module'" in result
    )


def test_subprocess_execute_code(subprocess_code_execution_toolkit):
    code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
    
result = factorial(5)
print(result)
"""
    result = subprocess_code_execution_toolkit.execute_code(code)
    assert "120" in result


def test_subprocess_execute_code_error(subprocess_code_execution_toolkit):
    code = """
x = [1, 2, 3]
print(x[10])
"""
    result = subprocess_code_execution_toolkit.execute_code(code)
    assert "IndexError: list index out of range" in result


def test_invalid_sandbox_type():
    with pytest.raises(RuntimeError) as exc_info:
        CodeExecutionToolkit(sandbox="invalid")
    assert "not supported" in str(exc_info.value)


def test_get_tools(code_execution_toolkit):
    tools = code_execution_toolkit.get_tools()
    assert len(tools) == 1
    assert tools[0].get_function_name() == "execute_code"


def test_verbose_output(code_execution_toolkit):
    """Test that verbose output works correctly."""
    toolkit = CodeExecutionToolkit(sandbox="internal_python", verbose=True)
    code = "print('test')"
    result = toolkit.execute_code(code)
    assert "test" in result
