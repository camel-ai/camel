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
import json
import tempfile
from contextlib import AsyncExitStack
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.toolkits.mcp_toolkit import MCPToolkit, _MCPServer


class Test_MCPServer:
    r"""Test _MCPServer class."""

    @pytest.mark.asyncio
    async def test_init(self):
        r"""Test initialization of _MCPServer."""
        # Test with default parameters
        server = _MCPServer("test_command")
        assert server.command_or_url == "test_command"
        assert server.args == []
        assert server.env == {}
        assert server._mcp_tools == []
        assert server.session is None
        assert server._is_connected is False

        # Test with custom parameters
        server = _MCPServer(
            "test_url",
            args=["--arg1", "--arg2"],
            env={"ENV_VAR": "value"},
            timeout=30,
        )
        assert server.command_or_url == "test_url"
        assert server.args == ["--arg1", "--arg2"]
        assert server.env == {"ENV_VAR": "value"}
        assert server._mcp_tools == []
        assert server.session is None
        assert server._is_connected is False

    @pytest.mark.asyncio
    async def test_connection_http(self):
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
            server = _MCPServer("https://example.com/api")
            async with server.connection() as connected_server:
                assert connected_server._is_connected is True
                assert connected_server._mcp_tools == ["tool1", "tool2"]

            # Verify mocks were called correctly
            mock_sse_client.assert_called_once_with(
                "https://example.com/api", headers={}
            )
            mock_session.assert_called_once()
            mock_session_instance.initialize.assert_called_once()
            mock_session_instance.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_stdio(self):
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
            server = _MCPServer(
                "local_command", args=["--arg1"], env={"ENV_VAR": "value"}
            )
            async with server.connection() as connected_server:
                assert connected_server._is_connected is True
                assert connected_server._mcp_tools == ["tool1", "tool2"]

            # Verify mocks were called correctly
            mock_stdio_client.assert_called_once()
            mock_session.assert_called_once()
            mock_session_instance.initialize.assert_called_once()
            mock_session_instance.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_mcp_tools_not_connected(self):
        r"""Test list_mcp_tools when not connected."""
        server = _MCPServer("test_command")
        result = await server.list_mcp_tools()
        assert isinstance(result, str)
        assert "not connected" in result

    @pytest.mark.asyncio
    async def test_list_mcp_tools_connected(self):
        r"""Test list_mcp_tools when connected."""
        server = _MCPServer("test_command")
        server._session = AsyncMock()

        # Mock successful response
        mock_result = MagicMock()
        server._session.list_tools.return_value = mock_result

        result = await server.list_mcp_tools()
        assert result == mock_result
        server._session.list_tools.assert_called_once()

        # Mock exception
        server._session.list_tools.side_effect = Exception("Test error")
        result = await server.list_mcp_tools()
        assert isinstance(result, str)
        assert "Failed to list MCP tools" in result

    @pytest.mark.asyncio
    async def test_generate_function_from_mcp_tool(self):
        r"""Test generate_function_from_mcp_tool."""
        server = _MCPServer("test_command")
        server._session = AsyncMock()

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
        func = server.generate_function_from_mcp_tool(mock_tool)

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
        server._session.call_tool.return_value = mock_result

        # Test function call
        result = await func(param1="test", param2=123)
        assert result == "Test result"
        server._session.call_tool.assert_called_once_with(
            "test_function", {"param1": "test", "param2": 123}
        )

        # Test missing required parameter - now returns a message
        with patch("camel.toolkits.mcp_toolkit.logger") as mock_logger:
            mock_logger.reset_mock()

            result = await func(param1="test")
            assert result == "Missing required parameters."
            mock_logger.warning.assert_called_once()

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
    async def test_build_tool_schema(self):
        r"""Test build_tool_schema method."""
        server = _MCPServer("test_command")
        mock_tool = MagicMock()
        mock_tool.name = "test_function"
        mock_tool.description = "Test function description"
        mock_tool.inputSchema = {
            "properties": {
                "param1": {"type": "string"},
                "param2": {"type": "integer"},
            },
            "required": ["param1", "param2"],
        }
        schema = server._build_tool_schema(mock_tool)

        target_schema = {
            "type": "function",
            "function": {
                "name": "test_function",
                "description": "Test function description",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"},
                        "param2": {"type": "integer"},
                    },
                    "required": ["param1", "param2"],
                },
            },
        }
        assert schema == target_schema

        # No description
        mock_tool.description = None
        schema = server._build_tool_schema(mock_tool)
        assert schema == {
            "type": "function",
            "function": {
                "name": "test_function",
                "description": "No description provided.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "param1": {"type": "string"},
                        "param2": {"type": "integer"},
                    },
                    "required": ["param1", "param2"],
                },
            },
        }

    @pytest.mark.asyncio
    async def test_get_tools(self):
        r"""Test get_tools method for _MCPServer."""
        with patch(
            "camel.toolkits.mcp_toolkit.FunctionTool"
        ) as mock_function_tool:
            server = _MCPServer("test_command")

            # Mock tools
            mock_tool1 = MagicMock()
            mock_tool2 = MagicMock()
            server._mcp_tools = [mock_tool1, mock_tool2]

            # Mock generate_function_from_mcp_tool
            mock_func1 = AsyncMock()
            mock_func2 = AsyncMock()
            server.generate_function_from_mcp_tool = MagicMock(
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
            tools = server.get_tools()

            # Verify results
            assert len(tools) == 2
            assert tools[0] == mock_function_tool_instance1
            assert tools[1] == mock_function_tool_instance2

            # Verify mocks were called correctly
            server.generate_function_from_mcp_tool.assert_any_call(mock_tool1)
            server.generate_function_from_mcp_tool.assert_any_call(mock_tool2)

    @pytest.mark.asyncio
    async def test_connect_explicit(self):
        r"""Test explicit connect method."""
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
            server = _MCPServer("https://example.com/api")
            result = await server.connect()

            # Verify results
            assert result == server
            assert server._is_connected is True
            assert server._mcp_tools == ["tool1", "tool2"]
            assert server.session is not None

            # Verify mocks were called correctly
            mock_sse_client.assert_called_once_with(
                "https://example.com/api", headers={}
            )
            mock_session.assert_called_once()
            mock_session_instance.initialize.assert_called_once()
            mock_session_instance.list_tools.assert_called_once()

            # Test connecting when already connected
            with patch("camel.toolkits.mcp_toolkit.logger") as mock_logger:
                result = await server.connect()
                assert result == server
                mock_logger.warning.assert_called_once()
                # Verify no new connections were made
                assert mock_sse_client.call_count == 1

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        r"""Test connect method with failure."""
        with patch("mcp.client.sse.sse_client") as mock_sse_client:
            # Setup mock to raise exception
            mock_sse_client.return_value.__aenter__.side_effect = Exception(
                "Connection error"
            )

            # Create server
            server = _MCPServer("https://example.com/api")

            # Mock disconnect to verify it's called on failure
            server.disconnect = AsyncMock()

            # Test connect with failure
            with patch("camel.toolkits.mcp_toolkit.logger") as mock_logger:
                await server.connect()

                # Verify disconnect was called to clean up
                server.disconnect.assert_called_once()
                mock_logger.error.assert_called_once()

                # Verify server is not connected
                assert server._is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_explicit(self):
        r"""Test explicit disconnect method."""
        # Create server
        server = _MCPServer("test_command")

        # Setup connected state
        server._is_connected = True
        server._exit_stack = AsyncMock()
        server._exit_stack.aclose = AsyncMock()
        server._session = MagicMock()

        # Test disconnect
        await server.disconnect()

        # Verify results
        assert server._is_connected is False
        assert server.session is None
        server._exit_stack.aclose.assert_called_once()

        # Test disconnecting when not connected
        server._exit_stack.aclose.reset_mock()

        # Set up disconnected state
        server._is_connected = False
        server._exit_stack = AsyncMock()
        server._exit_stack.aclose = AsyncMock()

        await server.disconnect()

        # Verify exit stack is still closed even when not connected
        server._exit_stack.aclose.assert_called_once()


class TestMCPToolkit:
    r"""Test MCPToolkit class."""

    def test_init(self):
        r"""Test initialization of MCPToolkit."""
        # Test with servers list
        server1 = _MCPServer("test_command1")
        server2 = _MCPServer("test_command2")
        toolkit = MCPToolkit(servers=[server1, server2])

        assert toolkit.servers == [server1, server2]
        assert isinstance(toolkit._exit_stack, AsyncExitStack)
        assert toolkit._connected is False

        # Test with both servers and config_path
        with patch("camel.toolkits.mcp_toolkit.logger") as mock_logger:
            with patch.object(
                MCPToolkit, "_load_servers_from_config", return_value=[]
            ):
                toolkit = MCPToolkit(
                    servers=[server1], config_path="dummy_path"
                )
                assert toolkit.servers == [server1]
                mock_logger.warning.assert_called_once()

    def test_init_config_file_not_found(self):
        r"""Test from_config with non-existent file."""
        with patch("camel.toolkits.mcp_toolkit.logger") as mock_logger:
            with tempfile.TemporaryDirectory() as temp_dir:
                non_existent_path = Path(temp_dir) / "non_existent.json"
                toolkit = MCPToolkit(config_path=str(non_existent_path))

                # Should return an empty toolkit.
                assert toolkit.servers == []
                mock_logger.warning.assert_called_once()

    def test_init_config_invalid_json(self):
        r"""Test from_config with invalid JSON."""
        with patch("camel.toolkits.mcp_toolkit.logger") as mock_logger:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "invalid.json"
                config_path.write_text("{invalid json")

                toolkit = MCPToolkit(config_path=str(config_path))

                # Should return an empty toolkit
                assert toolkit.servers == []
                mock_logger.warning.assert_called_once()

    def test_init_config_valid(self):
        r"""Test from_config with valid configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "valid.json"
            config_data = {
                "mcpServers": {
                    "server1": {
                        "command": "test-command",
                        "args": ["--arg1"],
                        "env": {"TEST_ENV": "value"},
                    },
                    "server2": {"url": "https://test.com/sse"},
                }
            }
            config_path.write_text(json.dumps(config_data))

            toolkit = MCPToolkit(config_path=str(config_path))
            assert len(toolkit.servers) == 2

            # Check local server toolkit
            assert toolkit.servers[0].command_or_url == "test-command"
            assert toolkit.servers[0].args == ["--arg1"]
            assert "TEST_ENV" in toolkit.servers[0].env

            # Check web server toolkit
            assert toolkit.servers[1].command_or_url == "https://test.com/sse"

    def test_load_servers_from_config_missing_required_fields(self):
        r"""Test _load_servers_from_config with missing required fields."""
        with patch("camel.toolkits.mcp_toolkit.logger") as mock_logger:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "invalid_fields.json"

                # Missing command field
                config_data = {"mcpServers": {"server1": {"args": ["--arg1"]}}}
                config_path.write_text(json.dumps(config_data))

                mcp_toolkit = MCPToolkit()
                servers = mcp_toolkit._load_servers_from_config(
                    str(config_path)
                )
                # Should return an empty list and log a warning
                assert servers == []
                mock_logger.warning.assert_called()

                mock_logger.reset_mock()

                # Missing url field
                config_data = {"mcpServers": {"server1": {"timeout": 30}}}
                config_path.write_text(json.dumps(config_data))

                servers = mcp_toolkit._load_servers_from_config(
                    str(config_path)
                )
                # Should return an empty list and log a warning
                assert servers == []
                mock_logger.warning.assert_called()

    def test_load_servers_from_config_invalid_structure(self):
        r"""Test _load_servers_from_config with invalid structure."""
        with patch("camel.toolkits.mcp_toolkit.logger") as mock_logger:
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = Path(temp_dir) / "invalid_structure.json"

                # mcpServers is not a dictionary
                config_data = {"mcpServers": "not a dictionary"}
                config_path.write_text(json.dumps(config_data))

                mcp_toolkit = MCPToolkit()
                servers = mcp_toolkit._load_servers_from_config(
                    str(config_path)
                )
                # Should return an empty list and log a warning
                assert servers == []
                mock_logger.warning.assert_called_with(
                    "'mcpServers' is not a dictionary, skipping..."
                )

    @pytest.mark.asyncio
    async def test_connection(self):
        r"""Test connection context manager."""
        server1 = _MCPServer("test_command1")
        server2 = _MCPServer("test_command2")
        toolkit = MCPToolkit(servers=[server1, server2])

        # Mock the connection context managers of both servers
        class MockAsyncContextManager:
            async def __aenter__(self):
                return AsyncMock()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        server1.connection = MagicMock(return_value=MockAsyncContextManager())
        server2.connection = MagicMock(return_value=MockAsyncContextManager())

        async with toolkit.connection() as connected_toolkit:
            assert connected_toolkit._connected is True
            assert isinstance(connected_toolkit._exit_stack, AsyncExitStack)

        assert toolkit._connected is False
        assert isinstance(toolkit._exit_stack, AsyncExitStack)

    def test_is_connected(self):
        r"""Test is_connected method."""
        toolkit = MCPToolkit(servers=[_MCPServer("test_command")])
        assert toolkit.is_connected() is False
        toolkit._connected = True
        assert toolkit.is_connected() is True

    @pytest.mark.asyncio
    async def test_get_tools(self):
        r"""Test get_tools method."""
        server1 = _MCPServer("test_command1")
        server2 = _MCPServer("test_command2")
        toolkit = MCPToolkit(servers=[server1, server2])

        # Mock get_tools for both servers
        mock_tool1 = MagicMock()
        mock_tool2 = MagicMock()
        mock_tool3 = MagicMock()

        server1.get_tools = MagicMock(return_value=[mock_tool1, mock_tool2])
        server2.get_tools = MagicMock(return_value=[mock_tool3])

        tools = toolkit.get_tools()

        assert len(tools) == 3
        assert tools == [mock_tool1, mock_tool2, mock_tool3]
        server1.get_tools.assert_called_once()
        server2.get_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect(self):
        r"""Test explicit connect method."""
        # Create mock servers
        server1 = _MCPServer("test_command1")
        server2 = _MCPServer("test_command2")

        # Mock connect methods
        server1.connect = AsyncMock(return_value=server1)
        server2.connect = AsyncMock(return_value=server2)

        # Create toolkit with mock servers
        toolkit = MCPToolkit(servers=[server1, server2])

        # Test connect
        result = await toolkit.connect()

        # Verify results
        assert result == toolkit
        assert toolkit._connected is True
        assert toolkit._exit_stack is not None
        server1.connect.assert_called_once()
        server2.connect.assert_called_once()

        # Test connecting when already connected
        with patch("camel.toolkits.mcp_toolkit.logger") as mock_logger:
            result = await toolkit.connect()
            assert result == toolkit
            mock_logger.warning.assert_called_once()
            # Verify servers not connected again
            assert server1.connect.call_count == 1
            assert server2.connect.call_count == 1

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        r"""Test connect method with failure."""
        # Create mock servers
        server1 = _MCPServer("test_command1")
        server2 = _MCPServer("test_command2")

        # First server connects successfully, second fails
        server1.connect = AsyncMock(return_value=server1)
        server2.connect = AsyncMock(side_effect=Exception("Connection error"))

        # Create toolkit with mock servers
        toolkit = MCPToolkit(servers=[server1, server2])

        # Mock disconnect to verify it's called on failure
        toolkit.disconnect = AsyncMock()

        # Test connect with failure
        with patch("camel.toolkits.mcp_toolkit.logger") as mock_logger:
            await toolkit.connect()

            # Verify disconnect was called to clean up
            toolkit.disconnect.assert_called_once()
            mock_logger.error.assert_called_once()

            # Verify first server was connected
            server1.connect.assert_called_once()
            # Verify second server was attempted
            server2.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        r"""Test explicit disconnect method."""
        # Create mock servers
        server1 = _MCPServer("test_command1")
        server2 = _MCPServer("test_command2")

        # Mock disconnect methods
        server1.disconnect = AsyncMock()
        server2.disconnect = AsyncMock()

        # Create toolkit with mock servers
        toolkit = MCPToolkit(servers=[server1, server2])

        # Setup connected state
        toolkit._connected = True
        toolkit._exit_stack = AsyncMock()
        toolkit._exit_stack.aclose = AsyncMock()

        # Test disconnect
        await toolkit.disconnect()

        # Verify results
        assert toolkit._connected is False
        server1.disconnect.assert_called_once()
        server2.disconnect.assert_called_once()
        toolkit._exit_stack.aclose.assert_called_once()

        # Test disconnecting when not connected
        server1.disconnect.reset_mock()
        server2.disconnect.reset_mock()
        toolkit._exit_stack.aclose.reset_mock()

        await toolkit.disconnect()

        # Verify no actions taken when not connected
        server1.disconnect.assert_not_called()
        server2.disconnect.assert_not_called()
        toolkit._exit_stack.aclose.assert_not_called()
