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
"""
Tests for the refactored MCPToolkit.
"""

import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.toolkits.mcp_toolkit import (
    MCPConnectionError,
    MCPToolError,
    MCPToolkit,
)
from camel.utils.mcp_client import MCPClient


class TestMCPToolkit:
    """Test MCPToolkit class."""

    def test_init_with_clients(self):
        """Test MCPToolkit initialization with client instances."""
        mock_client = MagicMock(spec=MCPClient)
        toolkit = MCPToolkit(clients=[mock_client])
        assert len(toolkit.clients) == 1
        assert toolkit.clients[0] == mock_client
        assert not toolkit.is_connected

    def test_init_with_config_dict(self):
        """Test MCPToolkit initialization with config dictionary."""
        config_dict = {
            "mcpServers": {"test_server": {"command": "npx", "args": ["test"]}}
        }

        toolkit = MCPToolkit(config_dict=config_dict)
        assert len(toolkit.clients) == 1
        assert toolkit.clients[0].config.command == "npx"

    def test_init_with_config_file(self):
        """Test MCPToolkit initialization with config file."""
        config_data = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        "/path",
                    ],
                },
                "remote-server": {
                    "url": "https://api.example.com/mcp",
                    "headers": {"Authorization": "Bearer token"},
                },
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            toolkit = MCPToolkit(config_path=config_path)
            assert len(toolkit.clients) == 2

            # Check first client (filesystem)
            assert toolkit.clients[0].config.command == "npx"
            expected_args = [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "/path",
            ]
            assert toolkit.clients[0].config.args == expected_args

            # Check second client (remote-server)
            url = "https://api.example.com/mcp"
            assert toolkit.clients[1].config.url == url
            expected_headers = {"Authorization": "Bearer token"}
            assert toolkit.clients[1].config.headers == expected_headers

        finally:
            Path(config_path).unlink()

    def test_init_no_sources_error(self):
        """Test error when no configuration sources provided."""
        expected_msg = (
            "At least one of clients, config_path, or "
            "config_dict must be provided"
        )
        with pytest.raises(ValueError, match=expected_msg):
            MCPToolkit()

    def test_init_invalid_config_dict(self):
        """Test error with invalid config dictionary."""
        config_dict = {"invalid": "config"}

        expected_msg = "No valid MCP clients could be created"
        with pytest.raises(ValueError, match=expected_msg):
            MCPToolkit(config_dict=config_dict)

    def test_init_file_not_found(self):
        """Test error when config file not found."""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            MCPToolkit(config_path="/nonexistent/config.json")

    def test_init_invalid_json_file(self):
        """Test error with invalid JSON file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("invalid json content")
            config_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid JSON"):
                MCPToolkit(config_path=config_path)
        finally:
            Path(config_path).unlink()

    def test_multiple_sources_combined(self):
        """Test that multiple sources are combined."""
        mock_client = MagicMock(spec=MCPClient)
        config_dict = {
            "mcpServers": {"test_server": {"command": "npx", "args": ["test"]}}
        }

        toolkit = MCPToolkit(clients=[mock_client], config_dict=config_dict)

        assert len(toolkit.clients) == 2
        assert toolkit.clients[0] == mock_client
        assert toolkit.clients[1].config.command == "npx"


class TestMCPToolkitConnectionManagement:
    """Test connection management in MCPToolkit."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to all clients."""
        # Create mock clients with properly mocked async context managers
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        # Create proper async context manager mocks
        @asynccontextmanager
        async def mock_connect1():
            yield MagicMock()  # Mock session

        @asynccontextmanager
        async def mock_connect2():
            yield MagicMock()  # Mock session

        mock_client1.connect = mock_connect1
        mock_client2.connect = mock_connect2
        mock_client1.is_connected.return_value = True
        mock_client2.is_connected.return_value = True

        toolkit = MCPToolkit(clients=[mock_client1, mock_client2])

        await toolkit.connect()

        assert toolkit._is_connected
        assert toolkit.is_connected

    @pytest.mark.asyncio
    async def test_connect_failure_rollback(self):
        """Test rollback when connection fails."""
        # Create mock clients
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        # Set up the first client as a successful async context manager
        mock_client1.__aenter__.return_value = mock_client1
        mock_client1.__aexit__.return_value = None

        # Set up the second client to raise an exception during __aenter__
        mock_client2.__aenter__.side_effect = Exception("Connection failed")

        toolkit = MCPToolkit(clients=[mock_client1, mock_client2])

        expected_msg = "Failed to connect to client 2"
        with pytest.raises(MCPConnectionError, match=expected_msg):
            await toolkit.connect()

        assert not toolkit._is_connected
        # Verify the first client's __aexit__ was called for cleanup
        mock_client1.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_already_connected(self):
        """Test connecting when already connected."""
        mock_client = MagicMock()

        @asynccontextmanager
        async def mock_connect():
            yield MagicMock()  # Mock session

        mock_client.connect = mock_connect

        toolkit = MCPToolkit(clients=[mock_client])
        toolkit._is_connected = True

        result = await toolkit.connect()

        assert result is toolkit

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """Test successful disconnection from all clients."""
        mock_client1 = MagicMock()
        mock_client1.disconnect = AsyncMock()

        mock_client2 = MagicMock()
        mock_client2.disconnect = AsyncMock()

        toolkit = MCPToolkit(clients=[mock_client1, mock_client2])
        toolkit._is_connected = True

        await toolkit.disconnect()

        assert not toolkit._is_connected

    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self):
        """Test disconnect when not connected."""
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()

        toolkit = MCPToolkit(clients=[mock_client])

        await toolkit.disconnect()

        # Should be a no-op when not connected
        assert not toolkit._is_connected

    @pytest.mark.asyncio
    async def test_disconnect_with_errors(self):
        """Test disconnect with some clients failing."""
        mock_client1 = MagicMock()
        disconnect_exc = Exception("Disconnect failed")
        mock_client1.disconnect = AsyncMock(side_effect=disconnect_exc)

        mock_client2 = MagicMock()
        mock_client2.disconnect = AsyncMock()

        toolkit = MCPToolkit(clients=[mock_client1, mock_client2])
        toolkit._is_connected = True

        await toolkit.disconnect()

        assert not toolkit._is_connected

    def test_is_connected_property(self):
        """Test is_connected property."""
        mock_client1 = MagicMock()
        mock_client1.is_connected.return_value = True

        mock_client2 = MagicMock()
        mock_client2.is_connected.return_value = True

        toolkit = MCPToolkit(clients=[mock_client1, mock_client2])

        # Not connected initially
        assert not toolkit.is_connected

        # Mark as connected
        toolkit._is_connected = True
        assert toolkit.is_connected

        # One client disconnected
        mock_client2.is_connected.return_value = False
        assert not toolkit.is_connected

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        mock_client = MagicMock()

        @asynccontextmanager
        async def mock_connect():
            yield MagicMock()  # Mock session

        mock_client.connect = mock_connect
        mock_client.is_connected.return_value = True

        toolkit = MCPToolkit(clients=[mock_client])

        async with toolkit as connected_toolkit:
            assert connected_toolkit is toolkit


