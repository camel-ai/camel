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
import platform
import tempfile
from pathlib import Path

import pytest

from camel.toolkits import TerminalToolkit


@pytest.fixture
def terminal_toolkit(temp_dir):
    return TerminalToolkit(working_directory=temp_dir, safe_mode=False)


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
    assert toolkit.timeout == 20.0
    assert isinstance(toolkit.shell_sessions, dict)
    assert toolkit.os_type == platform.system()


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

    # Test session persistence
    session_id = "persistent_session"
    terminal_toolkit.shell_exec(session_id, "echo 'test1'")
    assert session_id in terminal_toolkit.shell_sessions
    assert terminal_toolkit.shell_sessions[session_id]["output"] != ""


def test_shell_exec_multiple_sessions(terminal_toolkit, temp_dir):
    # Test multiple concurrent sessions
    session1 = "session1"
    session2 = "session2"

    result1 = terminal_toolkit.shell_exec(
        session1,
        "echo 'Session 1'",
    )
    result2 = terminal_toolkit.shell_exec(
        session2,
        "echo 'Session 2'",
    )

    assert "Session 1" in result1
    assert "Session 2" in result2
    assert session1 in terminal_toolkit.shell_sessions
    assert session2 in terminal_toolkit.shell_sessions
