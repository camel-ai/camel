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
    """Create a mock Lark client."""
    with patch("lark_oapi.Client") as mock_client_class:
        mock_client = MagicMock()
        builder = mock_client_class.builder.return_value
        app_id = builder.app_id.return_value
        app_secret = app_id.app_secret.return_value
        domain = app_secret.domain.return_value
        domain.build.return_value = mock_client
        yield mock_client


def test_lark_toolkit_init(mock_env_vars, mock_lark_client):
    """Test LarkToolkit initialization."""
    from camel.toolkits import LarkToolkit

    toolkit = LarkToolkit()
    assert toolkit._app_id == "test_app_id"
    assert toolkit._app_secret == "test_app_secret"
    assert toolkit._domain == "https://open.larksuite.com"


def test_lark_toolkit_init_with_custom_domain(mock_env_vars, mock_lark_client):
    """Test LarkToolkit initialization with custom domain."""
    from camel.toolkits import LarkToolkit

    toolkit = LarkToolkit(domain="https://open.feishu.cn")
    assert toolkit._domain == "https://open.feishu.cn"


def test_lark_create_document(mock_env_vars, mock_lark_client):
    """Test creating a Lark document."""
    from camel.toolkits import LarkToolkit

    # Mock the response
    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data.document.document_id = "doc_123"
    mock_response.data.document.title = "Test Document"
    mock_response.data.document.revision_id = 1

    mock_lark_client.docx.v1.document.create.return_value = mock_response

    toolkit = LarkToolkit()
    result = toolkit.lark_create_document(title="Test Document")

    assert result["document_id"] == "doc_123"
    assert result["title"] == "Test Document"
    assert result["revision_id"] == 1
    assert "url" in result


def test_lark_create_document_failure(mock_env_vars, mock_lark_client):
    """Test handling of document creation failure."""
    from camel.toolkits import LarkToolkit

    # Mock a failed response
    mock_response = MagicMock()
    mock_response.success.return_value = False
    mock_response.code = 99991
    mock_response.msg = "Permission denied"

    mock_lark_client.docx.v1.document.create.return_value = mock_response

    toolkit = LarkToolkit()
    result = toolkit.lark_create_document(title="Test Document")

    assert "error" in result
    assert "Permission denied" in result["error"]


def test_lark_get_document(mock_env_vars, mock_lark_client):
    """Test getting document metadata."""
    from camel.toolkits import LarkToolkit

    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data.document.document_id = "doc_123"
    mock_response.data.document.title = "Test Document"
    mock_response.data.document.revision_id = 5

    mock_lark_client.docx.v1.document.get.return_value = mock_response

    toolkit = LarkToolkit()
    result = toolkit.lark_get_document(document_id="doc_123")

    assert result["document_id"] == "doc_123"
    assert result["title"] == "Test Document"
    assert result["revision_id"] == 5


def test_lark_get_document_content(mock_env_vars, mock_lark_client):
    """Test getting document raw content."""
    from camel.toolkits import LarkToolkit

    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data.content = "This is the document content"

    mock_lark_client.docx.v1.document.raw_content.return_value = mock_response

    toolkit = LarkToolkit()
    result = toolkit.lark_get_document_content(document_id="doc_123")

    assert result["document_id"] == "doc_123"
    assert result["content"] == "This is the document content"


def test_lark_list_document_blocks(mock_env_vars, mock_lark_client):
    """Test listing document blocks."""
    from camel.toolkits import LarkToolkit

    # Create mock blocks
    mock_block1 = MagicMock()
    mock_block1.block_id = "block_1"
    mock_block1.block_type = 2
    mock_block1.parent_id = "doc_123"

    mock_block2 = MagicMock()
    mock_block2.block_id = "block_2"
    mock_block2.block_type = 3
    mock_block2.parent_id = "doc_123"

    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data.items = [mock_block1, mock_block2]
    mock_response.data.has_more = False
    mock_response.data.page_token = None

    mock_lark_client.docx.v1.document_block.list.return_value = mock_response

    toolkit = LarkToolkit()
    result = toolkit.lark_list_document_blocks(document_id="doc_123")

    assert result["document_id"] == "doc_123"
    assert len(result["blocks"]) == 2
    assert result["blocks"][0]["block_id"] == "block_1"
    assert result["has_more"] is False


