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
import sys
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits.aci_toolkit import ACIToolkit

# Add aci to sys.modules to allow patching
sys.modules['aci'] = MagicMock()
sys.modules['aci.types'] = MagicMock()
sys.modules['aci.types.enums'] = MagicMock()


@pytest.mark.skipif(
    os.getenv("ACI_API_KEY") is None, reason="ACI_API_KEY not set"
)
def test_aci_toolkit_init():
    r"""Test ACIToolkit initialization."""
    # Test initialization with default parameters
    toolkit = ACIToolkit()
    assert toolkit._api_key == os.getenv("ACI_API_KEY")
    assert toolkit._base_url == os.getenv("ACI_BASE_URL")
    assert toolkit.linked_account_owner_id is None

    # Test initialization with custom parameters
    custom_api_key = "test_api_key"
    custom_base_url = "https://test.api.url"
    custom_owner_id = "test_owner"
    toolkit = ACIToolkit(
        api_key=custom_api_key,
        base_url=custom_base_url,
        linked_account_owner_id=custom_owner_id,
    )
    assert toolkit._api_key == custom_api_key
    assert toolkit._base_url == custom_base_url
    assert toolkit.linked_account_owner_id == custom_owner_id


@patch("aci.ACI")
def test_search_tool(mock_aci):
    r"""Test search_tool method."""
    # Setup mock
    mock_client = MagicMock()
    mock_aci.return_value = mock_client
    mock_client.apps.search.return_value = ["app1", "app2"]

    # Initialize toolkit and call method
    toolkit = ACIToolkit(api_key="test_key")
    result = toolkit.search_tool(
        intent="test intent",
        allowed_app_only=True,
        include_functions=True,
        categories=["category1"],
        limit=5,
        offset=0,
    )

    # Verify results
    assert result == ["app1", "app2"]
    mock_client.apps.search.assert_called_once_with(
        intent="test intent",
        allowed_apps_only=True,
        include_functions=True,
        categories=["category1"],
        limit=5,
        offset=0,
    )


@patch("aci.ACI")
def test_search_tool_exception(mock_aci):
    r"""Test search_tool method with exception."""
    # Setup mock to raise exception
    mock_client = MagicMock()
    mock_aci.return_value = mock_client
    mock_client.apps.search.side_effect = Exception("Test error")

    # Initialize toolkit and call method
    toolkit = ACIToolkit(api_key="test_key")
    result = toolkit.search_tool()

    # Verify results
    assert result == "Test error"
    mock_client.apps.search.assert_called_once()


@patch("aci.ACI")
def test_list_configured_apps(mock_aci):
    r"""Test list_configured_apps method."""
    # Setup mock
    mock_client = MagicMock()
    mock_aci.return_value = mock_client
    mock_client.app_configurations.list.return_value = ["config1", "config2"]

    # Initialize toolkit and call method
    toolkit = ACIToolkit(api_key="test_key")
    result = toolkit.list_configured_apps(
        app_names=["app1"], limit=5, offset=0
    )

    # Verify results
    assert result == ["config1", "config2"]
    mock_client.app_configurations.list.assert_called_once_with(
        app_names=["app1"], limit=5, offset=0
    )


@patch("aci.types.enums.SecurityScheme")
@patch("aci.ACI")
def test_configure_app(mock_aci, mock_security_scheme):
    r"""Test configure_app method."""
    # Setup mock
    mock_client = MagicMock()
    mock_aci.return_value = mock_client

    # Mock app details with API key security scheme
    mock_app_details = MagicMock()
    mock_app_details.security_schemes = ["api_key"]
    mock_client.apps.get.return_value = mock_app_details

    # Mock SecurityScheme enum
    mock_security_scheme.API_KEY = "api_key"

    mock_client.app_configurations.create.return_value = {"status": "success"}

    # Initialize toolkit and call method
    toolkit = ACIToolkit(api_key="test_key")
    result = toolkit.configure_app(app_name="test_app")

    # Verify results
    assert result == {"status": "success"}
    mock_client.apps.get.assert_called_once_with(app_name="test_app")
    mock_client.app_configurations.create.assert_called_once()


