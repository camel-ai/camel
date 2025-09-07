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

import os
import unittest
from unittest.mock import MagicMock, patch

from camel.runtimes import DaytonaRuntime
from camel.toolkits.function_tool import FunctionTool


def sample_function(x: int, y: int) -> int:
    r"""Sample function for testing."""
    return x + y


@patch('daytona_sdk.Daytona')
@patch('daytona_sdk.DaytonaConfig')
def test_init_with_explicit_params(mock_config, mock_daytona):
    r"""Test initialization with explicit parameters."""
    runtime = DaytonaRuntime(
        api_key="test_key", api_url="http://test-url", language="python"
    )

    # Assert parameters are set correctly
    assert runtime.api_key == "test_key"
    assert runtime.api_url == "http://test-url"
    assert runtime.language == "python"

    # Assert config was created with correct parameters
    mock_config.assert_called_once_with(
        api_key="test_key", api_url="http://test-url"
    )

    # Assert Daytona client was initialized
    mock_daytona.assert_called_once()


@patch.dict(
    os.environ,
    {'DAYTONA_API_KEY': 'env_key', 'DAYTONA_API_URL': 'http://env-url'},
)
@patch('daytona_sdk.Daytona')
@patch('daytona_sdk.DaytonaConfig')
def test_init_with_env_vars(mock_config, mock_daytona):
    r"""Test initialization with environment variables."""
    runtime = DaytonaRuntime()

    # Assert parameters are set from environment
    assert runtime.api_key == "env_key"
    assert runtime.api_url == "http://env-url"
    assert runtime.language == "python"  # Default value

    # Assert config was created with correct parameters
    mock_config.assert_called_once_with(
        api_key="env_key", api_url="http://env-url"
    )


@patch('daytona_sdk.CreateSandboxBaseParams')
@patch('daytona_sdk.Daytona')
@patch('daytona_sdk.DaytonaConfig')
def test_build_success(mock_config, mock_daytona, mock_params):
    r"""Test successful sandbox creation."""
    # Setup mock
    mock_sandbox = MagicMock()
    mock_sandbox.id = "test-sandbox-id"
    mock_daytona_instance = mock_daytona.return_value
    mock_daytona_instance.create.return_value = mock_sandbox

    # Create runtime and build sandbox
    runtime = DaytonaRuntime(api_key="test_key")
    result = runtime.build()

    # Assert sandbox was created
    mock_daytona_instance.create.assert_called_once()
    assert runtime.sandbox == mock_sandbox
    assert result == runtime  # Should return self


@patch('daytona_sdk.CreateSandboxBaseParams')
@patch('daytona_sdk.Daytona')
@patch('daytona_sdk.DaytonaConfig')
def test_build_failure(mock_config, mock_daytona, mock_params):
    r"""Test sandbox creation failure."""
    # Setup mock to raise exception
    mock_daytona_instance = mock_daytona.return_value
    mock_daytona_instance.create.side_effect = Exception("Test error")

    # Create runtime
    runtime = DaytonaRuntime(api_key="test_key")

    # Assert exception is raised
    with unittest.TestCase().assertRaises(RuntimeError) as context:
        runtime.build()

    assert "Daytona sandbox creation failed" in str(context.exception)


@patch('daytona_sdk.Daytona')
@patch('daytona_sdk.DaytonaConfig')
def test_stop(mock_config, mock_daytona):
    r"""Test stopping and removing the sandbox."""
    # Setup mock
    mock_sandbox = MagicMock()
    mock_daytona_instance = mock_daytona.return_value

    # Create runtime with sandbox
    runtime = DaytonaRuntime(api_key="test_key")
    runtime.sandbox = mock_sandbox

    # Stop sandbox
    result = runtime.stop()

    # Assert sandbox was deleted
    mock_daytona_instance.delete.assert_called_once_with(mock_sandbox)
    assert runtime.sandbox is None
    assert result == runtime  # Should return self


@patch('daytona_sdk.Daytona')
@patch('daytona_sdk.DaytonaConfig')
def test_add_function(mock_config, mock_daytona):
    r"""Test adding a function to the runtime."""
    # Setup mock
    mock_sandbox = MagicMock()
    mock_daytona_instance = mock_daytona.return_value
    mock_daytona_instance.create.return_value = mock_sandbox

    # Create runtime and build sandbox
    runtime = DaytonaRuntime(api_key="test_key")
    runtime.build()

    # Add function
    tool = FunctionTool(sample_function)
    result = runtime.add(funcs=tool, entrypoint="test_entry")

    # Assert function was added
    assert "sample_function" in runtime.tools_map
    assert runtime.entrypoint["sample_function"] == "test_entry"
    assert result == runtime  # Should return self


@patch('daytona_sdk.Daytona')
@patch('daytona_sdk.DaytonaConfig')
def test_reset(mock_config, mock_daytona):
    r"""Test resetting the sandbox."""
    # Setup mock
    mock_sandbox = MagicMock()
    mock_daytona_instance = mock_daytona.return_value
    mock_daytona_instance.create.return_value = mock_sandbox

    # Create runtime with sandbox
    runtime = DaytonaRuntime(api_key="test_key")
    runtime.sandbox = mock_sandbox

    # Mock the build method to verify it's called
    original_build = runtime.build
    runtime.build = MagicMock(return_value=runtime)

    # Reset sandbox
    result = runtime.reset()

    # Assert sandbox was deleted and rebuilt
    mock_daytona_instance.delete.assert_called_once_with(mock_sandbox)
    assert runtime.build.called
    assert result == runtime  # Should return self

    # Restore original build method
    runtime.build = original_build
