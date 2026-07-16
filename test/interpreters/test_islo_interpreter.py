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

import os
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("islo")

from camel.interpreters import (  # noqa: E402
    InterpreterError,
    IsloInterpreter,
)


def _mock_exec_response(exec_id="e1", sandbox_id="s1", status="running"):
    """Build a mock ExecResponse."""
    response = MagicMock()
    response.exec_id = exec_id
    response.sandbox_id = sandbox_id
    response.status = status
    return response


def _mock_exec_result(
    exec_id="e1",
    status="completed",
    stdout="",
    stderr="",
    exit_code=0,
    truncated=False,
):
    """Build a mock ExecResultResponse."""
    result = MagicMock()
    result.exec_id = exec_id
    result.status = status
    result.stdout = stdout
    result.stderr = stderr
    result.exit_code = exit_code
    result.truncated = truncated
    return result


def _mock_sandbox(status="running", name="camel-islo-test"):
    """Build a mock SandboxResponse."""
    sandbox = MagicMock()
    sandbox.status = status
    sandbox.name = name
    return sandbox


def _make_interpreter(mock_islo_cls, **kwargs):
    """Create an IsloInterpreter with a mocked Islo client."""
    client = MagicMock()
    mock_islo_cls.return_value = client
    kwargs.setdefault("require_confirm", False)
    kwargs.setdefault("api_key", "test-key")
    kwargs.setdefault("poll_interval", 0.01)
    interpreter = IsloInterpreter(**kwargs)
    return interpreter, client


def _setup_happy_path(client, exec_result=None):
    """Configure the mocked client for a successful execution."""
    client.sandboxes.get_sandbox.return_value = _mock_sandbox("running")
    client.sandboxes.exec_in_sandbox.return_value = _mock_exec_response()
    client.sandboxes.get_exec_result.return_value = (
        exec_result if exec_result is not None else _mock_exec_result()
    )


@patch('islo.Islo')
def test_init_with_explicit_params(mock_islo):
    """Test initialization with explicit parameters is lazy."""
    interpreter, client = _make_interpreter(
        mock_islo,
        sandbox_name="my-sandbox",
        image="custom-image:latest",
    )

    assert interpreter.require_confirm is False
    assert interpreter.sandbox_name == "my-sandbox"
    assert interpreter.image == "custom-image:latest"
    # The interpreter attaches to an existing sandbox, so it must not
    # delete it by default.
    assert interpreter.delete_on_exit is False

    mock_islo.assert_called_once_with(api_key="test-key")
    # Sandbox creation is lazy: nothing is created at init time.
    client.sandboxes.create_sandbox.assert_not_called()


@patch.dict(os.environ, {'ISLO_API_KEY': 'env-test-key'})
@patch('islo.Islo')
def test_init_with_env_var(mock_islo):
    """Test initialization from the ISLO_API_KEY environment variable."""
    interpreter = IsloInterpreter(require_confirm=False)

    # No explicit key: the SDK client resolves ISLO_API_KEY itself.
    mock_islo.assert_called_once_with(api_key=None)
    assert interpreter.delete_on_exit is True


@patch('islo.Islo')
def test_unsupported_code_type(mock_islo):
    """Test unsupported code type raises error without touching client."""
    interpreter, client = _make_interpreter(mock_islo)

    with pytest.raises(InterpreterError) as exc_info:
        interpreter.run("print(1)", "unsupported_language")

    assert "Unsupported code type" in str(exc_info.value)
    client.sandboxes.create_sandbox.assert_not_called()
    client.sandboxes.exec_in_sandbox.assert_not_called()