@patch("aci.ACI")
def test_enable_linked_account(mock_aci):
    r"""Test enable_linked_account method."""
    # Setup mock
    mock_client = MagicMock()
    mock_aci.return_value = mock_client

    mock_linked_account = MagicMock()
    mock_linked_account.id = "test_id"
    mock_linked_account.enabled = True

    mock_client.linked_accounts.enable.return_value = mock_linked_account

    # Initialize toolkit and call method
    toolkit = ACIToolkit(api_key="test_key")
    result = toolkit.enable_linked_account(linked_account_id="test_id")

    # Verify results
    assert result == mock_linked_account
    assert result.enabled is True
    mock_client.linked_accounts.enable.assert_called_once_with(
        linked_account_id="test_id"
    )


@patch("aci.ACI")
def test_disable_linked_account(mock_aci):
    r"""Test disable_linked_account method."""
    # Setup mock
    mock_client = MagicMock()
    mock_aci.return_value = mock_client

    mock_linked_account = MagicMock()
    mock_linked_account.id = "test_id"
    mock_linked_account.enabled = False

    mock_client.linked_accounts.disable.return_value = mock_linked_account

    # Initialize toolkit and call method
    toolkit = ACIToolkit(api_key="test_key")
    result = toolkit.disable_linked_account(linked_account_id="test_id")

    # Verify results
    assert result == mock_linked_account
    assert result.enabled is False
    mock_client.linked_accounts.disable.assert_called_once_with(
        linked_account_id="test_id"
    )


@patch("aci.ACI")
def test_delete_linked_account(mock_aci):
    r"""Test delete_linked_account method."""
    # Setup mock
    mock_client = MagicMock()
    mock_aci.return_value = mock_client

    # Initialize toolkit and call method
    toolkit = ACIToolkit(api_key="test_key")
    result = toolkit.delete_linked_account(linked_account_id="test_id")

    # Verify results
    assert "test_id" in result
    assert "deleted successfully" in result
    mock_client.linked_accounts.delete.assert_called_once_with(
        linked_account_id="test_id"
    )


@patch("aci.ACI")
def test_get_tools(mock_aci):
    r"""Test get_tools method."""
    # Setup mock
    mock_client = MagicMock()
    mock_aci.return_value = mock_client

    # Mock configured apps
    mock_app = MagicMock()
    mock_app.app_name = "test_app"
    mock_client.app_configurations.list.return_value = [mock_app]

    # Mock function search
    mock_client.functions.search.return_value = [
        {"function": {"name": "test_function"}}
    ]

    # Mock function definition
    mock_client.functions.get_definition.return_value = {
        "type": "function",
        "function": {
            "name": "test_function",
            "description": "Test function",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }

    # Initialize toolkit and call method
    toolkit = ACIToolkit(api_key="test_key")
    result = toolkit.get_tools()

    # Verify results
    assert len(result) == 16
    mock_client.app_configurations.list.assert_called_once()
    mock_client.functions.search.assert_called_once()
    mock_client.functions.get_definition.assert_called_once_with(
        "test_function"
    )


@patch("aci.ACI")
def test_execute_function(mock_aci):
    r"""Test execute_function method."""
    # Setup mock
    mock_client = MagicMock()
    mock_aci.return_value = mock_client
    mock_client.handle_function_call.return_value = {"result": "success"}

    # Initialize toolkit and call method
    toolkit = ACIToolkit(api_key="test_key")
    result = toolkit.execute_function(
        function_name="test_function",
        function_arguments={"arg1": "value1"},
        linked_account_owner_id="test_owner",
        allowed_apps_only=True,
    )

    # Verify results
    assert result == {"result": "success"}
    mock_client.handle_function_call.assert_called_once_with(
        "test_function", {"arg1": "value1"}, "test_owner", True
    )


@patch("aci.ACI")
@pytest.mark.asyncio
async def test_aexecute_function(mock_aci):
    r"""Test aexecute_function async method."""
    # Setup mock
    mock_client = MagicMock()
    mock_aci.return_value = mock_client
    mock_client.handle_function_call.return_value = {"result": "async_success"}

    # Initialize toolkit and call async method
    toolkit = ACIToolkit(api_key="test_key")
    result = await toolkit.aexecute_function(
        function_name="test_async_function",
        function_arguments={"arg1": "async_value1"},
        linked_account_owner_id="test_async_owner",
        allowed_apps_only=False,
    )

    # Verify results
    assert result == {"result": "async_success"}
    mock_client.handle_function_call.assert_called_once_with(
        "test_async_function",
        {"arg1": "async_value1"},
        "test_async_owner",
        False,
    )
