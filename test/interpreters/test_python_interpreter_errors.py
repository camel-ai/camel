# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import pytest

from camel.interpreters import InternalPythonInterpreter, InterpreterError


@pytest.fixture()
def interpreter():
    return InternalPythonInterpreter(require_confirm=False)


@pytest.fixture()
def raising_interpreter():
    return InternalPythonInterpreter(
        require_confirm=False,
        raise_error=True,
    )


@pytest.mark.parametrize(
    "code, error_name",
    [
        ("x = 1 / 0", "ZeroDivisionError"),
        ("x = 1 + 'a'", "TypeError"),
        ("x = int('not a number')", "ValueError"),
    ],
)
def test_native_error_is_reported_when_not_raising(
    interpreter: InternalPythonInterpreter, code: str, error_name: str
):
    r"""With ``raise_error=False`` a runtime error must be reported as a
    traceback string, exactly like interpreter errors are."""
    result = interpreter.execute(code)

    assert isinstance(result, str)
    assert error_name in result


@pytest.mark.parametrize(
    "code, error_name",
    [
        ("x = 1 / 0", "ZeroDivisionError"),
        ("x = 1 + 'a'", "TypeError"),
    ],
)
def test_native_error_is_wrapped_when_raising(
    raising_interpreter: InternalPythonInterpreter, code: str, error_name: str
):
    r"""With ``raise_error=True`` a runtime error must surface as
    ``InterpreterError``, keeping the original exception as its cause."""
    with pytest.raises(InterpreterError) as excinfo:
        raising_interpreter.execute(code)

    assert error_name in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, Exception)


def test_native_error_clears_state(
    raising_interpreter: InternalPythonInterpreter,
):
    r"""A failed execution must not leak partially built state when
    ``keep_state`` is False."""
    raising_interpreter.execute("leaked = 1")
    with pytest.raises(InterpreterError):
        raising_interpreter.execute("x = 1 / 0", keep_state=False)

    with pytest.raises(InterpreterError):
        raising_interpreter.execute("leaked")
