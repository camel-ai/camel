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
Tests for the unified MCP client.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import mcp.types as types
import pytest

from camel.utils.mcp_client import (
    MCPClient,
    ServerConfig,
    TransportType,
    create_mcp_client,
    create_mcp_client_from_config_file,
)


class TestTransportType:
    """Test TransportType enum."""

    def test_transport_type_values(self):
        """Test that TransportType has expected values."""
        assert TransportType.STDIO == "stdio"
        assert TransportType.SSE == "sse"
        assert TransportType.STREAMABLE_HTTP == "streamable_http"
        assert TransportType.WEBSOCKET == "websocket"


class TestServerConfig:
    """Test ServerConfig validation and transport detection."""

    def test_stdio_config_valid(self):
        """Test valid STDIO configuration."""
        config = ServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
        )
        assert config.command == "npx"
        assert config.args == [
            "-y",
            "@modelcontextprotocol/server-filesystem",
            "/path",
        ]
        assert config.transport_type == TransportType.STDIO

    def test_http_config_valid(self):
        """Test valid HTTP configuration."""
        config = ServerConfig(
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer token"},
        )
        assert config.url == "https://api.example.com/mcp"
        assert config.headers == {"Authorization": "Bearer token"}
        assert config.transport_type == TransportType.STREAMABLE_HTTP

    def test_http_config_prefer_sse(self):
        """Test HTTP configuration with SSE preference."""
        config = ServerConfig(
            url="https://api.example.com/mcp", prefer_sse=True
        )
        assert config.transport_type == TransportType.SSE

    def test_websocket_config_valid(self):
        """Test valid WebSocket configuration."""
        config = ServerConfig(url="ws://localhost:8080/mcp")
        assert config.url == "ws://localhost:8080/mcp"
        assert config.transport_type == TransportType.WEBSOCKET

    def test_websocket_secure_config_valid(self):
        """Test valid secure WebSocket configuration."""
        config = ServerConfig(url="wss://api.example.com/mcp")
        assert config.url == "wss://api.example.com/mcp"
        assert config.transport_type == TransportType.WEBSOCKET

    def test_config_no_command_or_url(self):
        """Test that config without command or url raises ValueError."""
        with pytest.raises(
            ValueError, match="Either 'command'.*or 'url'.*must be provided"
        ):
            ServerConfig()

    def test_config_both_command_and_url(self):
        """Test that config with both command and url raises ValueError."""
        with pytest.raises(
            ValueError, match="Cannot specify both 'command' and 'url'"
        ):
            ServerConfig(command="npx", url="https://api.example.com/mcp")

    def test_unsupported_url_scheme(self):
        """Test that unsupported URL scheme raises ValueError."""
        config = ServerConfig(url="ftp://example.com/mcp")
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            _ = config.transport_type

    def test_config_defaults(self):
        """Test default configuration values."""
        config = ServerConfig(command="test")
        assert config.timeout == 30.0
        assert config.encoding == "utf-8"
        assert config.sse_read_timeout == 300.0
        assert config.terminate_on_close is True
        assert config.prefer_sse is False

    def test_config_with_optional_stdio_params(self):
        """Test STDIO config with optional parameters."""
        config = ServerConfig(
            command="python",
            args=["server.py"],
            env={"VAR": "value"},
            cwd="/tmp",
            encoding="utf-16",
        )
        assert config.command == "python"
        assert config.args == ["server.py"]
        assert config.env == {"VAR": "value"}
        assert config.cwd == "/tmp"
        assert config.encoding == "utf-16"


class TestMCPClient:
    """Test MCPClient class."""

    def test_init_with_server_config(self):
        """Test MCPClient initialization with ServerConfig."""
        config = ServerConfig(command="npx", args=["test"])
        client = MCPClient(config)
        assert client.config == config
        assert client.transport_type == TransportType.STDIO
        assert client.session is None
        assert not client.is_connected()

    def test_init_with_dict_config(self):
        """Test MCPClient initialization with dict config."""
        config_dict = {"command": "npx", "args": ["test"]}
        client = MCPClient(config_dict)
        assert isinstance(client.config, ServerConfig)
        assert client.config.command == "npx"
        assert client.config.args == ["test"]

    def test_init_with_client_info(self):
        """Test MCPClient initialization with client info."""
        config = ServerConfig(command="npx", args=["test"])
        client_info = types.Implementation(name="test-client", version="1.0.0")
        client = MCPClient(config, client_info=client_info)
        assert client.client_info == client_info

    def test_init_with_invalid_config(self):
        """Test MCPClient initialization with invalid config."""
        with pytest.raises(ValueError):
            MCPClient({})  # No command or url

    def test_transport_type_property(self):
        """Test that transport_type property works correctly."""
        # STDIO
        client1 = MCPClient({"command": "test"})
        assert client1.transport_type == TransportType.STDIO

        # HTTP
        client2 = MCPClient({"url": "https://example.com"})
        assert client2.transport_type == TransportType.STREAMABLE_HTTP

        # WebSocket
        client3 = MCPClient({"url": "ws://example.com"})
        assert client3.transport_type == TransportType.WEBSOCKET

        # SSE
        client4 = MCPClient({"url": "https://example.com", "prefer_sse": True})
        assert client4.transport_type == TransportType.SSE

    def test_session_properties(self):
        """Test session property and is_connected method."""
        config = ServerConfig(command="test")
        client = MCPClient(config)

        # Initially not connected
        assert client.session is None
        assert not client.is_connected()

        # Simulate connection by setting session
        mock_session = MagicMock()
        client._session = mock_session

        assert client.session == mock_session
        assert client.is_connected()

        # Clear session
        client._session = None
        assert client.session is None
        assert not client.is_connected()


