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
import numpy as np
import pytest
import torch

from camel.interpreters import InternalPythonInterpreter, InterpreterError

pytestmark = pytest.mark.heavy_dependency


def action_function():
    return "access action function"


@pytest.fixture()
def interpreter():
    action_space = {"action1": action_function, "str": str}
    white_list = ["torch", "numpy.array", "openai"]
    return InternalPythonInterpreter(
        action_space=action_space,
        import_white_list=white_list,
        raise_error=True,
    )


def test_state_update(interpreter: InternalPythonInterpreter):
    code = "x = input_variable"
    input_variable = 10
    execution_res = interpreter.execute(
        code, state={"input_variable": input_variable}
    )
    assert execution_res == input_variable


def test_syntax_error(interpreter: InternalPythonInterpreter):
    code = "x input_variable"
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code)
    exec_msg = e.value.args[0]
    assert "Syntax error in code: invalid syntax" in exec_msg


def test_import_success0(interpreter: InternalPythonInterpreter):
    code = """import torch as pt, openai
a = pt.tensor([[1., -1.], [1., -1.]])
openai.__version__"""
    execution_res = interpreter.execute(code)
    assert torch.equal(
        interpreter.state["a"], torch.tensor([[1.0, -1.0], [1.0, -1.0]])
    )
    assert isinstance(execution_res, str)


def test_import_success1(interpreter: InternalPythonInterpreter):
    code = """from torch import tensor
a = tensor([[1., -1.], [1., -1.]])"""
    execution_res = interpreter.execute(code)
    assert torch.equal(execution_res, torch.tensor([[1.0, -1.0], [1.0, -1.0]]))


def test_import_success2(interpreter: InternalPythonInterpreter):
    code = """from numpy import array
x = array([[1, 2, 3], [4, 5, 6]])"""
    execution_res = interpreter.execute(code)
    assert np.equal(execution_res, np.array([[1, 2, 3], [4, 5, 6]])).all()


def test_import_fail0(interpreter: InternalPythonInterpreter):
    code = """import os
os.mkdir("/tmp/test")"""
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code)
    exec_msg = e.value.args[0]
    assert exec_msg == (
        "Evaluation of the code stopped at node 0. See:\n"
        "It is not permitted to import modules than module"
        " white list (try to import os)."
    )


def test_import_fail1(interpreter: InternalPythonInterpreter):
    code = """import numpy as np
x = np.array([[1, 2, 3], [4, 5, 6]], np.int32)"""
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code)
    exec_msg = e.value.args[0]
    assert exec_msg == (
        "Evaluation of the code stopped at node 0. See:\n"
        "It is not permitted to import modules than module"
        " white list (try to import numpy)."
    )


def test_action_space(interpreter: InternalPythonInterpreter):
    code = "res = action1()"
    execution_res = interpreter.execute(code)
    assert execution_res == "access action function"


def test_fuzz_space(interpreter: InternalPythonInterpreter):
    from PIL import Image

    fuzz_state = {"image": Image.new("RGB", (256, 256))}
    code = "output_image = input_image.crop((20, 20, 100, 100))"
    execution_res = interpreter.execute(code, fuzz_state=fuzz_state)
    assert execution_res.width == 80
    assert execution_res.height == 80


def test_keep_state0(interpreter: InternalPythonInterpreter):
    code1 = "a = 42"
    code2 = "b = a"
    code3 = "c = b"

    execution_res = interpreter.execute(code1, keep_state=True)
    assert execution_res == 42
    execution_res = interpreter.execute(code2, keep_state=False)
    assert execution_res == 42
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code3, keep_state=False)
    exec_msg = e.value.args[0]
    assert exec_msg == (
        "Evaluation of the code stopped at node 0. See:\n"
        "The variable `b` is not defined."
    )