@patch('islo.Islo')
def test_run_python_happy_path(mock_islo):
    """Test a successful python run with two-step async exec polling."""
    interpreter, client = _make_interpreter(mock_islo)
    client.sandboxes.get_sandbox.return_value = _mock_sandbox("running")
    client.sandboxes.exec_in_sandbox.return_value = _mock_exec_response()
    client.sandboxes.get_exec_result.side_effect = [
        _mock_exec_result(status="running"),
        _mock_exec_result(status="completed", stdout="hi", exit_code=0),
    ]

    code = "print('hi')"
    result = interpreter.run(code, "python")

    assert result == "hi"
    client.sandboxes.create_sandbox.assert_called_once()
    create_kwargs = client.sandboxes.create_sandbox.call_args.kwargs
    assert create_kwargs["name"].startswith("camel-islo-")
    exec_kwargs = client.sandboxes.exec_in_sandbox.call_args.kwargs
    assert exec_kwargs["command"] == ["python3", "-c", code]
    assert client.sandboxes.get_exec_result.call_count == 2


@patch('islo.Islo')
def test_run_bash_command_mapping(mock_islo):
    """Test that bash code maps to ['bash', '-c', code]."""
    interpreter, client = _make_interpreter(mock_islo)
    _setup_happy_path(client, _mock_exec_result(stdout="ok"))

    interpreter.run("echo ok", "bash")

    exec_kwargs = client.sandboxes.exec_in_sandbox.call_args.kwargs
    assert exec_kwargs["command"] == ["bash", "-c", "echo ok"]


@patch('islo.Islo')
def test_run_with_stderr_and_exit_code(mock_islo):
    """Test that stderr and nonzero exit codes appear in the output."""
    interpreter, client = _make_interpreter(mock_islo)
    _setup_happy_path(
        client,
        _mock_exec_result(
            status="failed", stdout="out", stderr="boom", exit_code=1
        ),
    )

    result = interpreter.run("exit 1", "bash")

    assert "out" in result
    assert "[stderr] boom" in result
    assert "Exit code: 1" in result


@patch('islo.Islo')
def test_run_timeout_status_raises(mock_islo):
    """Test that a server-side timeout raises InterpreterError."""
    interpreter, client = _make_interpreter(mock_islo)
    _setup_happy_path(client, _mock_exec_result(status="timeout"))

    with pytest.raises(InterpreterError) as exc_info:
        interpreter.run("import time; time.sleep(999)", "python")

    assert "timed out" in str(exc_info.value)


@patch('islo.Islo')
def test_run_truncated_output(mock_islo):
    """Test that truncated results append a truncation notice."""
    interpreter, client = _make_interpreter(mock_islo)
    _setup_happy_path(
        client, _mock_exec_result(stdout="partial", truncated=True)
    )

    result = interpreter.run("print('x' * 10**9)", "python")

    assert "partial" in result
    assert "[output truncated]" in result


@patch('islo.Islo')
def test_execute_command(mock_islo):
    """Test execute_command runs the command through bash."""
    interpreter, client = _make_interpreter(mock_islo)
    _setup_happy_path(client, _mock_exec_result(stdout="file.txt"))

    result = interpreter.execute_command("ls")

    assert result == "file.txt"
    exec_kwargs = client.sandboxes.exec_in_sandbox.call_args.kwargs
    assert exec_kwargs["command"] == ["bash", "-c", "ls"]


@patch('islo.Islo')
def test_cleanup_deletes_owned_sandbox(mock_islo):
    """Test cleanup deletes a sandbox created by the interpreter."""
    interpreter, client = _make_interpreter(mock_islo)
    _setup_happy_path(client)

    interpreter.run("print(1)", "python")
    interpreter.cleanup()

    client.sandboxes.delete_sandbox.assert_called_once_with(
        sandbox_name=interpreter.sandbox_name
    )


@patch('islo.Islo')
def test_cleanup_keeps_attached_sandbox(mock_islo):
    """Test cleanup does not delete a sandbox attached by name."""
    interpreter, client = _make_interpreter(
        mock_islo, sandbox_name="existing-sandbox"
    )
    _setup_happy_path(client)

    interpreter.run("print(1)", "python")
    interpreter.cleanup()

    client.sandboxes.delete_sandbox.assert_not_called()


