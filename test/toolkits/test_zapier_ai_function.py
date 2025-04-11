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
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import ZapierToolkit
from camel.toolkits.function_tool import FunctionTool


@pytest.fixture
def zapier_toolkit():
    # Set environment variables for testing
    os.environ['ZAPIER_NLA_API_KEY'] = 'test_api_key'
    return ZapierToolkit()


def test_init_missing_credentials():
    # Test initialization with missing credentials
    os.environ.pop('ZAPIER_NLA_API_KEY', None)

    with pytest.raises(ValueError):
        ZapierToolkit()


@patch('requests.get')
def test_list_actions_success(mock_get, zapier_toolkit):
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "id": "action1",
                "description": "Test action 1",
                "params": {"param1": "value1"},
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = zapier_toolkit.list_actions()

    assert result == mock_response.json.return_value
    mock_get.assert_called_once_with(
        f"{zapier_toolkit.base_url}exposed/",
        params={'api_key': 'test_api_key'},
        headers={'accept': 'application/json', 'x-api-key': 'test_api_key'},
    )


@patch('requests.post')
def test_execute_action_success(mock_post, zapier_toolkit):
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": "Action executed successfully"
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    action_id = "test_action"
    instructions = "Send an email"
    result = zapier_toolkit.execute_action(action_id, instructions)

    assert result == mock_response.json.return_value
    mock_post.assert_called_once_with(
        f"{zapier_toolkit.base_url}exposed/{action_id}/execute/",
        params={'api_key': 'test_api_key'},
        headers={
            'accept': 'application/json',
            'x-api-key': 'test_api_key',
            'Content-Type': 'application/json',
        },
        json={'instructions': instructions, 'preview_only': False},
    )


def test_get_tools(zapier_toolkit):
    # Test get_tools method returns list of FunctionTool objects
    tools = zapier_toolkit.get_tools()
    assert isinstance(tools, list)
    assert len(tools) > 0
    for tool in tools:
        assert isinstance(tool, FunctionTool)
