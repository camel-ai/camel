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
from unittest.mock import MagicMock, patch

import pytest
import requests

from camel.toolkits import FunctionTool, KlavisToolkit


# Fixture for mocking environment variables
@pytest.fixture
def mock_env_api_key(monkeypatch):
    monkeypatch.setenv("KLAVIS_API_KEY", "test_api_key")


# Fixture for KlavisToolkit instance
@pytest.fixture
def klavis_toolkit(mock_env_api_key):
    # Patch requests dependency during initialization
    with patch('requests.request'):
        toolkit = KlavisToolkit(timeout=10.0)
    return toolkit


# Fixture for mocking requests.request
@pytest.fixture
def mock_requests():
    with patch('requests.request') as mock_req:
        yield mock_req


# --------------------------
# Test __init__ method
# --------------------------
def test_init(klavis_toolkit):
    assert klavis_toolkit.api_key == "test_api_key"
    assert klavis_toolkit.base_url == "https://api.klavis.ai"
    assert klavis_toolkit.timeout == 10.0


# --------------------------
# Test _request method
# --------------------------
def test_request_success(klavis_toolkit, mock_requests):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"status": "success"}
    mock_requests.return_value = mock_response

    result = klavis_toolkit._request('GET', '/test-endpoint')

    mock_requests.assert_called_once_with(
        'GET',
        'https://api.klavis.ai/test-endpoint',
        headers={
            'accept': 'application/json',
            'Authorization': 'Bearer test_api_key',
        },
        json=None,
        timeout=10.0,
    )
    assert result == {"status": "success"}


def test_request_with_payload_and_headers(klavis_toolkit, mock_requests):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"status": "posted"}
    mock_requests.return_value = mock_response

    payload = {"key": "value"}
    headers = {"X-Custom": "Header"}
    result = klavis_toolkit._request(
        'POST', '/post-endpoint', payload=payload, additional_headers=headers
    )

    expected_headers = {
        'accept': 'application/json',
        'Authorization': 'Bearer test_api_key',
        'X-Custom': 'Header',
    }
    mock_requests.assert_called_once_with(
        'POST',
        'https://api.klavis.ai/post-endpoint',
        headers=expected_headers,
        json=payload,
        timeout=10.0,
    )
    assert result == {"status": "posted"}


def test_request_http_error(klavis_toolkit, mock_requests):
    mock_response = MagicMock()
    http_error = requests.exceptions.HTTPError("404 Client Error: Not Found")
    mock_response.raise_for_status.side_effect = http_error
    mock_requests.return_value = mock_response

    result = klavis_toolkit._request('GET', '/not-found')

    assert "error" in result
    assert "Request failed: 404 Client Error: Not Found" in result["error"]


def test_request_connection_error(klavis_toolkit, mock_requests):
    connection_error = requests.exceptions.ConnectionError(
        "Connection timed out"
    )
    mock_requests.side_effect = connection_error

    result = klavis_toolkit._request('GET', '/timeout-endpoint')

    assert "error" in result
    assert "Request failed: Connection timed out" in result["error"]


def test_request_non_json_response(klavis_toolkit, mock_requests):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = ValueError(
        "No JSON object could be decoded"
    )
    mock_requests.return_value = mock_response

    result = klavis_toolkit._request('GET', '/bad-json')

    assert result == {"error": "Response is not valid JSON"}


# --------------------------
# Test public methods calling _request
# --------------------------
@patch.object(KlavisToolkit, '_request')
def test_create_server_instance(mock_request, klavis_toolkit):
    mock_request.return_value = {"instanceId": "inst-123"}
    result = klavis_toolkit.create_server_instance(
        "test-server", "user-abc", "platform-xyz"
    )
    expected_payload = {
        "serverName": "test-server",
        "userId": "user-abc",
        "platformName": "platform-xyz",
    }
    expected_headers = {'Content-Type': 'application/json'}
    mock_request.assert_called_once_with(
        'POST',
        '/mcp-server/instance/create',
        payload=expected_payload,
        additional_headers=expected_headers,
    )
    assert result == {"instanceId": "inst-123"}


@patch.object(KlavisToolkit, '_request')
def test_get_server_instance(mock_request, klavis_toolkit):
    mock_request.return_value = {"status": "active"}
    result = klavis_toolkit.get_server_instance("inst-123")
    mock_request.assert_called_once_with(
        'GET', '/mcp-server/instance/get/inst-123'
    )
    assert result == {"status": "active"}


