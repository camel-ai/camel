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
from unittest.mock import patch

import pytest

from camel.toolkits.terminal_toolkit.runtime_utils import (
    get_platform_info,
)


@patch("camel.toolkits.terminal_toolkit.runtime_utils.platform")
def test_linux_amd64(mock_platform):
    mock_platform.system.return_value = "Linux"
    mock_platform.machine.return_value = "x86_64"
    os_name, arch = get_platform_info()
    assert os_name == "linux"
    assert arch == "amd64"


@patch("camel.toolkits.terminal_toolkit.runtime_utils.platform")
def test_darwin_arm64(mock_platform):
    mock_platform.system.return_value = "Darwin"
    mock_platform.machine.return_value = "arm64"
    os_name, arch = get_platform_info()
    assert os_name == "darwin"
    assert arch == "arm64"


@patch("camel.toolkits.terminal_toolkit.runtime_utils.platform")
def test_windows_amd64(mock_platform):
    mock_platform.system.return_value = "Windows"
    mock_platform.machine.return_value = "AMD64"
    os_name, arch = get_platform_info()
    assert os_name == "windows"
    assert arch == "amd64"


@patch("camel.toolkits.terminal_toolkit.runtime_utils.platform")
def test_unsupported_os(mock_platform):
    mock_platform.system.return_value = "FreeBSD"
    mock_platform.machine.return_value = "x86_64"
    with pytest.raises(
        RuntimeError, match="Unsupported operating system"
    ):
        get_platform_info()


@patch("camel.toolkits.terminal_toolkit.runtime_utils.platform")
def test_unsupported_arch(mock_platform):
    mock_platform.system.return_value = "Linux"
    mock_platform.machine.return_value = "mips"
    with pytest.raises(
        RuntimeError, match="Unsupported architecture"
    ):
        get_platform_info()
