# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from pathlib import Path

import pytest

from camel.interpreters import InterpreterError, SubprocessInterpreter


@pytest.fixture
def subprocess_interpreter():
    return SubprocessInterpreter(
        user_check=False,
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
    assert "stdout: 30\n" in result
    assert "stderr: " in result


def test_python_stderr(subprocess_interpreter):
    python_code = """
def divide(a, b):
    return a / b

result = divide(10, 0)
print(result)
"""
    result = subprocess_interpreter.run(python_code, "python")
    assert "stdout: " in result
    assert "ZeroDivisionError: division by zero" in result
    assert "stderr: " in result


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
    assert "stdout: 30\n" in result
    assert "stderr: " in result


def test_bash_stderr(subprocess_interpreter):
    bash_code = """
#!/bin/bash

echo $(undefined_command)
"""
    result = subprocess_interpreter.run(bash_code, "bash")
    assert "stdout: " in result
    assert "stderr: " in result
    assert "undefined_command: command not found" in result


def test_run_file_not_found(subprocess_interpreter):
    result = subprocess_interpreter.run_file(Path("/path/to/nonexistent/file"),
                                             "python")
    assert "/path/to/nonexistent/file is not a file." in result


def test_run_unsupported_code_type(subprocess_interpreter):
    with pytest.raises(InterpreterError) as exc_info:
        subprocess_interpreter.run("print('Hello')", "unsupported_code_type")
    assert "Unsupported code type unsupported_code_type." in str(
        exc_info.value)


def test_user_check(subprocess_interpreter, monkeypatch):
    subprocess_interpreter.user_check = True
    python_code = "print('Hello')"

    # Simulate user input 'n' for no
    monkeypatch.setattr('builtins.input', lambda _: 'n')

    with pytest.raises(InterpreterError) as exc_info:
        subprocess_interpreter.run(python_code, "python")
    assert "User does not run the code" in str(exc_info.value)

    # Simulate user input 'y' for yes
    monkeypatch.setattr('builtins.input', lambda _: 'y')

    # No error should be raised when user inputs 'y'
    result = subprocess_interpreter.run(python_code, "python")
    assert "stdout: Hello\n" in result
    assert "stderr: " in result
