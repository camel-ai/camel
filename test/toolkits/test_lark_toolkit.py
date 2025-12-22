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
import json
import os
from unittest.mock import MagicMock, patch

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
def mock_lark_client():
    """Create a mock Lark client and skip authentication."""
    with patch("lark_oapi.Client") as mock_client_class:
        mock_client = MagicMock()
        builder = mock_client_class.builder.return_value
        app_id = builder.app_id.return_value
        app_secret = app_id.app_secret.return_value
        domain = app_secret.domain.return_value
        domain.build.return_value = mock_client

        with patch(
            "camel.toolkits.lark_toolkit.LarkToolkit._authenticate"
        ) as mock_auth:
            mock_auth.return_value = None
            yield mock_client


@pytest.fixture
def lark_toolkit(mock_env_vars, mock_lark_client):
    """Create a LarkToolkit instance for testing."""
    from camel.toolkits import LarkToolkit

    toolkit = LarkToolkit()
    toolkit._user_access_token = "test_user_token"
    return toolkit


# ============================================================================
# Initialization Tests
# ============================================================================


def test_lark_toolkit_init(mock_env_vars, mock_lark_client):
    """Test LarkToolkit initialization."""
    from camel.toolkits import LarkToolkit

    toolkit = LarkToolkit()
    assert toolkit._app_id == "test_app_id"
    assert toolkit._app_secret == "test_app_secret"
    assert toolkit._domain == "https://open.larksuite.com"


def test_lark_toolkit_init_with_feishu(mock_env_vars, mock_lark_client):
    """Test LarkToolkit initialization with Feishu (China) domain."""
    from camel.toolkits import LarkToolkit

    toolkit = LarkToolkit(use_feishu=True)
    assert toolkit._domain == "https://open.feishu.cn"


# ============================================================================
# Document Operation Tests - with API call verification
# ============================================================================


def test_lark_create_document(lark_toolkit):
    """Test creating a Lark document with request verification."""
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "document": {
                    "document_id": "doc_123",
                    "title": "Test Document",
                    "revision_id": 1,
                }
            },
        }
        mock_post.return_value = mock_response

        result = lark_toolkit.lark_create_document(
            title="Test Document", folder_token="folder_abc"
        )

        # Verify result
        assert result["document_id"] == "doc_123"
        assert result["title"] == "Test Document"
        assert "url" in result

        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "docx/v1/documents" in call_args[0][0]
        assert "Authorization" in call_args[1]["headers"]
        assert call_args[1]["json"]["title"] == "Test Document"


def test_lark_create_document_failure(lark_toolkit):
    """Test handling of document creation failure."""
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 99991,
            "msg": "Permission denied",
        }
        mock_post.return_value = mock_response

        result = lark_toolkit.lark_create_document(title="Test Document")

        assert "error" in result
        assert "Permission denied" in result["error"]
        mock_post.assert_called_once()


def test_lark_get_document(lark_toolkit):
    """Test getting document metadata with request verification."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "document": {
                    "document_id": "doc_123",
                    "title": "Test Document",
                    "revision_id": 5,
                }
            },
        }
        mock_get.return_value = mock_response

        result = lark_toolkit.lark_get_document(document_id="doc_123")

        assert result["document_id"] == "doc_123"
        mock_get.assert_called_once()
        assert "docx/v1/documents/doc_123" in mock_get.call_args[0][0]


def test_lark_get_document_content(lark_toolkit):
    """Test getting document content."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"content": "This is the document content"},
        }
        mock_get.return_value = mock_response

        result = lark_toolkit.lark_get_document_content(document_id="doc_123")

        assert result["content"] == "This is the document content"
        mock_get.assert_called_once()


# ============================================================================
# Block Operation Tests
# ============================================================================


def test_lark_create_block(lark_toolkit):
    """Test creating a block with request verification."""
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "children": [{"block_id": "new_block_1"}],
                "document_revision_id": 10,
            },
        }
        mock_post.return_value = mock_response

        result = lark_toolkit.lark_create_block(
            document_id="doc_123",
            block_type="text",
            content="New paragraph text",
        )

        assert result["block_id"] == "new_block_1"
        mock_post.assert_called_once()
        assert "doc_123" in mock_post.call_args[0][0]


