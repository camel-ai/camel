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
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import TerminalToolkit
from camel.toolkits.terminal_toolkit.go_runtime import (
    ensure_go_available,
)
from camel.toolkits.terminal_toolkit.java_runtime import (
    _find_java_home,
    ensure_java_available,
)
from camel.toolkits.terminal_toolkit.runtime_utils import (
    get_platform_info,
)


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





class TestGetPlatformInfo:
    """Tests for get_platform_info()."""

    @patch("camel.toolkits.terminal_toolkit.runtime_utils.platform")
    def test_linux_amd64(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "x86_64"
        os_name, arch = get_platform_info()
        assert os_name == "linux"
        assert arch == "amd64"

    @patch("camel.toolkits.terminal_toolkit.runtime_utils.platform")
    def test_darwin_arm64(self, mock_platform):
        mock_platform.system.return_value = "Darwin"
        mock_platform.machine.return_value = "arm64"
        os_name, arch = get_platform_info()
        assert os_name == "darwin"
        assert arch == "arm64"

    @patch("camel.toolkits.terminal_toolkit.runtime_utils.platform")
    def test_windows_amd64(self, mock_platform):
        mock_platform.system.return_value = "Windows"
        mock_platform.machine.return_value = "AMD64"
        os_name, arch = get_platform_info()
        assert os_name == "windows"
        assert arch == "amd64"

    @patch("camel.toolkits.terminal_toolkit.runtime_utils.platform")
    def test_unsupported_os(self, mock_platform):
        mock_platform.system.return_value = "FreeBSD"
        mock_platform.machine.return_value = "x86_64"
        with pytest.raises(
            RuntimeError, match="Unsupported operating system"
        ):
            get_platform_info()

    @patch("camel.toolkits.terminal_toolkit.runtime_utils.platform")
    def test_unsupported_arch(self, mock_platform):
        mock_platform.system.return_value = "Linux"
        mock_platform.machine.return_value = "mips"
        with pytest.raises(
            RuntimeError, match="Unsupported architecture"
        ):
            get_platform_info()


class TestEnsureGoAvailable:
    """Tests for ensure_go_available()."""

    @patch("camel.toolkits.terminal_toolkit.go_runtime.subprocess.run")
    @patch("camel.toolkits.terminal_toolkit.go_runtime.shutil.which")
    def test_go_already_installed(self, mock_which, mock_run):
        """Should return path without downloading if go is on PATH."""
        mock_which.return_value = "/usr/local/go/bin/go"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="go version go1.23.6 linux/amd64",
        )

        callback = MagicMock()
        path = ensure_go_available(update_callback=callback)

        assert path == "/usr/local/go/bin"
        callback.assert_called()
        # Should NOT have tried to download
        assert (
            "installing"
            not in str(callback.call_args_list).lower()
        )

    @patch(
        "camel.toolkits.terminal_toolkit.go_runtime"
        ".download_and_extract_runtime"
    )
    @patch(
        "camel.toolkits.terminal_toolkit.go_runtime"
        ".get_platform_info"
    )
    @patch(
        "camel.toolkits.terminal_toolkit.go_runtime"
        ".os.path.exists"
    )
    @patch(
        "camel.toolkits.terminal_toolkit.go_runtime"
        ".shutil.which"
    )
    def test_go_not_installed_downloads(
        self,
        mock_which,
        mock_exists,
        mock_platform,
        mock_download,
    ):
        """Should attempt download when go is not found."""
        mock_which.return_value = None
        mock_platform.return_value = ("linux", "amd64")
        # First call: check if already downloaded (False)
        # Second call: check after download (True)
        mock_exists.side_effect = [False, True]

        callback = MagicMock()
        path = ensure_go_available(update_callback=callback)

        assert path is not None
        mock_download.assert_called_once()
        # Verify the URL uses the template correctly
        call_kwargs = mock_download.call_args
        assert (
            "go1.23.6.linux-amd64.tar.gz"
            in call_kwargs.kwargs["url"]
        )

    @patch(
        "camel.toolkits.terminal_toolkit.go_runtime"
        ".get_platform_info"
    )
    @patch(
        "camel.toolkits.terminal_toolkit.go_runtime"
        ".shutil.which"
    )
    def test_go_unsupported_platform(
        self, mock_which, mock_platform
    ):
        """Should return None for unsupported platforms."""
        mock_which.return_value = None
        mock_platform.side_effect = RuntimeError("Unsupported")

        callback = MagicMock()
        path = ensure_go_available(update_callback=callback)

        assert path is None