@patch('islo.Islo')
def test_update_action_space(mock_islo):
    """Test update_action_space raises RuntimeError."""
    interpreter, _ = _make_interpreter(mock_islo)

    with pytest.raises(RuntimeError):
        interpreter.update_action_space({"key": "value"})


@patch('islo.Islo')
def test_supported_code_types(mock_islo):
    """Test supported code types include the documented aliases."""
    interpreter, _ = _make_interpreter(mock_islo)
    supported_types = interpreter.supported_code_types()

    for code_type in (
        "python",
        "py3",
        "python3",
        "py",
        "bash",
        "shell",
        "sh",
        "javascript",
        "js",
        "node",
    ):
        assert code_type in supported_types


@patch('islo.Islo')
def test_paused_sandbox_is_resumed(mock_islo):
    """Test a paused sandbox is resumed before execution."""
    interpreter, client = _make_interpreter(
        mock_islo, sandbox_name="paused-sandbox"
    )
    client.sandboxes.get_sandbox.side_effect = [
        _mock_sandbox("paused"),
        _mock_sandbox("running"),
    ]
    client.sandboxes.exec_in_sandbox.return_value = _mock_exec_response()
    client.sandboxes.get_exec_result.return_value = _mock_exec_result(
        stdout="resumed"
    )

    result = interpreter.run("print('resumed')", "python")

    assert result == "resumed"
    client.sandboxes.resume_sandbox.assert_called_once_with(
        sandbox_name="paused-sandbox"
    )
    # Attached sandboxes are never re-created.
    client.sandboxes.create_sandbox.assert_not_called()


@patch('islo.Islo')
def test_startup_failure_deletes_created_sandbox(mock_islo):
    """Test a created sandbox is deleted when startup fails."""
    interpreter, client = _make_interpreter(mock_islo)
    client.sandboxes.get_sandbox.return_value = _mock_sandbox("failed")

    with pytest.raises(InterpreterError) as exc_info:
        interpreter.run("print(1)", "python")

    assert "failed" in str(exc_info.value)
    client.sandboxes.create_sandbox.assert_called_once()
    created_name = client.sandboxes.create_sandbox.call_args.kwargs["name"]
    # The billed cloud sandbox must not leak: it is deleted best-effort
    # before the startup failure propagates.
    client.sandboxes.delete_sandbox.assert_called_once_with(
        sandbox_name=created_name
    )
    client.sandboxes.exec_in_sandbox.assert_not_called()


@patch('islo.Islo')
def test_startup_failure_keeps_attached_sandbox(mock_islo):
    """Test an attached sandbox is not deleted when startup fails."""
    interpreter, client = _make_interpreter(
        mock_islo, sandbox_name="existing-sandbox"
    )
    client.sandboxes.get_sandbox.return_value = _mock_sandbox("failed")

    with pytest.raises(InterpreterError):
        interpreter.run("print(1)", "python")

    client.sandboxes.create_sandbox.assert_not_called()
    client.sandboxes.delete_sandbox.assert_not_called()


@patch('islo.Islo')
def test_failed_exec_with_no_output_reports_failure(mock_islo):
    """Test a failed execution with no output is not reported as
    success."""
    interpreter, client = _make_interpreter(mock_islo)
    _setup_happy_path(
        client,
        _mock_exec_result(
            status="failed", stdout="", stderr="", exit_code=None
        ),
    )

    result = interpreter.run("print(1)", "python")

    assert "failed" in result
    assert "successfully" not in result


@patch('islo.Islo')
def test_require_confirm_halts_execution(mock_islo):
    """Test declining the confirmation prompt halts execution."""
    interpreter, client = _make_interpreter(mock_islo, require_confirm=True)

    with patch('builtins.input', return_value='n'):
        with pytest.raises(InterpreterError) as exc_info:
            interpreter.run("print(1)", "python")

    assert "Execution halted" in str(exc_info.value)
    client.sandboxes.exec_in_sandbox.assert_not_called()