def test_lark_update_block(lark_toolkit):
    """Test updating a block with request verification."""
    with patch("requests.patch") as mock_patch:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {"document_revision_id": 12},
        }
        mock_patch.return_value = mock_response

        result = lark_toolkit.lark_update_block(
            document_id="doc_123",
            block_id="block_1",
            content="Updated content",
        )

        assert result["block_id"] == "block_1"
        assert "document_revision_id" in result
        mock_patch.assert_called_once()


def test_lark_delete_block(lark_toolkit):
    """Test deleting a block."""
    with (
        patch("requests.get") as mock_get,
        patch("requests.delete") as mock_delete,
    ):
        mock_get_block = MagicMock()
        mock_get_block.json.return_value = {
            "code": 0,
            "data": {
                "block": {
                    "block_id": "block_1",
                    "block_type": 2,
                    "parent_id": "doc_123",
                }
            },
        }
        mock_get_children = MagicMock()
        mock_get_children.json.return_value = {
            "code": 0,
            "data": {"items": [{"block_id": "block_1"}], "has_more": False},
        }
        mock_get.side_effect = [mock_get_block, mock_get_children]

        mock_delete.return_value.json.return_value = {
            "code": 0,
            "data": {"document_revision_id": 13},
        }

        result = lark_toolkit.lark_delete_block(
            document_id="doc_123", block_id="block_1"
        )

        assert result["block_id"] == "block_1"
        assert "document_revision_id" in result
        mock_delete.assert_called_once()


def test_lark_delete_block_with_parent(lark_toolkit):
    """Test deleting a block with parent_block_id provided."""
    with (
        patch("requests.get") as mock_get,
        patch("requests.delete") as mock_delete,
    ):
        # Only mock get_children since get_block is skipped
        mock_get_children = MagicMock()
        mock_get_children.json.return_value = {
            "code": 0,
            "data": {"items": [{"block_id": "block_1"}], "has_more": False},
        }
        mock_get.return_value = mock_get_children

        mock_delete.return_value.json.return_value = {
            "code": 0,
            "data": {"document_revision_id": 13},
        }

        result = lark_toolkit.lark_delete_block(
            document_id="doc_123",
            block_id="block_1",
            parent_block_id="parent_block",
        )

        assert result["block_id"] == "block_1"
        # Should only call get once (for children), not twice
        assert mock_get.call_count == 1
        mock_delete.assert_called_once()


# ============================================================================
# Tool Registration Tests
# ============================================================================


def test_get_tools(lark_toolkit):
    """Test getting all tools from the toolkit."""
    tools = lark_toolkit.get_tools()

    # Verify all tools are FunctionTool instances
    assert all(isinstance(tool, FunctionTool) for tool in tools)

    # Get tool names dynamically
    tool_names = [tool.func.__name__ for tool in tools]

    # Verify expected core tools are present (not hardcoded count)
    expected_tools = [
        # Drive operations
        "lark_get_root_folder_token",
        "lark_list_folder_contents",
        "lark_create_folder",
        # Document operations
        "lark_create_document",
        "lark_get_document",
        "lark_get_document_content",
        "lark_list_document_blocks",
        # Block operations
        "lark_get_block",
        "lark_get_block_children",
        "lark_create_block",
        "lark_update_block",
        "lark_delete_block",
        # Messaging operations
        "lark_send_message",
        "lark_list_chats",
        "lark_get_chat",
        "lark_get_chat_messages",
    ]

    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Missing tool: {expected_tool}"

    # Verify tool count matches expected (flexible check)
    assert len(tools) >= len(
        expected_tools
    ), f"Expected at least {len(expected_tools)} tools, got {len(tools)}"


# ============================================================================
# Helper Function Tests - Block parsing
# ============================================================================


def test_extract_text_from_element():
    """Test text extraction from various element types."""
    from camel.toolkits.lark_toolkit import _extract_text_from_element

    assert (
        _extract_text_from_element({"text_run": {"content": "Hello"}})
        == "Hello"
    )
    assert (
        _extract_text_from_element({"mention_user": {"user_id": "u1"}})
        == "@u1"
    )
    assert _extract_text_from_element({"unknown": {}}) == ""