class TestEnsureJavaAvailable:
    """Tests for ensure_java_available()."""

    @patch(
        "camel.toolkits.terminal_toolkit.java_runtime"
        ".subprocess.run"
    )
    @patch(
        "camel.toolkits.terminal_toolkit.java_runtime"
        ".shutil.which"
    )
    def test_java_already_installed(
        self, mock_which, mock_run
    ):
        """Should return path without downloading if java is on PATH."""
        mock_which.return_value = "/usr/lib/jvm/jdk-21/bin/java"
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr='openjdk version "21.0.2"',
            stdout="",
        )

        callback = MagicMock()
        path = ensure_java_available(update_callback=callback)

        assert path == "/usr/lib/jvm/jdk-21"
        callback.assert_called()

    @patch(
        "camel.toolkits.terminal_toolkit.java_runtime"
        ".download_and_extract_runtime"
    )
    @patch(
        "camel.toolkits.terminal_toolkit.java_runtime"
        "._find_java_home"
    )
    @patch(
        "camel.toolkits.terminal_toolkit.java_runtime"
        ".get_platform_info"
    )
    @patch(
        "camel.toolkits.terminal_toolkit.java_runtime"
        ".shutil.which"
    )
    def test_java_not_installed_downloads(
        self,
        mock_which,
        mock_platform,
        mock_find,
        mock_download,
    ):
        """Should attempt download when java is not found."""
        mock_which.return_value = None
        mock_platform.return_value = ("linux", "amd64")
        # First call: not found; second: found after download
        java_path = (
            "/home/user/.camel/runtimes/java/jdk-21"
        )
        mock_find.side_effect = [None, java_path]

        callback = MagicMock()
        path = ensure_java_available(
            update_callback=callback
        )

        assert path == java_path
        mock_download.assert_called_once()
        # Verify Adoptium URL uses correct mappings
        call_kwargs = mock_download.call_args
        call_url = call_kwargs.kwargs["url"]
        assert call_url.startswith(
            "https://api.adoptium.net/v3/binary/latest/"
            "21/ga/linux/x64/"
        )


class TestFindJavaHome:
    """Tests for _find_java_home()."""

    def test_finds_linux_java_home(self, tmp_path):
        """Should find JAVA_HOME on Linux directory structure."""
        jdk_dir = tmp_path / "jdk-21.0.2+13"
        bin_dir = jdk_dir / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "java").touch()

        result = _find_java_home(str(tmp_path), "linux")
        assert result == str(jdk_dir)

    def test_finds_macos_java_home(self, tmp_path):
        """Should find JAVA_HOME on macOS directory structure."""
        jdk_dir = tmp_path / "jdk-21.0.2+13"
        home_bin = jdk_dir / "Contents" / "Home" / "bin"
        home_bin.mkdir(parents=True)
        (home_bin / "java").touch()

        result = _find_java_home(str(tmp_path), "darwin")
        assert result == str(jdk_dir / "Contents" / "Home")

    def test_finds_windows_java_home(self, tmp_path):
        """Should find JAVA_HOME on Windows directory structure."""
        jdk_dir = tmp_path / "jdk-21.0.2+13"
        bin_dir = jdk_dir / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "java.exe").touch()

        result = _find_java_home(str(tmp_path), "windows")
        assert result == str(jdk_dir)

    def test_returns_none_when_no_java(self, tmp_path):
        """Should return None when no JDK is found."""
        (tmp_path / "some_other_dir").mkdir()
        result = _find_java_home(str(tmp_path), "linux")
        assert result is None

    def test_returns_none_when_dir_missing(self):
        """Should return None when the directory doesn't exist."""
        result = _find_java_home("/nonexistent/path", "linux")
        assert result is None
