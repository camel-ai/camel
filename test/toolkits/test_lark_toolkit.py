# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
import os
from unittest.mock import patch

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
    assert len(tools) == 4
    assert all(isinstance(tool, FunctionTool) for tool in tools)
    assert [tool.func.__name__ for tool in tools] == [
        "lark_list_chats",
        "lark_get_chat_messages",
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

        assert result["code"] == 0
        assert len(result["data"]["items"]) == 1
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

        assert result["code"] == 0
        assert len(result["data"]["items"]) == 1
        assert result["data"]["has_more"] is False


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

        assert len(result["data"]["items"]) == 1
        assert result["data"]["has_more"] is True

        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["container_id_type"] == "chat"
        assert params["start_time"] == "1609459200"
        assert params["end_time"] == "1609545600"
        assert params["sort_type"] == "ByCreateTimeAsc"


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
        assert (tmp_path / "lark_file" / "file_abc").exists()


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
                "body": {"content": ("{\"image_key\":\"img_v3_02tb_abc\"}")}
            },
        }

        result = lark_toolkit.lark_get_message_resource_key(
            message_id="om_123"
        )

        assert result["key"] == "img_v3_02tb_abc"