def test_lark_get_block(mock_env_vars, mock_lark_client):
    """Test getting a specific block."""
    from camel.toolkits import LarkToolkit

    mock_block = MagicMock()
    mock_block.block_id = "block_1"
    mock_block.block_type = 2
    mock_block.parent_id = "doc_123"
    mock_block.children = ["child_1", "child_2"]

    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data.block = mock_block

    mock_lark_client.docx.v1.document_block.get.return_value = mock_response

    toolkit = LarkToolkit()
    result = toolkit.lark_get_block(document_id="doc_123", block_id="block_1")

    assert result["block_id"] == "block_1"
    assert result["block_type"] == 2
    assert result["parent_id"] == "doc_123"
    assert result["children"] == ["child_1", "child_2"]


def test_lark_get_block_children(mock_env_vars, mock_lark_client):
    """Test getting child blocks."""
    from camel.toolkits import LarkToolkit

    mock_child = MagicMock()
    mock_child.block_id = "child_1"
    mock_child.block_type = 2
    mock_child.parent_id = "block_1"

    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data.items = [mock_child]
    mock_response.data.has_more = False
    mock_response.data.page_token = None

    mock_lark_client.docx.v1.document_block_children.get.return_value = (
        mock_response
    )

    toolkit = LarkToolkit()
    result = toolkit.lark_get_block_children(
        document_id="doc_123", block_id="block_1"
    )

    assert result["block_id"] == "block_1"
    assert len(result["children"]) == 1
    assert result["children"][0]["block_id"] == "child_1"


def test_lark_create_block(mock_env_vars, mock_lark_client):
    """Test creating a new block."""
    from camel.toolkits import LarkToolkit

    mock_created_block = MagicMock()
    mock_created_block.block_id = "new_block_1"

    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data.children = [mock_created_block]
    mock_response.data.document_revision_id = 10

    mock_lark_client.docx.v1.document_block_children.create.return_value = (
        mock_response
    )

    toolkit = LarkToolkit()
    result = toolkit.lark_create_block(
        document_id="doc_123",
        block_type="text",
        content="New paragraph text",
    )

    assert result["block_id"] == "new_block_1"
    assert result["block_type"] == "text"
    assert result["document_revision_id"] == 10


def test_lark_create_heading_block(mock_env_vars, mock_lark_client):
    """Test creating a heading block."""
    from camel.toolkits import LarkToolkit

    mock_created_block = MagicMock()
    mock_created_block.block_id = "heading_block_1"

    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data.children = [mock_created_block]
    mock_response.data.document_revision_id = 11

    mock_lark_client.docx.v1.document_block_children.create.return_value = (
        mock_response
    )

    toolkit = LarkToolkit()
    result = toolkit.lark_create_block(
        document_id="doc_123",
        block_type="heading1",
        content="Main Heading",
    )

    assert result["block_id"] == "heading_block_1"
    assert result["block_type"] == "heading1"


def test_lark_update_block(mock_env_vars, mock_lark_client):
    """Test updating a block."""
    from camel.toolkits import LarkToolkit

    mock_response = MagicMock()
    mock_response.success.return_value = True
    mock_response.data.document_revision_id = 12

    mock_lark_client.docx.v1.document_block.patch.return_value = mock_response

    toolkit = LarkToolkit()
    result = toolkit.lark_update_block(
        document_id="doc_123",
        block_id="block_1",
        content="Updated content",
    )

    assert result["success"] is True
    assert result["block_id"] == "block_1"
    assert result["document_revision_id"] == 12


def test_lark_delete_block(mock_env_vars, mock_lark_client):
    """Test deleting a block."""
    from camel.toolkits import LarkToolkit

    # Mock get_block response
    mock_get_response = MagicMock()
    mock_get_response.success.return_value = True
    mock_get_response.data.block.block_id = "block_1"
    mock_get_response.data.block.block_type = 2
    mock_get_response.data.block.parent_id = "doc_123"
    mock_get_response.data.block.children = []

    mock_lark_client.docx.v1.document_block.get.return_value = (
        mock_get_response
    )

    # Mock delete response
    mock_delete_response = MagicMock()
    mock_delete_response.success.return_value = True
    mock_delete_response.data.document_revision_id = 13

    block_children = mock_lark_client.docx.v1.document_block_children
    block_children.batch_delete.return_value = mock_delete_response

    toolkit = LarkToolkit()
    result = toolkit.lark_delete_block(
        document_id="doc_123",
        block_id="block_1",
    )

    assert result["success"] is True
    assert result["document_revision_id"] == 13


