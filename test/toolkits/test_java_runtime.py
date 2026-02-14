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
from unittest.mock import MagicMock, patch

from camel.toolkits.terminal_toolkit.java_runtime import (
    _find_java_home,
    ensure_java_available,
)


@patch(
    "camel.toolkits.terminal_toolkit.java_runtime"
    ".subprocess.run"
)
@patch(
    "camel.toolkits.terminal_toolkit.java_runtime"
    ".shutil.which"
)
def test_java_already_installed(mock_which, mock_run):
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


def test_finds_linux_java_home(tmp_path):
    """Should find JAVA_HOME on Linux directory structure."""
    jdk_dir = tmp_path / "jdk-21.0.2+13"
    bin_dir = jdk_dir / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "java").touch()

    result = _find_java_home(str(tmp_path), "linux")
    assert result == str(jdk_dir)


def test_finds_macos_java_home(tmp_path):
    """Should find JAVA_HOME on macOS directory structure."""
    jdk_dir = tmp_path / "jdk-21.0.2+13"
    home_bin = jdk_dir / "Contents" / "Home" / "bin"
    home_bin.mkdir(parents=True)
    (home_bin / "java").touch()

    result = _find_java_home(str(tmp_path), "darwin")
    assert result == str(jdk_dir / "Contents" / "Home")


def test_finds_windows_java_home(tmp_path):
    """Should find JAVA_HOME on Windows directory structure."""
    jdk_dir = tmp_path / "jdk-21.0.2+13"
    bin_dir = jdk_dir / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "java.exe").touch()

    result = _find_java_home(str(tmp_path), "windows")
    assert result == str(jdk_dir)


def test_returns_none_when_no_java(tmp_path):
    """Should return None when no JDK is found."""
    (tmp_path / "some_other_dir").mkdir()
    result = _find_java_home(str(tmp_path), "linux")
    assert result is None


def test_returns_none_when_dir_missing():
    """Should return None when the directory doesn't exist."""
    result = _find_java_home("/nonexistent/path", "linux")
    assert result is None
