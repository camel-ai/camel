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
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits.ubuntu_toolkit import UbuntuToolkit


@pytest.fixture
def toolkit(tmp_path):
    return UbuntuToolkit(working_directory=str(tmp_path))


def test_initialization_defaults():
    toolkit = UbuntuToolkit()
    assert toolkit.command_timeout == 120
    assert toolkit.working_directory == os.getcwd()


def test_initialization_custom():
    toolkit = UbuntuToolkit(
        command_timeout=60,
        working_directory="/tmp",
        timeout=10.0,
    )
    assert toolkit.command_timeout == 60
    assert toolkit.working_directory == "/tmp"


def test_get_tools(toolkit):
    tools = toolkit.get_tools()
    assert len(tools) == 9
    tool_names = [t.get_function_name() for t in tools]
    assert "execute_command" in tool_names
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "list_directory" in tool_names
    assert "search_files" in tool_names
    assert "install_package" in tool_names
    assert "get_system_info" in tool_names
    assert "get_process_list" in tool_names
    assert "get_network_info" in tool_names


def test_execute_command_success(toolkit):
    result = toolkit.execute_command("echo hello")
    assert result == "hello"


def test_execute_command_invalid_syntax(toolkit):
    result = toolkit.execute_command("echo 'unterminated")
    assert "Error" in result


def test_execute_command_empty(toolkit):
    result = toolkit.execute_command("")
    assert "Error" in result


def test_execute_command_not_found(toolkit):
    result = toolkit.execute_command("nonexistent_command_xyz")
    assert "Error" in result


@patch("camel.toolkits.ubuntu_toolkit.subprocess.run")
def test_execute_command_timeout(mock_run, toolkit):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=120)
    result = toolkit.execute_command("sleep 999")
    assert "timed out" in result


def test_read_file(toolkit, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    result = toolkit.read_file("test.txt")
    assert result == "hello world"


def test_read_file_not_found(toolkit):
    result = toolkit.read_file("nonexistent.txt")
    assert "Error" in result
    assert "not found" in result


def test_write_file(toolkit, tmp_path):
    result = toolkit.write_file("output.txt", "test content")
    assert "Successfully" in result
    assert (tmp_path / "output.txt").read_text() == "test content"


def test_write_file_nested_dirs(toolkit, tmp_path):
    result = toolkit.write_file("subdir/output.txt", "nested content")
    assert "Successfully" in result
    assert (tmp_path / "subdir" / "output.txt").read_text() == "nested content"


def test_list_directory(toolkit, tmp_path):
    (tmp_path / "file_a.txt").touch()
    (tmp_path / "file_b.txt").touch()
    result = toolkit.list_directory(".")
    assert "file_a.txt" in result
    assert "file_b.txt" in result


def test_list_directory_empty(toolkit, tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    result = toolkit.list_directory("empty")
    assert "empty" in result.lower()


def test_list_directory_not_found(toolkit):
    result = toolkit.list_directory("nonexistent_dir")
    assert "Error" in result


def test_search_files(toolkit, tmp_path):
    (tmp_path / "test.py").touch()
    (tmp_path / "test.txt").touch()
    result = toolkit.search_files("*.py", ".")
    assert "test.py" in result


@patch("camel.toolkits.ubuntu_toolkit.subprocess.run")
def test_install_package(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="Package installed", stderr=""
    )
    result = toolkit.install_package("curl")
    assert "Package installed" in result
    call_args = mock_run.call_args[0][0]
    assert "apt-get" in call_args
    assert "curl" in call_args


@patch("camel.toolkits.ubuntu_toolkit.subprocess.run")
def test_get_system_info(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="mock output", stderr=""
    )
    result = toolkit.get_system_info()
    assert "OS Info" in result
    assert "Kernel" in result
    assert "CPU Cores" in result
    assert "Memory" in result
    assert "Disk" in result


@patch("camel.toolkits.ubuntu_toolkit.subprocess.run")
def test_get_process_list(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="USER PID %CPU\nroot 1 0.0",
        stderr="",
    )
    result = toolkit.get_process_list()
    assert "PID" in result


@patch("camel.toolkits.ubuntu_toolkit.subprocess.run")
def test_get_network_info(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="eth0: flags=4163", stderr=""
    )
    result = toolkit.get_network_info()
    assert "eth0" in result


@patch("camel.toolkits.ubuntu_toolkit.subprocess.run")
def test_get_network_info_fallback(mock_run, toolkit):
    # First call (ip addr) fails, second call (ifconfig) succeeds
    mock_run.side_effect = [
        MagicMock(
            returncode=0,
            stdout="Error: Command not found: ip",
            stderr="",
        ),
        MagicMock(returncode=0, stdout="eth0: flags=4163", stderr=""),
    ]
    result = toolkit.get_network_info()
    assert "Error: Command not found" in result or "eth0" in result


@patch("camel.toolkits.ubuntu_toolkit.subprocess.run")
def test_run_command_nonzero_exit(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=1, stdout="", stderr="permission denied"
    )
    result = toolkit.execute_command("some_command")
    assert "Error" in result
    assert "permission denied" in result
