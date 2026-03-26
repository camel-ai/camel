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

from camel.toolkits import TerminalToolkit
from camel.toolkits.terminal_toolkit.runtime_utils import Runtime


@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_java_available"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_go_available"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit"
    ".check_nodejs_availability"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit"
    ".setup_initial_env_with_uv"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_uv_available"
)
def test_default_skips_go_java(
    mock_uv,
    mock_setup,
    mock_node,
    mock_go,
    mock_java,
    tmp_path,
):
    """Default enable_other_runtimes=None should NOT call Go/Java."""
    mock_uv.return_value = (True, "/usr/bin/uv")
    mock_setup.return_value = True

    toolkit = TerminalToolkit(
        working_directory=str(tmp_path),
    )
    try:
        mock_go.assert_not_called()
        mock_java.assert_not_called()
    finally:
        toolkit.cleanup()


@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_java_available"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_go_available"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit"
    ".check_nodejs_availability"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit"
    ".setup_initial_env_with_uv"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_uv_available"
)
def test_go_enabled_calls_go_only(
    mock_uv,
    mock_setup,
    mock_node,
    mock_go,
    mock_java,
    tmp_path,
):
    """enable_other_runtimes=[Runtime.GO] should call Go but not Java."""
    mock_uv.return_value = (True, "/usr/bin/uv")
    mock_setup.return_value = True
    mock_go.return_value = "/usr/local/go/bin"

    toolkit = TerminalToolkit(
        working_directory=str(tmp_path),
        enable_other_runtimes=[Runtime.GO],
    )
    try:
        mock_go.assert_called_once()
        mock_java.assert_not_called()
    finally:
        toolkit.cleanup()


@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_java_available"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_go_available"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit"
    ".check_nodejs_availability"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit"
    ".setup_initial_env_with_uv"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_uv_available"
)
def test_both_enabled_calls_both(
    mock_uv,
    mock_setup,
    mock_node,
    mock_go,
    mock_java,
    tmp_path,
):
    """enable_other_runtimes=[Runtime.GO, Runtime.JAVA] should call both."""
    mock_uv.return_value = (True, "/usr/bin/uv")
    mock_setup.return_value = True
    mock_go.return_value = "/usr/local/go/bin"
    mock_java.return_value = "/usr/lib/jvm/jdk-21"

    toolkit = TerminalToolkit(
        working_directory=str(tmp_path),
        enable_other_runtimes=[Runtime.GO, Runtime.JAVA],
    )
    try:
        mock_go.assert_called_once()
        mock_java.assert_called_once()
    finally:
        toolkit.cleanup()


@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_java_available"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_go_available"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit"
    ".clone_current_environment"
)
def test_cloned_env_also_sets_up_runtimes(
    mock_clone,
    mock_go,
    mock_java,
    tmp_path,
):
    """clone_current_env=True with enable_other_runtimes should call Go."""
    mock_clone.return_value = True
    mock_go.return_value = "/usr/local/go/bin"

    toolkit = TerminalToolkit(
        working_directory=str(tmp_path),
        clone_current_env=True,
        enable_other_runtimes=[Runtime.GO],
    )
    try:
        mock_go.assert_called_once()
        mock_java.assert_not_called()
    finally:
        toolkit.cleanup()


@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_java_available"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_go_available"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit"
    ".check_nodejs_availability"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit"
    ".setup_initial_env_with_uv"
)
@patch(
    "camel.toolkits.terminal_toolkit.terminal_toolkit" ".ensure_uv_available"
)
def test_runtime_env_vars_not_in_os_environ(
    mock_uv,
    mock_setup,
    mock_node,
    mock_go,
    mock_java,
    tmp_path,
):
    """Runtime paths should be on the instance, not in os.environ."""
    import os

    mock_uv.return_value = (True, "/usr/bin/uv")
    mock_setup.return_value = True
    mock_go.return_value = "/custom/go/bin"

    original_path = os.environ.get("PATH", "")

    toolkit = TerminalToolkit(
        working_directory=str(tmp_path),
        enable_other_runtimes=[Runtime.GO],
    )
    try:
        # Process-level PATH should remain unchanged
        assert os.environ.get("PATH", "") == original_path
        # Instance should have Go path stored
        assert "/custom/go/bin" in toolkit._runtime_env_vars.get("PATH", "")
    finally:
        toolkit.cleanup()
