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
from pathlib import Path

import pytest

from camel.interpreters import InterpreterError, SubprocessInterpreter


@pytest.fixture
def subprocess_interpreter():
    return SubprocessInterpreter(
        require_confirm=False,
        print_stdout=True,
        print_stderr=True,
    )


def test_run_python_code(subprocess_interpreter):
    python_code = """
def add(a, b):
    return a + b

result = add(10, 20)
print(result)
"""
    result = subprocess_interpreter.run(python_code, "python")
    assert "30\n" in result


def test_python_stderr(subprocess_interpreter):
    python_code = """
def divide(a, b):
    return a / b

result = divide(10, 0)
print(result)
"""
    result = subprocess_interpreter.run(python_code, "python")
    assert "ZeroDivisionError: division by zero" in result


def test_run_bash_code(subprocess_interpreter):
    bash_code = """
#!/bin/bash

function add() {
    echo $(($1 + $2))
}

result=$(add 10 20)
echo $result
"""
    result = subprocess_interpreter.run(bash_code, "bash")
    assert "30\n" in result


def test_bash_stderr(subprocess_interpreter):
    bash_code = """
#!/bin/bash

echo $(undefined_command)
"""
    result = subprocess_interpreter.run(bash_code, "bash")
    assert "stderr: " in result
    assert "undefined_command: command not found" in result


def test_run_file_not_found(subprocess_interpreter):
    result = subprocess_interpreter.run_file(
        Path("/path/to/nonexistent/file"),
        "python",
    )
    assert "/path/to/nonexistent/file is not a file." in result


def test_run_unsupported_code_type(subprocess_interpreter):
    with pytest.raises(InterpreterError) as exc_info:
        subprocess_interpreter.run("print('Hello')", "unsupported_code_type")
    assert "Unsupported code type unsupported_code_type." in str(
        exc_info.value
    )


@pytest.mark.skip(reason="R may not installed on system")
def test_run_r_code(subprocess_interpreter):
    r_code = """
    add <- function(a, b) {
        return(a + b)
    }
    
    result <- add(10, 20)
    print(result)
    """
    result = subprocess_interpreter.run(r_code, "r")
    assert "[1] 30" in result


@pytest.mark.skip(reason="R may not installed on system")
def test_r_stderr(subprocess_interpreter):
    r_code = """
    undefined_function()
    """
    result = subprocess_interpreter.run(r_code, "r")
    assert "Error" in result


@pytest.mark.skip(reason="R may not installed on system")
def test_r_code_type_variants(subprocess_interpreter):
    r_code = "print('Hello')"
    # Test lowercase 'r'
    result1 = subprocess_interpreter.run(r_code, "r")
    assert "[1] \"Hello\"" in result1

    # Test uppercase 'R'
    result2 = subprocess_interpreter.run(r_code, "R")
    assert "[1] \"Hello\"" in result2


def test_require_confirm(subprocess_interpreter, monkeypatch):
    subprocess_interpreter.require_confirm = True
    python_code = "print('Hello')"

    # Simulate user input 'n' for no
    monkeypatch.setattr('builtins.input', lambda _: 'n')

    with pytest.raises(InterpreterError) as exc_info:
        subprocess_interpreter.run(python_code, "python")
    assert "Execution halted" in str(exc_info.value)

    # Simulate user input 'y' for yes
    monkeypatch.setattr('builtins.input', lambda _: 'y')

    # No error should be raised when user inputs 'y'
    result = subprocess_interpreter.run(python_code, "python")
    assert "Hello\n" in result