@patch.object(KlavisToolkit, '_request')
def test_delete_auth_data(mock_request, klavis_toolkit):
    mock_request.return_value = {"status": "deleted"}
    result = klavis_toolkit.delete_auth_data("inst-123")
    mock_request.assert_called_once_with(
        'DELETE', '/mcp-server/instance/delete-auth/inst-123'
    )
    assert result == {"status": "deleted"}


@patch.object(KlavisToolkit, '_request')
def test_delete_server_instance(mock_request, klavis_toolkit):
    mock_request.return_value = {"status": "instance deleted"}
    result = klavis_toolkit.delete_server_instance("inst-123")
    mock_request.assert_called_once_with(
        'DELETE', '/mcp-server/instance/delete/inst-123'
    )
    assert result == {"status": "instance deleted"}


@patch.object(KlavisToolkit, '_request')
def test_get_all_servers(mock_request, klavis_toolkit):
    mock_request.return_value = {"servers": [{"name": "server1"}]}
    result = klavis_toolkit.get_all_servers()
    mock_request.assert_called_once_with('GET', '/mcp-server/servers')
    assert result == {"servers": [{"name": "server1"}]}


@patch.object(KlavisToolkit, '_request')
def test_set_auth_token(mock_request, klavis_toolkit):
    mock_request.return_value = {"status": "token set"}
    result = klavis_toolkit.set_auth_token("inst-123", "auth-token-xyz")
    expected_payload = {
        "instanceId": "inst-123",
        "authToken": "auth-token-xyz",
    }
    expected_headers = {'Content-Type': 'application/json'}
    mock_request.assert_called_once_with(
        'POST',
        '/mcp-server/instance/set-auth-token',
        payload=expected_payload,
        additional_headers=expected_headers,
    )
    assert result == {"status": "token set"}


@patch('urllib.parse.quote', return_value='encoded_url')
@patch.object(KlavisToolkit, '_request')
def test_list_tools(mock_request, mock_quote, klavis_toolkit):
    mock_request.return_value = {"tools": ["toolA", "toolB"]}
    result = klavis_toolkit.list_tools("http://example.com/sse")
    mock_quote.assert_called_once_with("http://example.com/sse", safe='')
    mock_request.assert_called_once_with(
        'GET', '/mcp-server/list-tools/encoded_url'
    )
    assert result == {"tools": ["toolA", "toolB"]}


@patch.object(KlavisToolkit, '_request')
def test_call_tool_with_args(mock_request, klavis_toolkit):
    mock_request.return_value = {"result": "success"}
    tool_args = {"param1": "value1"}
    result = klavis_toolkit.call_tool(
        "http://example.com/sse", "myTool", tool_args=tool_args
    )
    expected_payload = {
        "serverUrl": "http://example.com/sse",
        "toolName": "myTool",
        "toolArgs": tool_args,
    }
    expected_headers = {'Content-Type': 'application/json'}
    mock_request.assert_called_once_with(
        'POST',
        '/mcp-server/call-tool',
        payload=expected_payload,
        additional_headers=expected_headers,
    )
    assert result == {"result": "success"}


@patch.object(KlavisToolkit, '_request')
def test_call_tool_without_args(mock_request, klavis_toolkit):
    mock_request.return_value = {"result": "success_no_args"}
    result = klavis_toolkit.call_tool("http://example.com/sse", "myTool")
    expected_payload = {
        "serverUrl": "http://example.com/sse",
        "toolName": "myTool",
        "toolArgs": {},  # Ensure empty dict is sent when args are None
    }
    expected_headers = {'Content-Type': 'application/json'}
    mock_request.assert_called_once_with(
        'POST',
        '/mcp-server/call-tool',
        payload=expected_payload,
        additional_headers=expected_headers,
    )
    assert result == {"result": "success_no_args"}


# --------------------------
# Test get_tools method
# --------------------------
def test_get_tools(klavis_toolkit):
    tools = klavis_toolkit.get_tools()
    assert len(tools) == 8  # Updated count
    expected_func_names = [
        'create_server_instance',
        'get_server_instance',
        'delete_auth_data',
        'delete_server_instance',
        'get_all_servers',
        'set_auth_token',
        'list_tools',  # Added
        'call_tool',  # Added
    ]
    for i, tool in enumerate(tools):
        assert isinstance(tool, FunctionTool)
        # Check if the function name matches the expected name
        assert tool.func.__name__ == expected_func_names[i]
