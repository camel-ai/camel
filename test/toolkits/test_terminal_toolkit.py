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
import platform
import tempfile
from pathlib import Path

import pytest

from camel.toolkits import TerminalToolkit
from camel.toolkits.terminal_toolkit import DANGEROUS_COMMANDS
from camel.toolkits.terminal_toolkit.utils import sanitize_command


@pytest.fixture
def terminal_toolkit(temp_dir, request):
    toolkit = TerminalToolkit(working_directory=temp_dir, safe_mode=False)
    # Ensure cleanup happens after test completes
    request.addfinalizer(toolkit.cleanup)
    return toolkit


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_file(temp_dir):
    file_path = temp_dir / "test.txt"
    content = "Hello\nWorld\nTest\nContent"
    file_path.write_text(content)
    return file_path


def test_init():
    toolkit = TerminalToolkit()
    try:
        assert toolkit.timeout == 20.0
        assert isinstance(toolkit.shell_sessions, dict)
        assert toolkit.os_type == platform.system()
    finally:
        toolkit.cleanup()


def test_shell_exec(terminal_toolkit, temp_dir):
    # Test basic command execution
    result = terminal_toolkit.shell_exec(
        "test_session",
        "echo 'Hello World'",
    )
    assert "Hello World" in result

    # Test command with error
    result = terminal_toolkit.shell_exec(
        "test_session",
        "nonexistent_command",
    )
    assert "not found" in result.lower()

    # Test session persistence - use non-blocking mode to create sessions
    session_id = "persistent_session"
    terminal_toolkit.shell_exec(session_id, "echo 'test1'", block=False)
    assert session_id in terminal_toolkit.shell_sessions
    # For non-blocking mode, check if session was created
    # (output might be empty initially)
    assert "output_stream" in terminal_toolkit.shell_sessions[session_id]


def test_shell_exec_multiple_sessions(terminal_toolkit, temp_dir):
    # Test multiple concurrent sessions - use non-blocking mode
    # to create sessions
    session1 = "session1"
    session2 = "session2"

    terminal_toolkit.shell_exec(
        session1,
        "echo 'Session 1'",
        block=False,
    )
    terminal_toolkit.shell_exec(
        session2,
        "echo 'Session 2'",
        block=False,
    )

    # For non-blocking mode, sessions should be created immediately
    assert session1 in terminal_toolkit.shell_sessions
    assert session2 in terminal_toolkit.shell_sessions


def test_shell_write_content_to_file_basic(temp_dir, request):
    """Test basic file writing functionality."""
    toolkit = TerminalToolkit(working_directory=str(temp_dir), safe_mode=False)
    request.addfinalizer(toolkit.cleanup)

    test_content = "Hello, World!"
    test_file = temp_dir / "test_write.txt"

    result = toolkit.shell_write_content_to_file(test_content, str(test_file))
    assert "successfully" in result.lower()
    assert test_file.exists()
    assert test_file.read_text() == test_content


def test_shell_write_content_to_file_with_subdirectory(temp_dir, request):
    """Test file writing with automatic parent directory creation."""
    toolkit = TerminalToolkit(working_directory=str(temp_dir), safe_mode=False)
    request.addfinalizer(toolkit.cleanup)

    test_content = "Nested content"
    # Create a path with non-existent subdirectory
    test_file = temp_dir / "subdir" / "nested" / "test.txt"

    result = toolkit.shell_write_content_to_file(test_content, str(test_file))
    assert "successfully" in result.lower()
    assert test_file.exists()
    assert test_file.read_text() == test_content


def test_shell_write_content_to_file_safe_mode_relative_path(
    temp_dir, request
):
    """Test safe mode with relative paths resolves correctly."""
    toolkit = TerminalToolkit(working_directory=str(temp_dir), safe_mode=True)
    request.addfinalizer(toolkit.cleanup)

    test_content = "Safe mode content"
    # Use a relative path - should be resolved relative to working_dir
    result = toolkit.shell_write_content_to_file(test_content, "relative.txt")
    assert "successfully" in result.lower()
    # File should be created inside working_dir
    expected_file = temp_dir / "relative.txt"
    assert expected_file.exists()
    assert expected_file.read_text() == test_content


