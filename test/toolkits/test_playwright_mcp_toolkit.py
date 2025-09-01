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
Tests for the refactored PlaywrightMCPToolkit.

This test suite verifies that the PlaywrightMCPToolkit works correctly
after being refactored to inherit directly from MCPToolkit instead of
using composition with an internal _mcp_toolkit instance.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.toolkits.playwright_mcp_toolkit import PlaywrightMCPToolkit
from camel.toolkits.mcp_toolkit import MCPToolkit
from camel.utils.mcp_client import MCPClient


class TestPlaywrightMCPToolkit:
    """Test suite for PlaywrightMCPToolkit."""

    def test_inheritance_structure(self):
        """Test that PlaywrightMCPToolkit properly inherits from MCPToolkit."""
        toolkit = PlaywrightMCPToolkit()
        
        # Verify inheritance hierarchy
        assert isinstance(toolkit, MCPToolkit)
        assert isinstance(toolkit, PlaywrightMCPToolkit)
        
        # Verify method inheritance
        assert hasattr(toolkit, 'connect')
        assert hasattr(toolkit, 'disconnect')
        assert hasattr(toolkit, 'get_tools')
        assert hasattr(toolkit, 'is_connected')

    def test_init_with_default_config(self):
        """Test PlaywrightMCPToolkit initialization with default configuration."""
        toolkit = PlaywrightMCPToolkit()
        
        # Verify that clients are created from config
        assert len(toolkit.clients) == 1
        assert isinstance(toolkit.clients[0], MCPClient)
        
        # Verify default configuration
        client_config = toolkit.clients[0].config
        assert client_config.command == "npx"
        assert "@playwright/mcp@latest" in client_config.args
        
        # Verify initial state
        assert not toolkit.is_connected

    def test_init_with_custom_timeout(self):
        """Test PlaywrightMCPToolkit initialization with custom timeout."""
        custom_timeout = 45.0
        toolkit = PlaywrightMCPToolkit(timeout=custom_timeout)
        
        # Verify timeout is set correctly
        assert toolkit.timeout == custom_timeout
        assert len(toolkit.clients) == 1

    def test_init_with_additional_args(self):
        """Test PlaywrightMCPToolkit initialization with additional arguments."""
        additional_args = ["--debug", "--headless=false"]
        toolkit = PlaywrightMCPToolkit(additional_args=additional_args)
        
        # Verify additional arguments are included
        client_config = toolkit.clients[0].config
        assert all(arg in client_config.args for arg in additional_args)
        assert "@playwright/mcp@latest" in client_config.args

    def test_init_with_timeout_and_args(self):
        """Test PlaywrightMCPToolkit initialization with both timeout and additional args."""
        custom_timeout = 60.0
        additional_args = ["--debug"]
        
        toolkit = PlaywrightMCPToolkit(
            timeout=custom_timeout,
            additional_args=additional_args
        )
        
        # Verify both settings
        assert toolkit.timeout == custom_timeout
        client_config = toolkit.clients[0].config
        assert "--debug" in client_config.args
        assert "@playwright/mcp@latest" in client_config.args

    def test_config_dict_structure(self):
        """Test that the internal config dictionary is structured correctly."""
        additional_args = ["--custom-flag"]
        toolkit = PlaywrightMCPToolkit(additional_args=additional_args)
        
        # Verify config structure through the created client
        client = toolkit.clients[0]
        config = client.config
        
        assert config.command == "npx"
        expected_args = ["@playwright/mcp@latest", "--custom-flag"]
        assert config.args == expected_args

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test PlaywrightMCPToolkit as async context manager."""
        with patch.object(MCPToolkit, 'connect', new_callable=AsyncMock) as mock_connect, \
             patch.object(MCPToolkit, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
            
            toolkit = PlaywrightMCPToolkit()
            
            async with toolkit:
                # Verify connect was called
                mock_connect.assert_called_once()
                
            # Verify disconnect was called on exit
            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_explicit_connect_disconnect(self):
        """Test explicit connect and disconnect methods."""
        with patch.object(MCPToolkit, 'connect', new_callable=AsyncMock) as mock_connect, \
             patch.object(MCPToolkit, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
            
            toolkit = PlaywrightMCPToolkit()
            
            # Test explicit connect
            await toolkit.connect()
            mock_connect.assert_called_once()
            
            # Test explicit disconnect
            await toolkit.disconnect()
            mock_disconnect.assert_called_once()

    def test_sync_context_manager(self):
        """Test PlaywrightMCPToolkit as sync context manager."""
        with patch.object(MCPToolkit, 'connect_sync') as mock_connect_sync, \
             patch.object(MCPToolkit, 'disconnect_sync') as mock_disconnect_sync:
            
            toolkit = PlaywrightMCPToolkit()
            
            with toolkit:
                # Verify sync connect was called
                mock_connect_sync.assert_called_once()
                
            # Verify sync disconnect was called on exit
            mock_disconnect_sync.assert_called_once()

    def test_get_tools_inheritance(self):
        """Test that get_tools method is properly inherited from MCPToolkit."""
        with patch.object(MCPToolkit, 'get_tools') as mock_get_tools:
            mock_tools = [MagicMock(), MagicMock()]
            mock_get_tools.return_value = mock_tools
            
            toolkit = PlaywrightMCPToolkit()
            tools = toolkit.get_tools()
            
            # Verify the method was called and returns expected result
            mock_get_tools.assert_called_once()
            assert tools == mock_tools

    def test_is_connected_property(self):
        """Test that is_connected property is properly inherited from MCPToolkit."""
        with patch.object(MCPToolkit, 'is_connected', new_callable=lambda: property(lambda self: True)):
            toolkit = PlaywrightMCPToolkit()
            assert hasattr(toolkit, 'is_connected')

    @pytest.mark.asyncio
    async def test_call_tool_inheritance(self):
        """Test that call_tool method is properly inherited from MCPToolkit."""
        with patch.object(MCPToolkit, 'call_tool', new_callable=AsyncMock) as mock_call_tool:
            mock_result = {"status": "success"}
            mock_call_tool.return_value = mock_result
            
            toolkit = PlaywrightMCPToolkit()
            result = await toolkit.call_tool("screenshot", {"url": "https://example.com"})
            
            # Verify the method was called with correct arguments
            mock_call_tool.assert_called_once_with("screenshot", {"url": "https://example.com"})
            assert result == mock_result

    def test_no_internal_mcp_toolkit_attribute(self):
        """Test that the old _mcp_toolkit attribute no longer exists."""
        toolkit = PlaywrightMCPToolkit()
        
        # Verify that _mcp_toolkit attribute doesn't exist
        assert not hasattr(toolkit, '_mcp_toolkit')

    def test_clients_attribute_exists(self):
        """Test that clients attribute exists (inherited from MCPToolkit)."""
        toolkit = PlaywrightMCPToolkit()
        
        # Verify that clients attribute exists and is properly initialized
        assert hasattr(toolkit, 'clients')
        assert isinstance(toolkit.clients, list)
        assert len(toolkit.clients) == 1

    def test_multiple_instances_independence(self):
        """Test that multiple PlaywrightMCPToolkit instances are independent."""
        toolkit1 = PlaywrightMCPToolkit(additional_args=["--arg1"])
        toolkit2 = PlaywrightMCPToolkit(additional_args=["--arg2"])
        
        # Verify instances are independent
        config1 = toolkit1.clients[0].config
        config2 = toolkit2.clients[0].config
        
        assert "--arg1" in config1.args
        assert "--arg1" not in config2.args
        assert "--arg2" in config2.args
        assert "--arg2" not in config1.args

    @pytest.mark.asyncio
    async def test_error_handling_inheritance(self):
        """Test that error handling is properly inherited from MCPToolkit."""
        with patch.object(MCPToolkit, 'connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            toolkit = PlaywrightMCPToolkit()
            
            # Verify that exceptions are properly propagated
            with pytest.raises(Exception, match="Connection failed"):
                await toolkit.connect()

    def test_docstring_and_attributes(self):
        """Test that class docstring and attributes are properly maintained."""
        toolkit = PlaywrightMCPToolkit()
        
        # Verify class has proper docstring
        assert PlaywrightMCPToolkit.__doc__ is not None
        assert "PlaywrightMCPToolkit" in PlaywrightMCPToolkit.__doc__
        assert "Model Context Protocol" in PlaywrightMCPToolkit.__doc__

    def test_method_resolution_order(self):
        """Test that method resolution order is correct after refactoring."""
        mro = PlaywrightMCPToolkit.__mro__
        
        # Verify MRO: PlaywrightMCPToolkit -> MCPToolkit -> BaseToolkit -> object
        assert len(mro) >= 3
        assert mro[0] == PlaywrightMCPToolkit
        assert mro[1] == MCPToolkit
        # Note: BaseToolkit should be in the MRO through MCPToolkit


class TestPlaywrightMCPToolkitIntegration:
    """Integration tests for PlaywrightMCPToolkit."""
    
    @pytest.mark.asyncio
    async def test_full_lifecycle_mock(self):
        """Test full lifecycle with mocked MCP operations."""
        with patch('camel.utils.mcp_client.create_mcp_client') as mock_create_client:
            # Mock client setup
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get_tools.return_value = [MagicMock(), MagicMock()]
            mock_client.is_connected.return_value = True
            mock_create_client.return_value = mock_client
            
            toolkit = PlaywrightMCPToolkit()
            
            # Test full lifecycle
            async with toolkit:
                tools = toolkit.get_tools()
                assert len(tools) == 2
                assert toolkit.is_connected

    def test_config_validation(self):
        """Test that configuration is properly validated."""
        # Test with empty additional args
        toolkit1 = PlaywrightMCPToolkit(additional_args=[])
        assert len(toolkit1.clients) == 1
        
        # Test with None additional args
        toolkit2 = PlaywrightMCPToolkit(additional_args=None)
        assert len(toolkit2.clients) == 1
        
        # Verify both have the same base configuration
        config1 = toolkit1.clients[0].config
        config2 = toolkit2.clients[0].config
        assert config1.args == config2.args == ["@playwright/mcp@latest"]


if __name__ == "__main__":
    pytest.main([__file__])
