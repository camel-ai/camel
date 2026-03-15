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

from camel.toolkits.terminal_toolkit.go_runtime import (
    ensure_go_available,
)


@patch("camel.toolkits.terminal_toolkit.go_runtime.subprocess.run")
@patch("camel.toolkits.terminal_toolkit.go_runtime.shutil.which")
def test_go_already_installed(mock_which, mock_run):
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
def test_go_unsupported_platform(mock_which, mock_platform):
    """Should return None for unsupported platforms."""
    mock_which.return_value = None
    mock_platform.side_effect = RuntimeError("Unsupported")

    callback = MagicMock()
    path = ensure_go_available(update_callback=callback)

    assert path is None
