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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.toolkits.mcp_toolkit import MCPToolkit


@pytest.mark.asyncio
async def test_init():
    r"""Test initialization of MCPToolkit."""
    # Test with default parameters
    toolkit = MCPToolkit("test_command")
    assert toolkit.command_or_url == "test_command"
    assert toolkit.args == []
    assert toolkit.env == {}
    assert toolkit._mcp_tools == []
    assert toolkit._session is None
    assert toolkit._is_connected is False

    # Test with custom parameters
    toolkit = MCPToolkit(
        "test_url",
        args=["--arg1", "--arg2"],
        env={"ENV_VAR": "value"},
        timeout=30,
    )
    assert toolkit.command_or_url == "test_url"
    assert toolkit.args == ["--arg1", "--arg2"]
    assert toolkit.env == {"ENV_VAR": "value"}
    assert toolkit._mcp_tools == []
    assert toolkit._session is None
    assert toolkit._is_connected is False


@pytest.mark.asyncio
async def test_connection_http():
    r"""Test connection with HTTP URL."""
    with (
        patch("mcp.client.sse.sse_client") as mock_sse_client,
        patch("mcp.client.session.ClientSession") as mock_session,
    ):
        # Setup mocks
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()
        mock_sse_client.return_value.__aenter__.return_value = (
            mock_read_stream,
            mock_write_stream,
        )

        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = (
            mock_session_instance
        )

        # Mock list_tools result
        list_tools_result = MagicMock()
        list_tools_result.tools = ["tool1", "tool2"]
        mock_session_instance.list_tools.return_value = list_tools_result

        # Test HTTP connection
        toolkit = MCPToolkit("https://example.com/api")
        async with toolkit.connection() as connected_toolkit:
            assert connected_toolkit._is_connected is True
            assert connected_toolkit._mcp_tools == ["tool1", "tool2"]

        # Verify mocks were called correctly
        mock_sse_client.assert_called_once_with("https://example.com/api")
        mock_session.assert_called_once()
        mock_session_instance.initialize.assert_called_once()
        mock_session_instance.list_tools.assert_called_once()


@pytest.mark.asyncio
async def test_connection_stdio():
    r"""Test connection with stdio command."""
    with (
        patch("mcp.client.stdio.stdio_client") as mock_stdio_client,
        patch("mcp.client.session.ClientSession") as mock_session,
    ):
        # Setup mocks
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()
        mock_stdio_client.return_value.__aenter__.return_value = (
            mock_read_stream,
            mock_write_stream,
        )

        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = (
            mock_session_instance
        )

        # Mock list_tools result
        list_tools_result = MagicMock()
        list_tools_result.tools = ["tool1", "tool2"]
        mock_session_instance.list_tools.return_value = list_tools_result

        # Test stdio connection
        toolkit = MCPToolkit(
            "local_command", args=["--arg1"], env={"ENV_VAR": "value"}
        )
        async with toolkit.connection() as connected_toolkit:
            assert connected_toolkit._is_connected is True
            assert connected_toolkit._mcp_tools == ["tool1", "tool2"]

        # Verify mocks were called correctly
        mock_stdio_client.assert_called_once()
        mock_session.assert_called_once()
        mock_session_instance.initialize.assert_called_once()
        mock_session_instance.list_tools.assert_called_once()


@pytest.mark.asyncio
async def test_list_mcp_tools_not_connected():
    r"""Test list_mcp_tools when not connected."""
    toolkit = MCPToolkit("test_command")
    result = await toolkit.list_mcp_tools()
    assert isinstance(result, str)
    assert "not connected" in result


@pytest.mark.asyncio
async def test_list_mcp_tools_connected():
    r"""Test list_mcp_tools when connected."""
    toolkit = MCPToolkit("test_command")
    toolkit._session = AsyncMock()

    # Mock successful response
    mock_result = MagicMock()
    toolkit._session.list_tools.return_value = mock_result

    result = await toolkit.list_mcp_tools()
    assert result == mock_result
    toolkit._session.list_tools.assert_called_once()

    # Mock exception
    toolkit._session.list_tools.side_effect = Exception("Test error")
    result = await toolkit.list_mcp_tools()
    assert isinstance(result, str)
    assert "Failed to list MCP tools" in result