class TestCreateMCPClient:
    """Test create_mcp_client factory function."""

    def test_create_from_dict(self):
        """Test creating client from dict config."""
        config_dict = {"command": "npx", "args": ["test"]}
        client = create_mcp_client(config_dict)
        assert isinstance(client, MCPClient)
        assert client.config.command == "npx"
        assert client.config.args == ["test"]

    def test_create_from_server_config(self):
        """Test creating client from ServerConfig object."""
        config = ServerConfig(command="npx", args=["test"])
        client = create_mcp_client(config)
        assert isinstance(client, MCPClient)
        assert client.config == config

    def test_create_with_client_info(self):
        """Test creating client with client_info parameter."""
        config_dict = {"command": "npx", "args": ["test"]}
        client_info = types.Implementation(name="test", version="1.0")
        client = create_mcp_client(config_dict, client_info=client_info)
        assert client.client_info == client_info


class TestCreateMCPClientFromConfigFile:
    """Test create_mcp_client_from_config_file function."""

    def test_create_from_config_file(self):
        """Test creating client from config file."""
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
            client = create_mcp_client_from_config_file(
                config_path, "filesystem"
            )
            assert isinstance(client, MCPClient)
            assert client.config.command == "npx"
            assert client.config.args == [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "/path",
            ]
            assert client.transport_type == TransportType.STDIO
        finally:
            Path(config_path).unlink()

    def test_create_from_config_file_http_server(self):
        """Test creating HTTP client from config file."""
        config_data = {
            "mcpServers": {
                "remote-server": {
                    "url": "https://api.example.com/mcp",
                    "headers": {"Authorization": "Bearer token"},
                }
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            client = create_mcp_client_from_config_file(
                config_path, "remote-server"
            )
            assert isinstance(client, MCPClient)
            assert client.config.url == "https://api.example.com/mcp"
            assert client.config.headers == {"Authorization": "Bearer token"}
            assert client.transport_type == TransportType.STREAMABLE_HTTP
        finally:
            Path(config_path).unlink()

    def test_create_from_config_file_server_not_found(self):
        """Test error when server not found in config file."""
        config_data = {
            "mcpServers": {"filesystem": {"command": "npx", "args": ["test"]}}
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(
                ValueError, match="Server 'nonexistent' not found"
            ):
                create_mcp_client_from_config_file(config_path, "nonexistent")
        finally:
            Path(config_path).unlink()

    def test_create_from_config_file_no_mcp_servers(self):
        """Test config file without mcpServers section."""
        config_data = {"other": "data"}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ValueError, match="Server 'test' not found"):
                create_mcp_client_from_config_file(config_path, "test")
        finally:
            Path(config_path).unlink()

    def test_create_from_config_file_with_kwargs(self):
        """Test creating client from config file with additional kwargs."""
        config_data = {
            "mcpServers": {"test": {"command": "npx", "args": ["test"]}}
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            client_info = types.Implementation(name="test", version="1.0")
            client = create_mcp_client_from_config_file(
                config_path, "test", client_info=client_info
            )
            assert client.client_info == client_info
        finally:
            Path(config_path).unlink()

    def test_create_from_config_file_invalid_json(self):
        """Test creating client from invalid JSON file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("invalid json content")
            config_path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                create_mcp_client_from_config_file(config_path, "test")
        finally:
            Path(config_path).unlink()


class TestIntegration:
    """Integration tests for the MCP client."""

    def test_stdio_server_configuration(self):
        """Test complete STDIO server configuration."""
        client = create_mcp_client(
            {
                "command": "python",
                "args": ["-m", "server"],
                "env": {"DEBUG": "1"},
                "cwd": "/tmp",
                "timeout": 60.0,
                "encoding": "utf-8",
            }
        )

        assert client.transport_type == TransportType.STDIO
        assert client.config.command == "python"
        assert client.config.args == ["-m", "server"]
        assert client.config.env == {"DEBUG": "1"}
        assert client.config.cwd == "/tmp"
        assert client.config.timeout == 60.0
        assert client.config.encoding == "utf-8"

    def test_http_server_configuration(self):
        """Test complete HTTP server configuration."""
        client = create_mcp_client(
            {
                "url": "https://api.example.com/mcp",
                "headers": {
                    "Authorization": "Bearer token",
                    "User-Agent": "test-client/1.0",
                },
                "timeout": 45.0,
                "sse_read_timeout": 600.0,
                "terminate_on_close": False,
            }
        )

        assert client.transport_type == TransportType.STREAMABLE_HTTP
        assert client.config.url == "https://api.example.com/mcp"
        assert client.config.headers["Authorization"] == "Bearer token"
        assert client.config.headers["User-Agent"] == "test-client/1.0"
        assert client.config.timeout == 45.0
        assert client.config.sse_read_timeout == 600.0
        assert client.config.terminate_on_close is False

    def test_websocket_server_configuration(self):
        """Test complete WebSocket server configuration."""
        client = create_mcp_client(
            {"url": "wss://api.example.com/mcp", "timeout": 30.0}
        )

        assert client.transport_type == TransportType.WEBSOCKET
        assert client.config.url == "wss://api.example.com/mcp"
        assert client.config.timeout == 30.0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_config_with_path_object(self):
        """Test config with Path object for cwd."""
        config = ServerConfig(command="python", cwd=Path("/tmp"))
        assert config.cwd == Path("/tmp")
        assert config.transport_type == TransportType.STDIO

    def test_config_with_empty_headers(self):
        """Test config with empty headers dict."""
        config = ServerConfig(url="https://api.example.com/mcp", headers={})
        assert config.headers == {}
        assert config.transport_type == TransportType.STREAMABLE_HTTP

    def test_config_edge_case_url_schemes(self):
        """Test various URL scheme edge cases."""
        # Test uppercase schemes
        config1 = ServerConfig(url="HTTP://api.example.com/mcp")
        # Note: This will actually fail because startswith() is case-sensitive
        # This is expected behavior - URLs should use lowercase schemes
        with pytest.raises(ValueError, match="Unsupported URL scheme"):
            _ = config1.transport_type

        # Test URL with port
        config2 = ServerConfig(url="https://api.example.com:8443/mcp")
        assert config2.transport_type == TransportType.STREAMABLE_HTTP

        # Test WebSocket with port
        config3 = ServerConfig(url="ws://localhost:8080/mcp")
        assert config3.transport_type == TransportType.WEBSOCKET

    def test_client_session_property_when_not_connected(self):
        """Test session property when not connected."""
        config = ServerConfig(command="test")
        client = MCPClient(config)

        assert client.session is None
        assert not client.is_connected()

    def test_invalid_transport_detection(self):
        """Test error conditions in transport type detection."""
        # Test missing command and URL - this should be caught by validation
        with pytest.raises(ValueError):
            ServerConfig()

    def test_config_validation_edge_cases(self):
        """Test additional config validation edge cases."""
        # Test that we can't have both command and URL
        with pytest.raises(ValueError, match="Cannot specify both"):
            ServerConfig(command="test", url="https://example.com")

        # Test empty command string - this should fail validation since empty string is falsy # noqa: E501
        with pytest.raises(
            ValueError, match="Either 'command'.*or 'url'.*must be provided"
        ):
            ServerConfig(command="")

        # Test empty URL string - this should also fail validation
        with pytest.raises(
            ValueError, match="Either 'command'.*or 'url'.*must be provided"
        ):
            ServerConfig(url="")

    def test_client_initialization_variations(self):
        """Test different ways to initialize the client."""
        # Test with minimal config
        client1 = MCPClient({"command": "test"})
        assert client1.config.command == "test"

        # Test with comprehensive config
        client2 = MCPClient(
            {
                "url": "wss://api.example.com/mcp",
                "timeout": 120.0,
                "sse_read_timeout": 600.0,
            }
        )
        assert client2.config.url == "wss://api.example.com/mcp"
        assert client2.config.timeout == 120.0

        # Test with client_info
        client_info = types.Implementation(name="test", version="2.0")
        client3 = MCPClient({"command": "test"}, client_info=client_info)
        assert client3.client_info.name == "test"
        assert client3.client_info.version == "2.0"


if __name__ == "__main__":
    pytest.main([__file__])
