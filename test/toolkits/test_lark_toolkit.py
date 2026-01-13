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
import json
import os
from unittest.mock import Mock, patch

import pytest

from camel.toolkits import FunctionTool


@pytest.fixture
def mock_env_vars():
    """Set up mock environment variables for testing."""
    with patch.dict(
        os.environ,
        {
            "LARK_APP_ID": "test_app_id",
            "LARK_APP_SECRET": "test_app_secret",
        },
    ):
        yield


@pytest.fixture
def lark_toolkit(mock_env_vars):
    """Create a LarkToolkit instance for testing."""
    from camel.toolkits import LarkToolkit

    return LarkToolkit()


def _mock_tenant_token(mock_post):
    mock_post.return_value.json.return_value = {
        "code": 0,
        "tenant_access_token": "token",
        "expire": 7200,
    }


# ============================================================================
# Initialization Tests
# ============================================================================


def test_lark_toolkit_init(mock_env_vars):
    """Test LarkToolkit initialization."""
    from camel.toolkits import LarkToolkit

    toolkit = LarkToolkit()
    assert toolkit._app_id == "test_app_id"
    assert toolkit._app_secret == "test_app_secret"
    assert toolkit._domain == "https://open.larksuite.com"


def test_lark_toolkit_init_with_feishu(mock_env_vars):
    """Test LarkToolkit initialization with Feishu (China) domain."""
    from camel.toolkits import LarkToolkit

    toolkit = LarkToolkit(use_feishu=True)
    assert toolkit._domain == "https://open.feishu.cn"


def test_lark_toolkit_get_tools(lark_toolkit):
    """Test only the expected tools are exposed."""
    tools = lark_toolkit.get_tools()
    assert len(tools) == 5
    assert all(isinstance(tool, FunctionTool) for tool in tools)
    assert [tool.func.__name__ for tool in tools] == [
        "lark_list_chats",
        "lark_get_chat_messages",
        "lark_send_message",
        "lark_get_message_resource",
        "lark_get_message_resource_key",
    ]


# ============================================================================
# Chat Operation Tests
# ============================================================================


def test_lark_list_chats(lark_toolkit):
    """Test listing chats."""
    with (
        patch("requests.post") as mock_post,
        patch("requests.get") as mock_get,
    ):
        _mock_tenant_token(mock_post)
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "items": [{"chat_id": "oc_1", "name": "Team"}],
                "has_more": False,
            },
        }

        result = lark_toolkit.lark_list_chats()

        assert len(result["chats"]) == 1
        assert result["chats"][0]["chat_id"] == "oc_1"
        assert result["chats"][0]["name"] == "Team"
        mock_get.assert_called_once()


def test_lark_get_chat_messages(lark_toolkit):
    """Test getting chat messages."""
    with (
        patch("requests.post") as mock_post,
        patch("requests.get") as mock_get,
    ):
        _mock_tenant_token(mock_post)
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "items": [{"message_id": "msg_1", "msg_type": "text"}],
                "has_more": False,
            },
        }

        result = lark_toolkit.lark_get_chat_messages(container_id="oc_123")

        assert len(result["messages"]) == 1
        assert result["messages"][0]["message_id"] == "msg_1"
        assert result["has_more"] is False


def test_lark_get_chat_messages_time_filters(lark_toolkit):
    """Test getting chat messages with time filtering options."""
    with (
        patch("requests.post") as mock_post,
        patch("requests.get") as mock_get,
    ):
        _mock_tenant_token(mock_post)
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "items": [{"message_id": "msg_1", "msg_type": "text"}],
                "has_more": True,
                "page_token": "next_page",
            },
        }

        result = lark_toolkit.lark_get_chat_messages(
            container_id="oc_123",
            container_id_type="chat",
            start_time="1609459200",
            end_time="1609545600",
            sort_type="ByCreateTimeAsc",
        )

        assert len(result["messages"]) == 1
        assert result["has_more"] is True

        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["container_id_type"] == "chat"
        assert params["start_time"] == "1609459200"
        assert params["end_time"] == "1609545600"
        assert params["sort_type"] == "ByCreateTimeAsc"


def test_lark_send_message(lark_toolkit):
    """Test sending a text message."""
    with patch("requests.post") as mock_post:
        tenant_response = Mock()
        tenant_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "token",
            "expire": 7200,
        }
        send_response = Mock()
        send_response.json.return_value = {
            "code": 0,
            "data": {
                "message_id": "om_123",
                "chat_id": "oc_456",
                "msg_type": "text",
            },
        }
        mock_post.side_effect = [tenant_response, send_response]

        result = lark_toolkit.lark_send_message(
            receive_id="oc_456",
            text="test content",
            receive_id_type="chat_id",
        )

        assert result["message_id"] == "om_123"
        assert result["chat_id"] == "oc_456"
        assert result["msg_type"] == "text"

        call_args = mock_post.call_args_list[1]
        params = call_args[1]["params"]
        payload = call_args[1]["json"]
        assert params["receive_id_type"] == "chat_id"
        assert payload["receive_id"] == "oc_456"
        assert payload["msg_type"] == "text"
        assert payload["content"] == json.dumps({"text": "test content"})


def test_lark_get_message_resource(tmp_path, mock_env_vars):
    """Test downloading a message resource."""
    from camel.toolkits import LarkToolkit

    with patch.dict(os.environ, {"CAMEL_WORKDIR": str(tmp_path)}):
        lark_toolkit = LarkToolkit()

    with (
        patch("requests.post") as mock_post,
        patch("requests.get") as mock_get,
    ):
        _mock_tenant_token(mock_post)
        mock_get.return_value.status_code = 200
        mock_get.return_value.headers = {"Content-Type": "image/png"}
        mock_get.return_value.content = b"binary-content"

        result = lark_toolkit.lark_get_message_resource(
            message_id="om_123",
            file_key="file_abc",
            resource_type="image",
        )

        assert result["content_type"] == "image/png"
        assert result["path"]
        assert result["size"] == len(b"binary-content")
        assert (tmp_path / "lark_file" / "file_abc.png").exists()


def test_lark_get_message_resource_key(lark_toolkit):
    """Test getting resource key from message content."""
    with (
        patch("requests.post") as mock_post,
        patch("requests.get") as mock_get,
    ):
        _mock_tenant_token(mock_post)
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {"body": {"content": '{"image_key":"img_v3_02tb_abc"}'}}
                ]
            },
        }

        result = lark_toolkit.lark_get_message_resource_key(
            message_id="om_123"
        )

        assert result["key"] == "img_v3_02tb_abc"