class TestMCPToolkitFactoryMethods:
    """Test factory methods for MCPToolkit."""

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful creation with factory method."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.is_connected.return_value = True

        # Mock the toolkit creation
        with patch.object(MCPToolkit, '__init__', return_value=None):
            with patch.object(MCPToolkit, 'connect', return_value=None):
                toolkit = MCPToolkit.__new__(MCPToolkit)
                toolkit.clients = [mock_client]
                toolkit._is_connected = False

                # Mock the connect method
                async def mock_connect():
                    toolkit._is_connected = True
                    return toolkit

                toolkit.connect = mock_connect

                patch_path = 'camel.toolkits.mcp_toolkit.MCPToolkit.__new__'
                with patch(patch_path, return_value=toolkit):
                    result = await MCPToolkit.create(clients=[mock_client])

                    assert result is toolkit
                    assert toolkit._is_connected

    @pytest.mark.asyncio
    async def test_create_failure_cleanup(self):
        """Test cleanup on creation failure."""
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()

        with patch.object(MCPToolkit, '__init__', return_value=None):
            toolkit = MCPToolkit.__new__(MCPToolkit)
            toolkit.clients = [mock_client]
            toolkit._is_connected = False

            async def failing_connect():
                raise Exception("Connection failed")

            toolkit.connect = failing_connect
            toolkit.disconnect = AsyncMock()

            patch_path = 'camel.toolkits.mcp_toolkit.MCPToolkit.__new__'
            with patch(patch_path, return_value=toolkit):
                expected_msg = "Failed to initialize MCPToolkit"
                with pytest.raises(MCPConnectionError, match=expected_msg):
                    await MCPToolkit.create(clients=[mock_client])