def test_shell_write_content_to_file_safe_mode_blocks_path_traversal(
    temp_dir, request
):
    """Test that safe mode blocks path traversal attempts."""
    toolkit = TerminalToolkit(working_directory=str(temp_dir), safe_mode=True)
    request.addfinalizer(toolkit.cleanup)

    test_content = "Malicious content"
    # Attempt path traversal
    result = toolkit.shell_write_content_to_file(
        test_content, "../outside_working_dir.txt"
    )
    assert "error" in result.lower()
    assert "outside" in result.lower() or "working directory" in result.lower()


@pytest.mark.parametrize(
    "command",
    [
        'bash -c "rm -rf /"',
        "sh -c 'rm -rf /'",
    ],
)
def test_sanitize_command_blocks_dangerous_shell_c_payloads(temp_dir, command):
    """Dangerous commands in shell-wrapper payloads must be blocked."""
    is_safe, message = sanitize_command(command, working_dir=str(temp_dir))
    assert not is_safe
    assert "blocked for safety" in message.lower()


def test_sanitize_command_blocks_cd_expansion_outside_workdir(
    temp_dir, monkeypatch
):
    """Expanded env vars should be resolved before cd path validation."""
    outside_dir = temp_dir.parent
    monkeypatch.setenv("HOME", str(outside_dir))

    is_safe, message = sanitize_command("cd $HOME", working_dir=str(temp_dir))
    assert not is_safe
    assert "outside" in message.lower()
    assert "copy" in message.lower()
    assert "working directory" in message.lower()

    is_safe, message = sanitize_command(
        "cd ${HOME}", working_dir=str(temp_dir)
    )
    assert not is_safe
    assert "outside" in message.lower()
    assert "copy" in message.lower()


def test_shell_exec_cd_outside_returns_copy_guidance(temp_dir, request):
    """Shell exec should provide copy guidance for blocked cd traversal."""
    toolkit = TerminalToolkit(working_directory=str(temp_dir), safe_mode=True)
    request.addfinalizer(toolkit.cleanup)

    result = toolkit.shell_exec("test_session", "cd ../")
    lowered = result.lower()
    assert "error:" in lowered
    assert "outside of the working directory" in lowered
    assert "copy" in lowered
    assert str(temp_dir) in result


def test_shell_exec_safe_mode_rejection_prefix(temp_dir, request):
    """Blocked command errors should clearly mention safe mode rejection."""
    toolkit = TerminalToolkit(working_directory=str(temp_dir), safe_mode=True)
    request.addfinalizer(toolkit.cleanup)

    result = toolkit.shell_exec("test_session", "rm -rf /")
    lowered = result.lower()
    assert lowered.startswith("error:")
    assert "rejected by terminaltoolkit safe mode" in lowered
    assert "blocked for safety" in lowered


@pytest.mark.parametrize("command", ["cd $(pwd)", "cd `pwd`"])
def test_sanitize_command_blocks_cd_command_substitution(temp_dir, command):
    """Dynamic command substitutions in cd targets must be rejected."""
    is_safe, message = sanitize_command(command, working_dir=str(temp_dir))
    assert not is_safe
    assert "command substitution" in message.lower()


def test_sanitize_command_allows_expanded_cd_inside_workdir(
    temp_dir, monkeypatch
):
    """Expanded env vars pointing inside working_dir should remain allowed."""
    subdir = temp_dir / "inner"
    subdir.mkdir()
    monkeypatch.setenv("CAMEL_INSIDE_DIR", str(subdir))

    is_safe, message = sanitize_command(
        "cd $CAMEL_INSIDE_DIR", working_dir=str(temp_dir)
    )
    assert is_safe
    assert message == "cd $CAMEL_INSIDE_DIR"


