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

from camel.interpreters import JupyterKernelInterpreter


@pytest.fixture
def interpreter():
    return JupyterKernelInterpreter(
        require_confirm=False, print_stdout=True, print_stderr=True
    )


def test_run_bash_code(interpreter: JupyterKernelInterpreter):
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
    result = interpreter.run(code, "bash")
    assert "55" in result


def test_run_bash_stderr(interpreter: JupyterKernelInterpreter):
    code = """
#!/bin/bash

undefined_command 123
"""
    result = interpreter.run(code, "bash")
    assert "CalledProcessError: Command" in result


def test_run_python_code(interpreter: JupyterKernelInterpreter):
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
    result = interpreter.run(code, "python")
    assert "-10" in result


def test_run_python_stderr(interpreter: JupyterKernelInterpreter):
    code = """
def divide(a, b):
    return a / b
    
def main():
    result = divide(10, 0)
    print(result)

if __name__ == "__main__":
    main()
"""
    result = interpreter.run(code, "python")
    assert "ZeroDivisionError: division by zero" in result