class TestMCPToolkitTools:
    """Test tool management in MCPToolkit."""

    def _create_test_toolkit(self, clients):
        """Helper method to create a toolkit with mock clients."""
        # Mock the parent class initialization to avoid the object.__new__
        # error
        with patch.object(MCPToolkit, '__init__', return_value=None):
            toolkit = MCPToolkit.__new__(MCPToolkit)
            toolkit.clients = clients
            toolkit._is_connected = True
            toolkit._exit_stack = None
            return toolkit

    def test_get_tools(self):
        """Test getting tools from all clients."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        mock_tool1 = MagicMock()
        mock_tool2 = MagicMock()
        mock_tool3 = MagicMock()

        mock_client1.get_tools.return_value = [mock_tool1, mock_tool2]
        mock_client2.get_tools.return_value = [mock_tool3]
        mock_client1.is_connected.return_value = True
        mock_client2.is_connected.return_value = True

        toolkit = self._create_test_toolkit([mock_client1, mock_client2])

        tools = toolkit.get_tools()

        assert len(tools) == 3
        assert tools == [mock_tool1, mock_tool2, mock_tool3]

    def test_get_tools_not_connected_warning(self):
        """Test warning when getting tools while not connected."""
        mock_client = MagicMock()
        mock_client.get_tools.return_value = []

        toolkit = self._create_test_toolkit([mock_client])
        # Set not connected for this test
        toolkit._is_connected = False

        with patch('camel.toolkits.mcp_toolkit.logger') as mock_logger:
            toolkit.get_tools()

            expected_msg = (
                "MCPToolkit is not connected. "
                "Tools may not be available until connected."
            )
            mock_logger.warning.assert_called_with(expected_msg)

    def test_get_tools_client_error(self):
        """Test handling client errors when getting tools."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        mock_tool = MagicMock()

        mock_client1.get_tools.side_effect = Exception("Client error")
        mock_client2.get_tools.return_value = [mock_tool]
        mock_client1.is_connected.return_value = True
        mock_client2.is_connected.return_value = True

        toolkit = self._create_test_toolkit([mock_client1, mock_client2])

        with patch('camel.toolkits.mcp_toolkit.logger') as mock_logger:
            tools = toolkit.get_tools()

            assert len(tools) == 1
            assert tools[0] == mock_tool
            expected_msg = "Failed to get tools from client 1: Client error"
            mock_logger.error.assert_called_with(expected_msg)

    def test_get_text_tools(self):
        """Test getting text descriptions of tools."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        mock_client1.get_text_tools.return_value = "Tool 1\nTool 2"
        mock_client2.get_text_tools.return_value = "Tool 3"
        mock_client1.is_connected.return_value = True
        mock_client2.is_connected.return_value = True

        toolkit = self._create_test_toolkit([mock_client1, mock_client2])

        text_tools = toolkit.get_text_tools()

        expected = (
            "=== Client 1 Tools ===\nTool 1\nTool 2\n\n"
            "=== Client 2 Tools ===\nTool 3"
        )
        assert text_tools == expected

    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        """Test successful tool call."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        mock_tool1 = MagicMock()
        mock_tool1.func.__name__ = "tool1"
        mock_tool2 = MagicMock()
        mock_tool2.func.__name__ = "tool2"

        mock_client1.get_tools.return_value = [mock_tool1]
        mock_client2.get_tools.return_value = [mock_tool2]
        mock_client2.call_tool = AsyncMock(return_value="tool result")
        mock_client1.is_connected.return_value = True
        mock_client2.is_connected.return_value = True

        toolkit = self._create_test_toolkit([mock_client1, mock_client2])

        result = await toolkit.call_tool("tool2", {"arg": "value"})

        assert result == "tool result"
        expected_args = ("tool2", {"arg": "value"})
        mock_client2.call_tool.assert_called_once_with(*expected_args)

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        """Test calling tool when not connected."""
        mock_client = MagicMock()

        toolkit = self._create_test_toolkit([mock_client])
        # Set not connected for this test
        toolkit._is_connected = False

        expected_msg = "MCPToolkit is not connected"
        with pytest.raises(MCPConnectionError, match=expected_msg):
            await toolkit.call_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self):
        """Test calling tool that doesn't exist."""
        mock_client = MagicMock()

        mock_tool = MagicMock()
        mock_tool.func.__name__ = "other_tool"
        mock_client.get_tools.return_value = [mock_tool]
        mock_client.is_connected.return_value = True

        toolkit = self._create_test_toolkit([mock_client])

        expected_msg = "Tool 'nonexistent_tool' not found in any client"
        with pytest.raises(MCPToolError, match=expected_msg):
            await toolkit.call_tool("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_call_tool_all_clients_fail(self):
        """Test tool call when all clients fail."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        mock_tool = MagicMock()
        mock_tool.func.__name__ = "test_tool"

        mock_client1.get_tools.return_value = [mock_tool]
        mock_client2.get_tools.return_value = [mock_tool]

        client1_exc = Exception("Client 1 error")
        client2_exc = Exception("Client 2 error")
        mock_client1.call_tool = AsyncMock(side_effect=client1_exc)
        mock_client2.call_tool = AsyncMock(side_effect=client2_exc)
        mock_client1.is_connected.return_value = True
        mock_client2.is_connected.return_value = True

        toolkit = self._create_test_toolkit([mock_client1, mock_client2])

        expected_msg = "Tool 'test_tool' failed on all clients"
        with pytest.raises(MCPToolError, match=expected_msg):
            await toolkit.call_tool("test_tool", {})

    def test_list_available_tools(self):
        """Test listing available tools organized by client."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        mock_tool1 = MagicMock()
        mock_tool1.func.__name__ = "tool1"
        mock_tool2 = MagicMock()
        mock_tool2.func.__name__ = "tool2"
        mock_tool3 = MagicMock()
        mock_tool3.func.__name__ = "tool3"

        mock_client1.get_tools.return_value = [mock_tool1, mock_tool2]
        mock_client2.get_tools.return_value = [mock_tool3]

        toolkit = self._create_test_toolkit([mock_client1, mock_client2])

        available_tools = toolkit.list_available_tools()

        expected = {"client_1": ["tool1", "tool2"], "client_2": ["tool3"]}
        assert available_tools == expected

    def test_list_available_tools_with_errors(self):
        """Test listing tools when some clients have errors."""
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        mock_tool = MagicMock()
        mock_tool.func.__name__ = "tool1"

        mock_client1.get_tools.side_effect = Exception("Client error")
        mock_client2.get_tools.return_value = [mock_tool]

        toolkit = self._create_test_toolkit([mock_client1, mock_client2])

        with patch('camel.toolkits.mcp_toolkit.logger') as mock_logger:
            available_tools = toolkit.list_available_tools()

            expected = {"client_1": [], "client_2": ["tool1"]}
            assert available_tools == expected
            expected_msg = "Failed to list tools from client 1: Client error"
            mock_logger.error.assert_called_with(expected_msg)


if __name__ == "__main__":
    pytest.main([__file__])