def test_keep_state1(interpreter: InternalPythonInterpreter):
    code1 = "from torch import tensor"
    code2 = "a = tensor([[1., -1.], [1., -1.]])"
    execution_res = interpreter.execute(code1, keep_state=True)
    execution_res = interpreter.execute(code2, keep_state=False)
    assert torch.equal(execution_res, torch.tensor([[1.0, -1.0], [1.0, -1.0]]))
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code2, keep_state=False)
    exec_msg = e.value.args[0]
    assert exec_msg == (
        "Evaluation of the code stopped at node 0. See:\n"
        "The variable `tensor` is not defined."
    )


def test_assign0(interpreter: InternalPythonInterpreter):
    code = "a = b = 1"
    interpreter.execute(code)
    assert interpreter.state["a"] == 1
    assert interpreter.state["b"] == 1


def test_assign1(interpreter: InternalPythonInterpreter):
    code = "a, b = c = 2, 3"
    interpreter.execute(code)
    assert interpreter.state["a"] == 2
    assert interpreter.state["b"] == 3
    assert interpreter.state["c"] == (2, 3)


def test_assign_fail(interpreter: InternalPythonInterpreter):
    code = "x = a, b, c = 2, 3"
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code, keep_state=False)
    exec_msg = e.value.args[0]
    assert exec_msg == (
        "Evaluation of the code stopped at node 0. See:\n"
        "Expected 3 values but got 2."
    )


def test_if0(interpreter: InternalPythonInterpreter):
    code = """a = 0
b = 1
if a < b:
    t = a
    a = b
    b = t
else:
    b = a"""
    interpreter.execute(code)
    assert interpreter.state["a"] == 1
    assert interpreter.state["b"] == 0


def test_if1(interpreter: InternalPythonInterpreter):
    code = """a = 1
b = 0
if a < b:
    t = a
    a = b
    b = t
else:
    b = a"""
    interpreter.execute(code)
    assert interpreter.state["a"] == 1
    assert interpreter.state["b"] == 1


def test_compare(interpreter: InternalPythonInterpreter):
    assert interpreter.execute("2 > 1") is True
    assert interpreter.execute("2 >= 1") is True
    assert interpreter.execute("2 < 1") is False
    assert interpreter.execute("2 == 1") is False
    assert interpreter.execute("2 != 1") is True
    assert interpreter.execute("1 <= 1") is True
    assert interpreter.execute("True is True") is True
    assert interpreter.execute("1 is not str") is True
    assert interpreter.execute("1 in [1, 2]") is True
    assert interpreter.execute("1 not in [1, 2]") is False


def test_oprators(interpreter: InternalPythonInterpreter):
    assert interpreter.execute("1 + 1") == 2
    assert interpreter.execute("1 - 1") == 0
    assert interpreter.execute("1 * 1") == 1
    assert interpreter.execute("1 / 2") == 0.5
    assert interpreter.execute("1 // 2") == 0
    assert interpreter.execute("1 % 2") == 1
    assert interpreter.execute("2 ** 2") == 4
    assert interpreter.execute("10 >> 2") == 2
    assert interpreter.execute("1 << 2") == 4
    assert interpreter.execute("+1") == 1
    assert interpreter.execute("-1") == -1
    assert interpreter.execute("not True") is False


def test_for(interpreter: InternalPythonInterpreter):
    code = """l = [2, 3, 5, 7, 11]
sum = 0
for i in l:
    sum = sum + i"""
    execution_res = interpreter.execute(code)
    assert execution_res == 28


def test_subscript_access(interpreter: InternalPythonInterpreter):
    code = """l = [2, 3, 5, 7, 11]
res = l[3]"""
    execution_res = interpreter.execute(code)
    assert execution_res == 7


def test_subscript_assign(interpreter: InternalPythonInterpreter):
    code = """l = [2, 3, 5, 7, 11]
l[3] = 1"""
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code, keep_state=False)
    exec_msg = e.value.args[0]
    assert exec_msg == (
        "Evaluation of the code stopped at node 1. See:\n"
        "Unsupported variable type. Expected ast.Name or "
        "ast.Tuple, got Subscript instead."
    )