def test_extract_text_from_block():
    """Test text extraction from various block types."""
    from camel.toolkits.lark_toolkit import _extract_text_from_block

    # Text block
    text_block = {
        "block_type": 2,
        "text": {"elements": [{"text_run": {"content": "Hello"}}]},
    }
    assert _extract_text_from_block(text_block) == "Hello"

    # Heading
    h1 = {
        "block_type": 3,
        "heading1": {"elements": [{"text_run": {"content": "Title"}}]},
    }
    assert _extract_text_from_block(h1) == "# Title"

    # Bullet
    bullet = {
        "block_type": 12,
        "bullet": {"elements": [{"text_run": {"content": "Item"}}]},
    }
    assert _extract_text_from_block(bullet) == "• Item"

    # Divider
    assert _extract_text_from_block({"block_type": 22}) == "---"


# ============================================================================
# Drive Operation Tests
# ============================================================================


def test_lark_get_root_folder_token(lark_toolkit):
    """Test getting root folder token."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {"token": "root_token", "id": "folder_id"},
        }

        result = lark_toolkit.lark_get_root_folder_token()

        assert result["token"] == "root_token"
        mock_get.assert_called_once()
        assert "root_folder/meta" in mock_get.call_args[0][0]


def test_lark_list_folder_contents(lark_toolkit):
    """Test listing folder contents."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "files": [{"token": "t1", "name": "Doc", "type": "docx"}],
                "has_more": False,
            },
        }

        result = lark_toolkit.lark_list_folder_contents(folder_token="root")

        assert len(result["files"]) == 1
        mock_get.assert_called_once()


# ============================================================================
# Messaging Operation Tests
# ============================================================================


def test_lark_send_message(lark_toolkit, mock_lark_client):
    """Test sending a message."""
    with patch("requests.post") as mock_post:
        token_resp = mock_lark_client.auth.v3.tenant_access_token.internal
        token_resp.return_value.success.return_value = True
        token_resp.return_value.raw.content = json.dumps(
            {"tenant_access_token": "token"}
        ).encode()

        mock_post.return_value.json.return_value = {
            "code": 0,
            "data": {"message_id": "msg_123", "chat_id": "oc_456"},
        }

        result = lark_toolkit.lark_send_message(
            receive_id="oc_456", content="Hello!", receive_id_type="chat_id"
        )

        assert result["message_id"] == "msg_123"
        mock_post.assert_called_once()
        assert "im/v1/messages" in mock_post.call_args[0][0]


def test_lark_send_message_failure(lark_toolkit, mock_lark_client):
    """Test message sending failure."""
    with patch("requests.post") as mock_post:
        token_resp = mock_lark_client.auth.v3.tenant_access_token.internal
        token_resp.return_value.success.return_value = True
        token_resp.return_value.raw.content = json.dumps(
            {"tenant_access_token": "token"}
        ).encode()

        mock_post.return_value.json.return_value = {
            "code": 99991,
            "msg": "Error",
        }

        result = lark_toolkit.lark_send_message(
            receive_id="x", content="Hi", receive_id_type="open_id"
        )

        assert "error" in result


def test_lark_list_chats(lark_toolkit, mock_lark_client):
    """Test listing chats."""
    with patch("requests.get") as mock_get:
        token_resp = mock_lark_client.auth.v3.tenant_access_token.internal
        token_resp.return_value.success.return_value = True
        token_resp.return_value.raw.content = json.dumps(
            {"tenant_access_token": "token"}
        ).encode()

        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "items": [{"chat_id": "oc_1", "name": "Team"}],
                "has_more": False,
            },
        }

        result = lark_toolkit.lark_list_chats()

        assert len(result["items"]) == 1
        mock_get.assert_called_once()


# ============================================================================
# OAuth Operation Tests
# ============================================================================


def test_clear_cached_tokens(lark_toolkit):
    """Test clearing cached OAuth tokens from memory and disk."""
    from pathlib import Path

    # Set up tokens in memory
    lark_toolkit._user_access_token = "test_token"
    lark_toolkit._refresh_token = "test_refresh"
    lark_toolkit._token_expires_at = 12345.0

    # Mock the token file existence and deletion
    with patch.object(Path, 'exists', return_value=True):
        with patch.object(Path, 'unlink') as mock_unlink:
            result = lark_toolkit.clear_cached_tokens()

            # Verify tokens were cleared from memory
            assert result is True
            assert lark_toolkit._user_access_token is None
            assert lark_toolkit._refresh_token is None
            assert lark_toolkit._token_expires_at is None

            # Verify file deletion was attempted
            mock_unlink.assert_called_once()


