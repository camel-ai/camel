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
    white_list = ["torch", "numpy.array"]
    return PythonInterpreter(action_space=action_space,
                             import_white_list=white_list)


def test_import_success0(interpreter):
    code = """import torch
a = torch.tensor([[1., -1.], [1., -1.]])"""
    rnt = interpreter.execute(code)
    assert torch.equal(interpreter.state["a"],
                       torch.tensor([[1., -1.], [1., -1.]]))
    assert torch.equal(rnt, torch.tensor([[1., -1.], [1., -1.]]))


def test_import_success1(interpreter):
    code = """from torch import tensor
a = tensor([[1., -1.], [1., -1.]])"""
    rnt = interpreter.execute(code)
    assert torch.equal(rnt, torch.tensor([[1., -1.], [1., -1.]]))


def test_import_success2(interpreter):
    code = """import torch as pytorch
a = pytorch.tensor([[1., -1.], [1., -1.]])"""
    rnt = interpreter.execute(code)
    assert torch.equal(rnt, torch.tensor([[1., -1.], [1., -1.]]))


def test_import_success3(interpreter):
    code = """from numpy import array
x = array([[1, 2, 3], [4, 5, 6]])"""
    rnt = interpreter.execute(code)
    assert np.equal(rnt, np.array([[1, 2, 3], [4, 5, 6]])).all()


def test_import_fail0(interpreter):
    code = """import os
os.mkdir("/tmp/test")"""
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code)
    exec_msg = e.value.args[0]
    assert exec_msg == ("Evaluation of the code stopped at line 0. See:\n"
                        "It is not permitted to import modules than module"
                        " white list (try to import os).")


def test_import_fail1(interpreter):
    code = """import numpy as np
x = np.array([[1, 2, 3], [4, 5, 6]], np.int32)"""
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code)
    exec_msg = e.value.args[0]
    assert exec_msg == ("Evaluation of the code stopped at line 0. See:\n"
                        "It is not permitted to import modules than module"
                        " white list (try to import numpy).")


def test_action_space(interpreter):
    code = "rnt = action1()"
    rnt = interpreter.execute(code)
    assert rnt == "access action function"


def test_fuzz_space(interpreter):
    from PIL import Image
    fuzz_state = {"image": Image.new("RGB", (256, 256))}
    code = "output_image = input_image.crop((20, 20, 100, 100))"
    rnt = interpreter.execute(code, fuzz_state=fuzz_state)
    assert rnt.width == 80
    assert rnt.height == 80


def test_keep_state0(interpreter):
    code1 = "a = 42"
    code2 = "b = a"
    code3 = "c = b"

    rnt = interpreter.execute(code1, keep_state=True)
    assert rnt == 42
    rnt = interpreter.execute(code2, keep_state=False)
    assert rnt == 42
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code3, keep_state=False)
    exec_msg = e.value.args[0]
    assert exec_msg == ("Evaluation of the code stopped at line 0. See:\n"
                        "The variable `b` is not defined.")


def test_keep_state1(interpreter):
    code1 = "from torch import tensor"
    code2 = "a = tensor([[1., -1.], [1., -1.]])"
    rnt = interpreter.execute(code1, keep_state=True)
    rnt = interpreter.execute(code2, keep_state=False)
    assert torch.equal(rnt, torch.tensor([[1., -1.], [1., -1.]]))
    with pytest.raises(InterpreterError) as e:
        interpreter.execute(code2, keep_state=False)
    exec_msg = e.value.args[0]
    assert exec_msg == ("Evaluation of the code stopped at line 0. See:\n"
                        "The variable `tensor` is not defined.")


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
    rnt = interpreter.execute(code)
    assert rnt == 28


def test_subscript(interpreter):
    code = """l = [2, 3, 5, 7, 11]
rnt = l[3]"""
    rnt = interpreter.execute(code)
    assert rnt == 7