def test_lark_batch_update_blocks(mock_env_vars, mock_lark_client):
    """Test batch updating blocks."""
    from camel.toolkits import LarkToolkit

    # Mock create response
    mock_created_block = MagicMock()
    mock_created_block.block_id = "new_block_1"

    mock_create_response = MagicMock()
    mock_create_response.success.return_value = True
    mock_create_response.data.children = [mock_created_block]
    mock_create_response.data.document_revision_id = 14

    mock_lark_client.docx.v1.document_block_children.create.return_value = (
        mock_create_response
    )

    # Mock update response
    mock_update_response = MagicMock()
    mock_update_response.success.return_value = True
    mock_update_response.data.document_revision_id = 15

    mock_lark_client.docx.v1.document_block.patch.return_value = (
        mock_update_response
    )

    toolkit = LarkToolkit()
    operations = [
        {"action": "create", "block_type": "text", "content": "New paragraph"},
        {
            "action": "update",
            "block_id": "existing_block",
            "content": "Updated",
        },
    ]
    result = toolkit.lark_batch_update_blocks(
        document_id="doc_123",
        operations=operations,
    )

    assert result["success"] is True
    assert len(result["results"]) == 2
    assert result["results"][0]["block_id"] == "new_block_1"


def test_get_tools(mock_env_vars, mock_lark_client):
    """Test getting all tools from the toolkit."""
    from camel.toolkits import LarkToolkit

    toolkit = LarkToolkit()
    tools = toolkit.get_tools()

    assert len(tools) == 10
    assert all(isinstance(tool, FunctionTool) for tool in tools)

    # Verify tool names
    tool_names = [tool.func.__name__ for tool in tools]
    assert "lark_create_document" in tool_names
    assert "lark_get_document" in tool_names
    assert "lark_get_document_content" in tool_names
    assert "lark_list_document_blocks" in tool_names
    assert "lark_get_block" in tool_names
    assert "lark_get_block_children" in tool_names
    assert "lark_create_block" in tool_names
    assert "lark_update_block" in tool_names
    assert "lark_delete_block" in tool_names
    assert "lark_batch_update_blocks" in tool_names


def test_extract_text_from_block():
    """Test text extraction from block structures."""
    from camel.toolkits.lark_toolkit import _extract_text_from_block

    # Test text block
    text_block = {
        "block_type": 2,
        "text": {
            "elements": [{"text_run": {"content": "Hello world"}}],
        },
    }
    assert _extract_text_from_block(text_block) == "Hello world"

    # Test heading block
    heading_block = {
        "block_type": 3,
        "heading1": {
            "elements": [{"text_run": {"content": "Main Title"}}],
        },
    }
    assert _extract_text_from_block(heading_block) == "# Main Title"

    # Test bullet block
    bullet_block = {
        "block_type": 12,
        "bullet": {
            "elements": [{"text_run": {"content": "List item"}}],
        },
    }
    assert _extract_text_from_block(bullet_block) == "• List item"

    # Test divider block
    divider_block = {"block_type": 22}
    assert _extract_text_from_block(divider_block) == "---"


def test_extract_text_from_element():
    """Test text extraction from text elements."""
    from camel.toolkits.lark_toolkit import _extract_text_from_element

    # Test text_run element
    text_element = {"text_run": {"content": "Hello"}}
    assert _extract_text_from_element(text_element) == "Hello"

    # Test mention_user element
    mention_element = {"mention_user": {"user_id": "user123"}}
    assert _extract_text_from_element(mention_element) == "@user123"

    # Test mention_doc element
    doc_element = {"mention_doc": {"title": "My Document"}}
    assert _extract_text_from_element(doc_element) == "[Doc: My Document]"

    # Test unknown element
    unknown_element = {"unknown_type": {}}
    assert _extract_text_from_element(unknown_element) == ""