def test_clear_cached_tokens_no_file(lark_toolkit):
    """Test clearing tokens when no cached file exists."""
    from pathlib import Path

    # Set up tokens in memory
    lark_toolkit._user_access_token = "test_token"
    lark_toolkit._refresh_token = "test_refresh"
    lark_toolkit._token_expires_at = 12345.0

    # Mock no token file exists
    with patch.object(Path, 'exists', return_value=False):
        result = lark_toolkit.clear_cached_tokens()

        # Should still succeed and clear memory tokens
        assert result is True
        assert lark_toolkit._user_access_token is None
        assert lark_toolkit._refresh_token is None
        assert lark_toolkit._token_expires_at is None


def test_clear_cached_tokens_delete_failure(lark_toolkit):
    """Test clearing tokens when file deletion fails."""
    from pathlib import Path

    lark_toolkit._user_access_token = "test_token"

    # Mock file exists but deletion fails
    with patch.object(Path, 'exists', return_value=True):
        err = OSError("Permission denied")
        with patch.object(Path, 'unlink', side_effect=err):
            result = lark_toolkit.clear_cached_tokens()

            # Should return False on deletion failure
            assert result is False
            # Memory tokens should still be cleared
            assert lark_toolkit._user_access_token is None


# ============================================================================
# Document Block Tests
# ============================================================================


def test_lark_list_document_blocks(lark_toolkit):
    """Test listing document blocks."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {
                        "block_id": "b1",
                        "block_type": 2,
                        "parent_id": "doc_123",
                    },
                    {
                        "block_id": "b2",
                        "block_type": 3,
                        "parent_id": "doc_123",
                    },
                ],
                "has_more": False,
            },
        }

        result = lark_toolkit.lark_list_document_blocks(document_id="doc_123")

        assert result["document_id"] == "doc_123"
        assert len(result["blocks"]) == 2
        assert result["has_more"] is False
        mock_get.assert_called_once()


def test_lark_list_document_blocks_failure(lark_toolkit):
    """Test listing document blocks failure."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 99991,
            "msg": "Document not found",
        }

        result = lark_toolkit.lark_list_document_blocks(document_id="invalid")

        assert "error" in result
        assert "Document not found" in result["error"]


def test_lark_get_block(lark_toolkit):
    """Test getting a specific block."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "block": {
                    "block_id": "block_1",
                    "block_type": 2,
                    "parent_id": "doc_123",
                    "children": ["child_1", "child_2"],
                    "text": {"elements": [{"text_run": {"content": "Hello"}}]},
                }
            },
        }

        result = lark_toolkit.lark_get_block(
            document_id="doc_123", block_id="block_1"
        )

        assert result["block_id"] == "block_1"
        assert result["block_type"] == 2
        assert result["children"] == ["child_1", "child_2"]
        mock_get.assert_called_once()


def test_lark_get_block_failure(lark_toolkit):
    """Test getting a block failure."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 99991,
            "msg": "Block not found",
        }

        result = lark_toolkit.lark_get_block(
            document_id="doc_123", block_id="invalid"
        )

        assert "error" in result
        assert "Block not found" in result["error"]


def test_lark_get_block_children(lark_toolkit):
    """Test getting block children."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {
                        "block_id": "child_1",
                        "block_type": 2,
                        "parent_id": "block_1",
                    },
                    {
                        "block_id": "child_2",
                        "block_type": 2,
                        "parent_id": "block_1",
                    },
                ],
                "has_more": False,
            },
        }

        result = lark_toolkit.lark_get_block_children(
            document_id="doc_123", block_id="block_1"
        )

        assert result["block_id"] == "block_1"
        assert len(result["children"]) == 2
        assert result["has_more"] is False
        mock_get.assert_called_once()


def test_lark_get_block_children_failure(lark_toolkit):
    """Test getting block children failure."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 99991,
            "msg": "Block not found",
        }

        result = lark_toolkit.lark_get_block_children(
            document_id="doc_123", block_id="invalid"
        )

        assert "error" in result