def test_dict(interpreter: InternalPythonInterpreter):
    code = """x = {1: 10, 2: 20}
y = {"number": 30, **x}
res = y[1] + y[2] + y["numbers"]"""
    execution_res = interpreter.execute(code)
    assert execution_res == 60


def test_formatted_value(interpreter: InternalPythonInterpreter):
    code = """x = 3
res = f"x = {x}"
    """
    execution_res = interpreter.execute(code)
    assert execution_res == "x = 3"


def test_joined_str(interpreter: InternalPythonInterpreter):
    code = """l = ["2", "3", "5", "7", "11"]
res = ",".join(l)"""
    execution_res = interpreter.execute(code)
    assert execution_res == "2,3,5,7,11"


def test_expression_not_support(interpreter: InternalPythonInterpreter):
    code = """x = 1
x += 1"""
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code, keep_state=False)
    exec_msg = e.value.args[0]
    assert exec_msg == (
        "Evaluation of the code stopped at node 1. See:"
        "\nAugAssign is not supported."
    )


def test_allow_builtins(interpreter: InternalPythonInterpreter):
    code = "res = len([0, 1])"
    execution_res = interpreter.execute(code)
    assert execution_res == 2


@pytest.fixture
def unsafe_interpreter():
    interpreter = InternalPythonInterpreter()
    interpreter.unsafe_mode = True
    return interpreter


def test_unsafe_mode_eval(unsafe_interpreter):
    # Test basic arithmetic
    result = unsafe_interpreter.run("2 + 2", code_type="python")
    assert result == "4"

    # Test string operations
    result = unsafe_interpreter.run("'hello' + ' world'", code_type="python")
    assert result == "hello world"

    # Test built-in functions
    result = unsafe_interpreter.run("len([1, 2, 3])", code_type="python")
    assert result == "3"


def test_unsafe_mode_exec(unsafe_interpreter):
    # Test print statement
    result = unsafe_interpreter.run("print('hello world')", code_type="python")
    assert result == "hello world\n"  # exec returns captured stdout

    # Test multiple print statements
    code = """
print('line 1')
print('line 2')
"""
    result = unsafe_interpreter.run(code, code_type="python")
    assert result == "line 1\nline 2\n"  # exec returns captured stdout

    # Test variable assignment without print
    code = """
x = 42
y = x * 2
"""
    result = unsafe_interpreter.run(code, code_type="python")
    assert result == ""  # exec returns empty string when no stdout

    # Test variable assignment with print
    code = """
x = 42
print(f'The value is {x}')
"""
    result = unsafe_interpreter.run(code, code_type="python")
    assert result == "The value is 42\n"  # exec returns captured stdout


def test_unsafe_mode_complex_operations(unsafe_interpreter):
    # Test list comprehension with eval
    result = unsafe_interpreter.run(
        "[x * 2 for x in range(3)]", code_type="python"
    )
    assert result == "[0, 2, 4]"  # eval returns str of result

    # Test function definition and execution
    code = """
def greet(name):
    print(f'Hello, {name}!')
greet('World')
"""
    result = unsafe_interpreter.run(code, code_type="python")
    assert result == "Hello, World!\n"  # exec returns captured stdout

    # Test multiple operations with variable scope
    code = """
total = 0
for i in range(5):
    total += i
print(f'Sum: {total}')
"""
    result = unsafe_interpreter.run(code, code_type="python")
    assert result == "Sum: 10\n"  # exec returns captured stdout


@pytest.fixture()
def not_allow_builtins_interpreter():
    interpreter = InternalPythonInterpreter(
        raise_error=True, allow_builtins=False
    )
    return interpreter


def test_not_allow_builtins(
    not_allow_builtins_interpreter: InternalPythonInterpreter,
):
    code = "res = len([0, 1])"
    with pytest.raises(InterpreterError) as e:
        not_allow_builtins_interpreter.execute(code)
    exec_msg = e.value.args[0]
    assert "The variable `len` is not defined." in exec_msg
