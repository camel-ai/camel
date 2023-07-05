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
import numpy as np
import pytest
import torch

from camel.utils import PythonInterpreter
from camel.utils.python_interpreter import InterpreterError


def action_function():
    return "access action function"


@pytest.fixture()
def interpreter():
    action_space = {"action1": action_function}
    white_list = ["torch", "numpy.array", "openai"]
    return PythonInterpreter(action_space=action_space,
                             import_white_list=white_list)


def test_import_success0(interpreter):
    code = """import torch as pt, openai
a = pt.tensor([[1., -1.], [1., -1.]])
openai.__version__"""
    execution_res = interpreter.execute(code)
    assert torch.equal(interpreter.state["a"],
                       torch.tensor([[1., -1.], [1., -1.]]))
    assert isinstance(execution_res, str)


def test_import_success1(interpreter):
    code = """from torch import tensor
a = tensor([[1., -1.], [1., -1.]])"""
    execution_res = interpreter.execute(code)
    assert torch.equal(execution_res, torch.tensor([[1., -1.], [1., -1.]]))


def test_import_success2(interpreter):
    code = """from numpy import array
x = array([[1, 2, 3], [4, 5, 6]])"""
    execution_res = interpreter.execute(code)
    assert np.equal(execution_res, np.array([[1, 2, 3], [4, 5, 6]])).all()


def test_import_fail0(interpreter):
    code = """import os
os.mkdir("/tmp/test")"""
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code)
    exec_msg = e.value.args[0]
    assert exec_msg == ("Evaluation of the code stopped at node 0. See:\n"
                        "It is not permitted to import modules than module"
                        " white list (try to import os).")


def test_import_fail1(interpreter):
    code = """import numpy as np
x = np.array([[1, 2, 3], [4, 5, 6]], np.int32)"""
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code)
    exec_msg = e.value.args[0]
    assert exec_msg == ("Evaluation of the code stopped at node 0. See:\n"
                        "It is not permitted to import modules than module"
                        " white list (try to import numpy).")


def test_action_space(interpreter):
    code = "res = action1()"
    execution_res = interpreter.execute(code)
    assert execution_res == "access action function"


def test_fuzz_space(interpreter):
    from PIL import Image
    fuzz_state = {"image": Image.new("RGB", (256, 256))}
    code = "output_image = input_image.crop((20, 20, 100, 100))"
    execution_res = interpreter.execute(code, fuzz_state=fuzz_state)
    assert execution_res.width == 80
    assert execution_res.height == 80


def test_keep_state0(interpreter):
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
    assert exec_msg == ("Evaluation of the code stopped at node 0. See:\n"
                        "The variable `b` is not defined.")


def test_keep_state1(interpreter):
    code1 = "from torch import tensor"
    code2 = "a = tensor([[1., -1.], [1., -1.]])"
    execution_res = interpreter.execute(code1, keep_state=True)
    execution_res = interpreter.execute(code2, keep_state=False)
    assert torch.equal(execution_res, torch.tensor([[1., -1.], [1., -1.]]))
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code2, keep_state=False)
    exec_msg = e.value.args[0]
    assert exec_msg == ("Evaluation of the code stopped at node 0. See:\n"
                        "The variable `tensor` is not defined.")


def test_assign0(interpreter):
    code = "a = b = 1"
    interpreter.execute(code)
    assert interpreter.state["a"] == 1
    assert interpreter.state["b"] == 1


def test_assign1(interpreter):
    code = "a, b = c = 2, 3"
    interpreter.execute(code)
    assert interpreter.state["a"] == 2
    assert interpreter.state["b"] == 3
    assert interpreter.state["c"] == (2, 3)


def test_assign_fail(interpreter):
    code = "x = a, b, c = 2, 3"
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code, keep_state=False)
    exec_msg = e.value.args[0]
    assert exec_msg == ("Evaluation of the code stopped at node 0. See:\n"
                        "Expected 3 values but got 2.")


def test_if(interpreter):
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


def test_for(interpreter):
    code = """l = [2, 3, 5, 7, 11]
sum = 0
for i in l:
    sum = sum + i"""
    execution_res = interpreter.execute(code)
    assert execution_res == 28


def test_subscript_access(interpreter):
    code = """l = [2, 3, 5, 7, 11]
res = l[3]"""
    execution_res = interpreter.execute(code)
    assert execution_res == 7


def test_subscript_assign(interpreter):
    code = """l = [2, 3, 5, 7, 11]
l[3] = 1"""
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code, keep_state=False)
    exec_msg = e.value.args[0]
    assert exec_msg == ("Evaluation of the code stopped at node 1. See:\n"
                        "Unsupported variable type. Expected ast.Name or "
                        "ast.Tuple, got Subscript instead.")
