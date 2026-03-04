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

from camel.interpreters import ExecSandboxInterpreter, InterpreterError

try:
    import exec_sandbox  # noqa: F401

    _exec_sandbox_available = True
except ImportError:
    _exec_sandbox_available = False

pytestmark = pytest.mark.skipif(
    not _exec_sandbox_available,
    reason="exec-sandbox is not installed. "
    "Install with: pip install 'camel-ai[exec-sandbox]'",
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def interpreter():
    """Create an ExecSandboxInterpreter for real execution."""
    interp = ExecSandboxInterpreter(require_confirm=False, timeout=30)
    yield interp
    interp.close()


# ============================================================================
# Normal cases — Python
# ============================================================================


def test_python_stdout(interpreter: ExecSandboxInterpreter):
    code = """
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def main():
    result = subtract(10, 20)
    print(result)

if __name__ == "__main__":
    main()
"""
    result = interpreter.run(code, "python")
    assert "-10" in result


def test_python_stderr(interpreter: ExecSandboxInterpreter):
    code = """
def divide(a, b):
    return a / b

divide(10, 0)
"""
    result = interpreter.run(code, "python")
    assert "ZeroDivisionError" in result


def test_python_multiline(interpreter: ExecSandboxInterpreter):
    result = interpreter.run("for i in range(3):\n    print(i)", "python")
    assert "0" in result
    assert "1" in result
    assert "2" in result


def test_python_unicode(interpreter: ExecSandboxInterpreter):
    result = interpreter.run("print('Hello 🌍 你好')", "python")
    assert "🌍" in result
    assert "你好" in result


# ============================================================================
# Normal cases — JavaScript
# ============================================================================


def test_javascript_stdout(interpreter: ExecSandboxInterpreter):
    result = interpreter.run("console.log(6 * 7)", "javascript")
    assert "42" in result


def test_javascript_stderr(interpreter: ExecSandboxInterpreter):
    result = interpreter.run("undefined_function()", "javascript")
    assert "not defined" in result or "not a function" in result


# ============================================================================
# Normal cases — Shell
# ============================================================================


def test_bash_stdout(interpreter: ExecSandboxInterpreter):
    code = """
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


def test_bash_stderr(interpreter: ExecSandboxInterpreter):
    result = interpreter.run("undefined_command 123", "bash")
    assert "not found" in result


def test_execute_command(interpreter: ExecSandboxInterpreter):
    result = interpreter.execute_command("echo hello")
    assert "hello" in result


# ============================================================================
# Normal cases — Code type aliases
# ============================================================================


def test_code_type_aliases(interpreter: ExecSandboxInterpreter):
    assert "0" in interpreter.run("print(0)", "py3")
    assert "0" in interpreter.run("console.log(0)", "ts")
    assert "0" in interpreter.run("echo 0", "sh")
    assert "0" in interpreter.run("console.log(0)", "node")


def test_code_type_case_insensitive(interpreter: ExecSandboxInterpreter):
    for variant in ("Python", "PYTHON", "Py"):
        result = interpreter.run("print('ok')", variant)
        assert "ok" in result


# ============================================================================
# Session persistence
# ============================================================================


def test_session_variable_persists(interpreter: ExecSandboxInterpreter):
    """Variable defined in call 1 is available in call 2."""
    interpreter.run("x = 42", "python")
    result = interpreter.run("print(x)", "python")
    assert "42" in result


def test_session_function_persists(interpreter: ExecSandboxInterpreter):
    """Function defined in call 1 can be called in call 2."""
    interpreter.run("def greet(name): return f'hello {name}'", "python")
    result = interpreter.run("print(greet('world'))", "python")
    assert "hello world" in result


def test_session_import_persists(interpreter: ExecSandboxInterpreter):
    """Imports persist across calls."""
    interpreter.run("import math", "python")
    result = interpreter.run("print(math.pi)", "python")
    assert "3.14" in result


def test_session_isolated_per_language(interpreter: ExecSandboxInterpreter):
    """Python and JavaScript sessions don't share state."""
    interpreter.run("x = 'from_python'", "python")
    result = interpreter.run(
        "try { console.log(x) } catch(e) { console.log('undefined') }",
        "javascript",
    )
    assert "undefined" in result


def test_session_bash_env_persists(interpreter: ExecSandboxInterpreter):
    """Environment variable set in call 1 is available in call 2."""
    interpreter.run("export MY_VAR=hello", "bash")
    result = interpreter.run("echo $MY_VAR", "bash")
    assert "hello" in result


# ============================================================================
# Edge cases
# ============================================================================


def test_empty_output(interpreter: ExecSandboxInterpreter):
    """Code with no output returns success message."""
    result = interpreter.run("x = 1", "python")
    assert result == "Code executed successfully (no output)"


def test_nonzero_exit_code(interpreter: ExecSandboxInterpreter):
    result = interpreter.run("exit 1", "bash")
    assert "Exit code: 1" in result


def test_large_output(interpreter: ExecSandboxInterpreter):
    """Large output is not truncated."""
    result = interpreter.run(
        "for i in range(1000):\n    print(f'line {i}')", "python"
    )
    assert "line 0" in result
    assert "line 999" in result


def test_stderr_only_exit_zero(interpreter: ExecSandboxInterpreter):
    """Code that writes to stderr but exits 0."""
    result = interpreter.run(
        "import sys; sys.stderr.write('warning\\n')", "python"
    )
    assert "STDERR: warning" in result


def test_session_survives_error(interpreter: ExecSandboxInterpreter):
    """Non-zero exit code does not kill the session."""
    # First call raises an error
    result1 = interpreter.run("raise ValueError('boom')", "python")
    assert "ValueError" in result1
    # Second call still works in the same session
    result2 = interpreter.run("print('still alive')", "python")
    assert "still alive" in result2


# ============================================================================
# Weird cases
# ============================================================================


def test_redefine_variable(interpreter: ExecSandboxInterpreter):
    """Overwriting a variable works across calls."""
    interpreter.run("x = 1", "python")
    interpreter.run("x = 2", "python")
    result = interpreter.run("print(x)", "python")
    assert "2" in result


def test_delete_variable_then_access(interpreter: ExecSandboxInterpreter):
    """Deleting a variable makes it unavailable."""
    interpreter.run("x = 1", "python")
    interpreter.run("del x", "python")
    result = interpreter.run(
        "try:\n    print(x)\nexcept NameError:\n    print('gone')",
        "python",
    )
    assert "gone" in result


def test_interleave_languages(interpreter: ExecSandboxInterpreter):
    """Interleaving Python and JS calls doesn't corrupt either session."""
    interpreter.run("x = 'py'", "python")
    interpreter.run("let y = 'js'", "javascript")
    result_py = interpreter.run("print(x)", "python")
    result_js = interpreter.run("console.log(y)", "javascript")
    assert "py" in result_py
    assert "js" in result_js


def test_close_then_reuse(interpreter: ExecSandboxInterpreter):
    """Closing and reusing recreates sessions from scratch."""
    interpreter.run("x = 42", "python")
    interpreter.close()
    # After close, a new run should work (new session, no state)
    result = interpreter.run("print('fresh')", "python")
    assert "fresh" in result


# ============================================================================
# Out of bounds / error cases
# ============================================================================


def test_unsupported_code_type(interpreter: ExecSandboxInterpreter):
    with pytest.raises(InterpreterError, match="Unsupported code type"):
        interpreter.run("code", "ruby")


def test_require_confirm_refused(
    interpreter: ExecSandboxInterpreter,
    monkeypatch: pytest.MonkeyPatch,
):
    interpreter.require_confirm = True
    monkeypatch.setattr("builtins.input", lambda _: "n")
    with pytest.raises(InterpreterError, match="Execution halted"):
        interpreter.run("print('hello')", "python")


def test_require_confirm_accepted(
    interpreter: ExecSandboxInterpreter,
    monkeypatch: pytest.MonkeyPatch,
):
    interpreter.require_confirm = True
    monkeypatch.setattr("builtins.input", lambda _: "y")
    result = interpreter.run("print('hello')", "python")
    assert "hello" in result


def test_timeout():
    """Infinite loop should be killed by timeout."""
    short_timeout = ExecSandboxInterpreter(require_confirm=False, timeout=3)
    try:
        result = short_timeout.run("while True: pass", "python")
        # exec-sandbox returns timeout as exit_code=-1 with stderr message
        assert "Exit code:" in result or "timeout" in result.lower()
    finally:
        short_timeout.close()