def test_lark_create_folder(lark_toolkit):
    """Test creating a folder."""
    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
    ):
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {"token": "root_token", "id": "folder_id"},
        }
        mock_post.return_value.json.return_value = {
            "code": 0,
            "data": {
                "token": "new_folder_token",
                "url": "https://larksuite.com/drive/folder/new_folder_token",
            },
        }

        result = lark_toolkit.lark_create_folder(name="Test Folder")

        assert result["token"] == "new_folder_token"
        assert "url" in result


def test_lark_get_chat(lark_toolkit, mock_lark_client):
    """Test getting chat details."""
    with patch("requests.get") as mock_get:
        token_resp = mock_lark_client.auth.v3.tenant_access_token.internal
        token_resp.return_value.success.return_value = True
        token_resp.return_value.raw.content = json.dumps(
            {"tenant_access_token": "token"}
        ).encode()

        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "chat_id": "oc_123",
                "name": "Test Chat",
                "user_count": 5,
            },
        }

        result = lark_toolkit.lark_get_chat(chat_id="oc_123")

        assert result["chat_id"] == "oc_123"
        assert result["name"] == "Test Chat"


def test_lark_get_chat_messages(lark_toolkit, mock_lark_client):
    """Test getting chat messages."""
    with patch("requests.get") as mock_get:
        token_resp = mock_lark_client.auth.v3.tenant_access_token.internal
        token_resp.return_value.success.return_value = True
        token_resp.return_value.raw.content = json.dumps(
            {"tenant_access_token": "token"}
        ).encode()

        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "items": [{"message_id": "msg_1", "msg_type": "text"}],
                "has_more": False,
            },
        }

        result = lark_toolkit.lark_get_chat_messages(container_id="oc_123")

        assert len(result["items"]) == 1
        assert result["has_more"] is False


def test_lark_get_chat_messages_time_filters(lark_toolkit, mock_lark_client):
    """Test getting chat messages with time filtering options."""
    with patch("requests.get") as mock_get:
        token_resp = mock_lark_client.auth.v3.tenant_access_token.internal
        token_resp.return_value.success.return_value = True
        token_resp.return_value.raw.content = json.dumps(
            {"tenant_access_token": "token"}
        ).encode()

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
            start_time="1609459200",
            end_time="1609545600",
            sort_type="ByCreateTimeAsc",
        )

        assert len(result["items"]) == 1
        assert result["has_more"] is True

        # Verify time filters were passed in the request
        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["start_time"] == "1609459200"
        assert params["end_time"] == "1609545600"
        assert params["sort_type"] == "ByCreateTimeAsc"


# ============================================================================
# Additional Failure Tests - Key error handling scenarios
# ============================================================================


def test_lark_get_document_failure(lark_toolkit):
    """Test getting document failure."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 99991,
            "msg": "Document not found",
        }

        result = lark_toolkit.lark_get_document(document_id="invalid")

        assert "error" in result
        assert "Document not found" in result["error"]


def test_lark_list_folder_contents_failure(lark_toolkit):
    """Test listing folder contents failure."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 99991,
            "msg": "Folder not found",
        }

        result = lark_toolkit.lark_list_folder_contents(folder_token="invalid")

        assert "error" in result
        assert "Folder not found" in result["error"]


# ============================================================================
# Pagination Tests - Representative pagination handling
# ============================================================================


def test_lark_list_folder_contents_pagination(lark_toolkit):
    """Test folder contents pagination."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "files": [{"token": "t1", "name": "File1", "type": "docx"}],
                "has_more": True,
                "next_page_token": "page_2_token",
            },
        }

        result = lark_toolkit.lark_list_folder_contents(folder_token="root")

        assert result["has_more"] is True
        assert result["page_token"] == "page_2_token"

        # Second page with page_token
        mock_get.return_value.json.return_value = {
            "code": 0,
            "data": {
                "files": [{"token": "t2", "name": "File2", "type": "docx"}],
                "has_more": False,
            },
        }

        result2 = lark_toolkit.lark_list_folder_contents(
            folder_token="root", page_token="page_2_token"
        )

        assert result2["has_more"] is False
        call_args = mock_get.call_args
        assert call_args[1]["params"]["page_token"] == "page_2_token"
