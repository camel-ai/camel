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
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from camel.toolkits.mcp_toolkit import ConnectionState, MCPClient, MCPToolkit


class TestMCPClient:
    r"""Test MCPClient class."""

    @pytest.mark.asyncio
    async def test_init(self):
        r"""Test initialization of MCPClient."""
        # Test with default parameters
        server = MCPClient("test_command")
        assert server.command_or_url == "test_command"
        assert server.args == []
        assert server.env == {}
        assert server._mcp_tools == []
        assert server._session is None
        assert server.is_connected is False

        # Test with custom parameters
        server = MCPClient(
            "test_url",
            args=["--arg1", "--arg2"],
            env={"ENV_VAR": "value"},
            timeout=30,
        )
        assert server.command_or_url == "test_url"
        assert server.args == ["--arg1", "--arg2"]
        assert server.env == {"ENV_VAR": "value"}
        assert server._mcp_tools == []
        assert server._session is None
        assert server.is_connected is False

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

            # Test HTTP connection using async context manager
            server = MCPClient("https://example.com/api")
            async with server as connected_server:
                assert connected_server.is_connected is True
                assert connected_server._mcp_tools == ["tool1", "tool2"]

            # Verify mocks were called correctly
            mock_sse_client.assert_called_once_with(
                "https://example.com/api", headers={}, timeout=None
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

            # Test stdio connection using async context manager
            server = MCPClient(
                "local_command", args=["--arg1"], env={"ENV_VAR": "value"}
            )
            async with server as connected_server:
                assert connected_server.is_connected is True
                assert connected_server._mcp_tools == ["tool1", "tool2"]

            # Verify mocks were called correctly
            mock_stdio_client.assert_called_once()
            mock_session.assert_called_once()
            mock_session_instance.initialize.assert_called_once()
            mock_session_instance.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_mcp_tools_not_connected(self):
        r"""Test list_mcp_tools when not connected."""
        server = MCPClient("test_command")
        result = await server.list_mcp_tools()
        assert isinstance(result, str)
        assert "not connected" in result

    @pytest.mark.asyncio
    async def test_list_mcp_tools_connected(self):
        r"""Test list_mcp_tools when connected."""
        server = MCPClient("test_command")
        server._session = AsyncMock()

        # Mock successful response
        mock_result = MagicMock()
        server._session.list_tools.return_value = mock_result

        result = await server.list_mcp_tools()
        assert result == mock_result
        server._session.list_tools.assert_called_once()

        # Mock exception
        server._session.list_tools.side_effect = Exception("Test error")
        with pytest.raises(Exception) as excinfo:
            await server.list_mcp_tools()
        assert "Test error" in str(excinfo.value)

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
            server = MCPClient("https://example.com/api")
            result = await server.connect()

            # Verify results
            assert result == server
            assert server.is_connected is True
            assert server._mcp_tools == ["tool1", "tool2"]
            assert server._session is not None

            # Verify mocks were called correctly
            mock_sse_client.assert_called_once_with(
                "https://example.com/api", headers={}, timeout=None
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
            server = MCPClient("https://example.com/api")

            with pytest.raises(Exception) as excinfo:
                await server.connect()

            assert "Connection error" in str(excinfo.value)
            assert server.is_connected is False

    @pytest.mark.asyncio
    async def test_disconnect_explicit(self):
        r"""Test explicit disconnect method."""
        # Create server
        server = MCPClient("test_command")

        # Setup connected state
        server._connection_state = ConnectionState.CONNECTED
        # Assign an AsyncMock to _exit_stack to check its aclose method
        mock_exit_stack = AsyncMock()
        server._exit_stack = mock_exit_stack
        server._session = MagicMock()

        # Test disconnect
        await server.disconnect()

        # Verify results
        assert server.is_connected is False
        assert server._session is None
        # Assert that aclose was called on the original mock_exit_stack
        mock_exit_stack.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_without_connection(self):
        r"""Test explicit disconnect method without connection."""
        # Create server
        server = MCPClient("test_command")

        # Setup not connected state
        server._connection_state = ConnectionState.DISCONNECTED
        # Store the mock session to assert its identity
        initial_mock_session = MagicMock()
        server._session = initial_mock_session

        # Test disconnect
        await server.disconnect()

        # Verify results
        assert server.is_connected is False
        # Session should remain unchanged when not connected
        assert server._session is initial_mock_session


class TestMCPToolkit:
    r"""Test MCPToolkit class."""

    def test_init(self):
        r"""Test initialization of MCPToolkit."""
        # Test with servers list
        server1 = MCPClient("test_command1")
        server2 = MCPClient("test_command2")
        toolkit = MCPToolkit(servers=[server1, server2])

        assert toolkit.servers == [server1, server2]
        assert toolkit.is_connected is False

        # Test with both servers and config_path - should raise error now
        with pytest.raises(ValueError):
            MCPToolkit()  # No parameters provided

    def test_init_config_file_not_found(self):
        r"""Test from_config with non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = Path(temp_dir) / "non_existent.json"

            with pytest.raises(FileNotFoundError):
                MCPToolkit(config_path=str(non_existent_path))

    def test_init_config_invalid_json(self):
        r"""Test from_config with invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "invalid.json"
            config_path.write_text("{invalid json")

            with pytest.raises(ValueError) as excinfo:
                MCPToolkit(config_path=str(config_path))

            assert "Invalid JSON" in str(excinfo.value)

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
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "invalid_fields.json"

            # Missing command field
            config_data = {"mcpServers": {"server1": {"args": ["--arg1"]}}}
            config_path.write_text(json.dumps(config_data))

            with pytest.raises(ValueError) as excinfo:
                MCPToolkit(config_path=str(config_path))

            assert "must have either 'command' or 'url' field" in str(
                excinfo.value
            )

    def test_load_servers_from_config_invalid_structure(self):
        r"""Test _load_servers_from_config with invalid structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "invalid_structure.json"

            # mcpServers is not a dictionary
            config_data = {"mcpServers": "not a dictionary"}
            config_path.write_text(json.dumps(config_data))

            with pytest.raises(ValueError) as excinfo:
                MCPToolkit(config_path=str(config_path))

            assert "'mcpServers' must be a dictionary" in str(excinfo.value)

    def test_is_connected(self):
        r"""Test is_connected property."""
        toolkit = MCPToolkit(servers=[MCPClient("test_command")])
        assert toolkit.is_connected is False
        toolkit._connection_state = ConnectionState.CONNECTED
        # Still False because servers are not connected
        assert toolkit.is_connected is False

    @pytest.mark.asyncio
    async def test_connect(self):
        r"""Test explicit connect method."""
        # Create mock servers
        server1 = MCPClient("test_command1")
        server2 = MCPClient("test_command2")

        # Mock connect methods and is_connected properties
        server1.connect = AsyncMock(return_value=server1)
        server2.connect = AsyncMock(return_value=server2)

        # Mock is_connected property to return True after connect
        type(server1).is_connected = PropertyMock(return_value=True)
        type(server2).is_connected = PropertyMock(return_value=True)

        # Create toolkit with mock servers
        toolkit = MCPToolkit(servers=[server1, server2])

        # Test connect
        result = await toolkit.connect()

        # Verify results
        assert result == toolkit
        assert toolkit.is_connected is True
        for server_mock in [server1, server2]:
            server_mock.connect.assert_called_once()

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
        server1 = MCPClient("test_command1")
        server2 = MCPClient("test_command2")

        # First server connects successfully, second fails
        server1.connect = AsyncMock(return_value=server1)
        server2.connect = AsyncMock(side_effect=Exception("Connection error"))

        # Mock disconnect for rollback
        server1.disconnect = AsyncMock()

        # Create toolkit with mock servers
        toolkit = MCPToolkit(servers=[server1, server2])

        # Test connect with failure - should raise the exception
        with pytest.raises(Exception) as excinfo:
            await toolkit.connect()

        assert "Connection error" in str(excinfo.value)

        # Verify first server was connected
        server1.connect.assert_called_once()
        # Verify second server was attempted
        server2.connect.assert_called_once()
        # Verify rollback was called
        server1.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        r"""Test explicit disconnect method."""
        # Create mock servers
        server1 = MCPClient("test_command1")
        server2 = MCPClient("test_command2")

        # Mock disconnect methods
        server1.disconnect = AsyncMock()
        server2.disconnect = AsyncMock()

        # Create toolkit with mock servers
        toolkit = MCPToolkit(servers=[server1, server2])

        # Setup connected state
        toolkit._connection_state = ConnectionState.CONNECTED

        # Test disconnect
        await toolkit.disconnect()

        # Verify results
        assert toolkit.is_connected is False
        server1.disconnect.assert_called_once()
        server2.disconnect.assert_called_once()

        # Test disconnecting when not connected
        server1.disconnect.reset_mock()
        server2.disconnect.reset_mock()

        await toolkit.disconnect()

        # Verify no actions taken when not connected
        server1.disconnect.assert_not_called()
        server2.disconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_connect_to_real_mcp_server(self):
        """Test connecting to MCP servers with mixed stdio and HTTP configs."""
        config_data = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem@2025.1.14",
                        ".",
                    ],
                },
                "edgeone-pages-mcp-server": {
                    "command": "npx",
                    "args": ["edgeone-pages-mcp"],
                },
                "http-server": {
                    "url": "https://api.example.com/mcp",
                    "mode": "streamable-http",
                    "headers": {
                        "Authorization": "Bearer test-token",
                        "Content-Type": "application/json",
                    },
                    "timeout": 30,
                },
            }
        }

        # Create toolkit to test configuration parsing
        toolkit = MCPToolkit(config_dict=config_data)

        # Verify servers were created correctly
        assert len(toolkit.servers) == 3
        assert toolkit.servers[0].command_or_url == "npx"
        filesystem_args = [
            "-y",
            "@modelcontextprotocol/server-filesystem@2025.1.14",
            ".",
        ]
        assert toolkit.servers[0].args == filesystem_args
        assert toolkit.servers[1].command_or_url == "npx"
        assert toolkit.servers[1].args == ["edgeone-pages-mcp"]

        # Check HTTP server configuration
        http_server = toolkit.servers[2]
        assert http_server.command_or_url == "https://api.example.com/mcp"
        assert http_server.mode == "streamable-http"
        auth_header = http_server.headers["Authorization"]
        assert auth_header == "Bearer test-token"
        assert http_server.timeout == 30

        # Mock the connections to avoid real network/process calls
        stdio_patch = "mcp.client.stdio.stdio_client"
        http_patch = "mcp.client.streamable_http.streamablehttp_client"
        session_patch = "mcp.client.session.ClientSession"

        with (
            patch(stdio_patch) as mock_stdio,
            patch(http_patch) as mock_http,
            patch(session_patch) as mock_session,
        ):
            # Setup mocks for stdio connections
            mock_stdio.return_value.__aenter__.return_value = (
                AsyncMock(),
                AsyncMock(),
            )

            # Setup mocks for HTTP connection
            mock_http.return_value.__aenter__.return_value = (
                AsyncMock(),
                AsyncMock(),
            )

            # Setup session mock
            mock_session_instance = AsyncMock()
            session_context = mock_session.return_value.__aenter__
            session_context.return_value = mock_session_instance

            # Mock list_tools result
            list_tools_result = MagicMock()
            list_tools_result.tools = []
            mock_session_instance.list_tools.return_value = list_tools_result

            # Test connection
            await toolkit.connect()
            assert toolkit.is_connected is True

            # Verify HTTP client was called with correct parameters
            mock_http.assert_called_once()
            call_args = mock_http.call_args
            assert call_args[0][0] == "https://api.example.com/mcp"
            auth_header_check = call_args[1]["headers"]["Authorization"]
            assert auth_header_check == "Bearer test-token"

            await toolkit.disconnect()
            assert toolkit.is_connected is False

        print("✅ Test_connect_to_real_mcp_server passed")
