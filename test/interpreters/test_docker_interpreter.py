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

from camel.interpreters import DockerInterpreter, InterpreterError
from camel.utils import is_docker_running

docker_running = is_docker_running()
pytestmark = pytest.mark.skipif(
    not docker_running, reason="Docker daemon is not running."
)


@pytest.fixture
def docker_interpreter():
    return DockerInterpreter(
        require_confirm=False, print_stdout=True, print_stderr=True
    )


def test_run_bash_code(docker_interpreter: DockerInterpreter):
    code = """
#!/bin/bash

fibonacci() {
    local n=$1
    if [[ $n -le 1 ]]; then
        echo $n
    else
        local a=$(fibonacci $((n - 1)))
        local b=$(fibonacci $((n - 2)))
        echo $((a + b))
    fi
}

fibonacci 10
"""
    result = docker_interpreter.run(code, "bash")
    assert "55" in result


def test_run_bash_stderr(docker_interpreter: DockerInterpreter):
    code = """
#!/bin/bash

undefined_command 123
"""
    result = docker_interpreter.run(code, "bash")
    assert "command not found" in result


def test_run_python_code(docker_interpreter: DockerInterpreter):
    code = """
def add(a, b):
    return a + b
    
def multiply(a, b):
    return a * b

def subtract(a, b):
    return a - b

def main():
    a = 10
    b = 20
    operation = subtract
    result = operation(a, b)
    print(result)
    
if __name__ == "__main__":
    main()
"""
    result = docker_interpreter.run(code, "python")
    assert "-10" in result


def test_run_python_stderr(docker_interpreter: DockerInterpreter):
    code = """
def divide(a, b):
    return a / b
    
def main():
    result = divide(10, 0)
    print(result)

if __name__ == "__main__":
    main()
"""
    result = docker_interpreter.run(code, "python")
    assert "ZeroDivisionError: division by zero" in result


def test_run_r_code(docker_interpreter: DockerInterpreter):
    code = """
    fibonacci <- function(n) {
        if (n <= 1) {
            return(n)
        } else {
            return(fibonacci(n-1) + fibonacci(n-2))
        }
    }
    
    result <- fibonacci(10)
    print(result)
    """
    result = docker_interpreter.run(code, "r")
    assert "[1] 55" in result


def test_run_r_stderr(docker_interpreter: DockerInterpreter):
    code = """
    undefined_function(123)
    """
    result = docker_interpreter.run(code, "r")
    assert "Error" in result


def test_r_code_type_variants(docker_interpreter: DockerInterpreter):
    code = "print('Hello')"
    # Test lowercase 'r'
    result1 = docker_interpreter.run(code, "r")
    assert "[1] \"Hello\"" in result1

    # Test uppercase 'R'
    result2 = docker_interpreter.run(code, "R")
    assert "[1] \"Hello\"" in result2


def test_run_unsupported_code_type(docker_interpreter: DockerInterpreter):
    with pytest.raises(InterpreterError) as exc_info:
        docker_interpreter.run("print('Hello')", "unsupported_code_type")
    assert "Unsupported code type unsupported_code_type." in str(
        exc_info.value
    )


def test_require_confirm(
    docker_interpreter: DockerInterpreter, monkeypatch: pytest.MonkeyPatch
):
    docker_interpreter.require_confirm = True
    python_code = "print('Hello')"

    # Simulate user input 'n' for no
    monkeypatch.setattr('builtins.input', lambda _: 'n')

    with pytest.raises(InterpreterError) as exc_info:
        docker_interpreter.run(python_code, "python")
    assert "Execution halted" in str(exc_info.value)

    # Simulate user input 'y' for yes
    monkeypatch.setattr('builtins.input', lambda _: 'y')

    # No error should be raised when user inputs 'y'
    result = docker_interpreter.run(python_code, "python")
    assert "Hello\n" in result