def test_sanitize_command_blocks_cd_dash(temp_dir):
    """'cd -' goes to $OLDPWD which may be outside workdir; must be blocked."""
    is_safe, message = sanitize_command("cd -", working_dir=str(temp_dir))
    assert not is_safe
    assert "outside" in message.lower()


def test_sanitize_command_blocks_cd_double_dash_outside(temp_dir):
    """'cd -- /etc' should block since /etc is outside workdir."""
    is_safe, message = sanitize_command(
        "cd -- /etc", working_dir=str(temp_dir)
    )
    assert not is_safe
    assert "outside" in message.lower()


def test_sanitize_command_allows_cd_double_dash_inside(temp_dir):
    """'cd -- subdir' should be allowed when subdir is inside workdir."""
    subdir = temp_dir / "inner"
    subdir.mkdir()
    is_safe, message = sanitize_command(
        "cd -- inner", working_dir=str(temp_dir)
    )
    assert is_safe


def test_sanitize_command_blocks_pushd_outside_workdir(temp_dir):
    """pushd to a path outside workdir must be blocked like cd."""
    is_safe, message = sanitize_command(
        "pushd /etc", working_dir=str(temp_dir)
    )
    assert not is_safe
    assert "outside" in message.lower()


def test_sanitize_command_allows_pushd_inside_workdir(temp_dir):
    """pushd to a path inside workdir should be allowed."""
    subdir = temp_dir / "inner"
    subdir.mkdir()
    is_safe, message = sanitize_command(
        "pushd inner", working_dir=str(temp_dir)
    )
    assert is_safe


@pytest.mark.parametrize(
    "command",
    [
        "cd sub && cd ..",
        "cd sub; cd ..",
        "cd sub || cd ..",
        "false && cd sub; cd ..",
        "cd sub & cd ..",
    ],
)
def test_sanitize_command_blocks_multiple_cd_in_chain(temp_dir, command):
    """Multiple cd/pushd with shell operators must be rejected."""
    subdir = temp_dir / "sub"
    subdir.mkdir()
    is_safe, message = sanitize_command(command, working_dir=str(temp_dir))
    assert not is_safe
    assert "multiple" in message.lower()
    assert "separate command" in message.lower()


@pytest.mark.parametrize(
    "command",
    [
        "cd sub && ls",
        "cd sub && echo hello",
        "ls && cd sub",
        "echo hello; cd sub",
    ],
)
def test_sanitize_command_allows_single_cd_in_chain(temp_dir, command):
    """A single cd combined with non-cd commands should be allowed."""
    subdir = temp_dir / "sub"
    subdir.mkdir()
    is_safe, message = sanitize_command(command, working_dir=str(temp_dir))
    assert is_safe
    assert message == command


def test_sanitize_command_blocks_pushd_chain(temp_dir):
    """Multiple pushd in a chain must also be rejected."""
    subdir = temp_dir / "sub"
    subdir.mkdir()
    is_safe, message = sanitize_command(
        "pushd sub && pushd .", working_dir=str(temp_dir)
    )
    assert not is_safe
    assert "multiple" in message.lower()


def test_sanitize_command_blocks_mixed_cd_pushd_chain(temp_dir):
    """cd mixed with pushd in a chain must be rejected."""
    subdir = temp_dir / "sub"
    subdir.mkdir()
    is_safe, message = sanitize_command(
        "cd sub && pushd .", working_dir=str(temp_dir)
    )
    assert not is_safe
    assert "multiple" in message.lower()


def test_sanitize_command_respects_customized_dangerous_commands(
    temp_dir, monkeypatch
):
    r"""Module-level dangerous commands should be importable/customizable."""
    import camel.toolkits.terminal_toolkit.utils as terminal_utils

    custom_commands = DANGEROUS_COMMANDS.copy()
    custom_commands.append("echo")
    monkeypatch.setattr(terminal_utils, "DANGEROUS_COMMANDS", custom_commands)

    is_safe, message = sanitize_command(
        'echo "should be blocked"', working_dir=str(temp_dir)
    )
    assert not is_safe
    assert "echo" in message.lower()