@pytest.mark.asyncio
async def test_generate_function_from_mcp_tool():
    r"""Test generate_function_from_mcp_tool."""
    toolkit = MCPToolkit("test_command")
    toolkit._session = AsyncMock()

    # Create mock MCP tool
    mock_tool = MagicMock()
    mock_tool.name = "test_function"
    mock_tool.description = "Test function description"
    mock_tool.inputSchema = {
        "properties": {
            "param1": {"type": "string"},
            "param2": {"type": "integer"},
            "param3": {"type": "boolean"},
        },
        "required": ["param1", "param2"],
    }

    # Generate function
    func = toolkit.generate_function_from_mcp_tool(mock_tool)

    # Check function attributes
    assert func.__name__ == "test_function"
    assert func.__doc__ == "Test function description"
    assert "param1" in func.__annotations__
    assert "param2" in func.__annotations__
    assert "param3" in func.__annotations__

    # Mock call_tool response
    mock_content = MagicMock()
    mock_content.type = "text"
    mock_content.text = "Test result"

    mock_result = MagicMock()
    mock_result.content = [mock_content]
    toolkit._session.call_tool.return_value = mock_result

    # Test function call
    result = await func(param1="test", param2=123)
    assert result == "Test result"
    toolkit._session.call_tool.assert_called_once_with(
        "test_function", {"param1": "test", "param2": 123}
    )

    # Test missing required parameter
    with pytest.raises(ValueError) as excinfo:
        await func(param1="test")
    assert "Missing required parameters" in str(excinfo.value)

    # Test different content types
    # Image content
    mock_content.type = "image"
    mock_content.url = "https://example.com/image.jpg"
    result = await func(param1="test", param2=123)
    assert "Image available at" in result

    # Image without URL
    mock_content.url = None
    result = await func(param1="test", param2=123)
    assert "Image content received" in result

    # Embedded resource
    mock_content.type = "embedded_resource"
    mock_content.name = "resource.pdf"
    result = await func(param1="test", param2=123)
    assert "Embedded resource: resource.pdf" in result

    # Embedded resource without name
    mock_content.name = None
    result = await func(param1="test", param2=123)
    assert "Embedded resource received" in result

    # Unknown content type
    mock_content.type = "unknown"
    result = await func(param1="test", param2=123)
    assert "not fully supported" in result

    # No content
    mock_result.content = []
    result = await func(param1="test", param2=123)
    assert "No data available" in result


@pytest.mark.asyncio
async def test_get_tools():
    r"""Test get_tools method."""
    with patch(
        "camel.toolkits.mcp_toolkit.FunctionTool"
    ) as mock_function_tool:
        toolkit = MCPToolkit("test_command")

        # Mock tools
        mock_tool1 = MagicMock()
        mock_tool2 = MagicMock()
        toolkit._mcp_tools = [mock_tool1, mock_tool2]

        # Mock generate_function_from_mcp_tool
        mock_func1 = AsyncMock()
        mock_func2 = AsyncMock()
        toolkit.generate_function_from_mcp_tool = MagicMock(
            side_effect=[mock_func1, mock_func2]
        )

        # Mock FunctionTool
        mock_function_tool_instance1 = MagicMock()
        mock_function_tool_instance2 = MagicMock()
        mock_function_tool.side_effect = [
            mock_function_tool_instance1,
            mock_function_tool_instance2,
        ]

        # Get tools
        tools = toolkit.get_tools()

        # Verify results
        assert len(tools) == 2
        assert tools[0] == mock_function_tool_instance1
        assert tools[1] == mock_function_tool_instance2

        # Verify mocks were called correctly
        toolkit.generate_function_from_mcp_tool.assert_any_call(mock_tool1)
        toolkit.generate_function_from_mcp_tool.assert_any_call(mock_tool2)
        mock_function_tool.assert_any_call(mock_func1)
        mock_function_tool.assert_any_call(mock_func2)
