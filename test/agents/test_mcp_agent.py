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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.agents import MCPAgent
from camel.agents.mcp_agent import SYS_PROMPT, MCPArgument, MCPToolCall
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


class TestMCPAgentInitialization:
    r"""Tests for MCPAgent initialization."""

    def test_init_with_function_call_available(self):
        r"""Test initialization with function call available."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            # Add a valid server configuration
            json.dump(
                {
                    "mcpWebServers": {
                        "test-server": {"url": "http://example.com/mcp"}
                    }
                },
                temp_file,
            )
            temp_file.flush()

            agent = MCPAgent(
                config_path=temp_file.name, model_function_call_available=True
            )

            # Verify system prompt is set correctly
            assert (
                agent._system_message.content == "You are a helpful assitant."
            )
            assert agent._model_function_call_available is True
            assert agent._text_tools is None

    def test_init_without_function_call_available(self):
        r"""Test initialization without function call available."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            # Add a valid server configuration
            json.dump(
                {
                    "mcpWebServers": {
                        "test-server": {"url": "http://example.com/mcp"}
                    }
                },
                temp_file,
            )
            temp_file.flush()

            agent = MCPAgent(
                config_path=temp_file.name, model_function_call_available=False
            )

            # Verify system prompt is set correctly
            assert agent._system_message.content == SYS_PROMPT
            assert agent._model_function_call_available is False
            assert agent._text_tools is None

    def test_init_with_model(self):
        r"""Test initialization with a model."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            # Add a valid server configuration
            json.dump(
                {
                    "mcpWebServers": {
                        "test-server": {"url": "http://example.com/mcp"}
                    }
                },
                temp_file,
            )
            temp_file.flush()

            model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=ModelType.GPT_4O,
            )
            agent = MCPAgent(config_path=temp_file.name, model=model)

            # Check that the model type is the same rather than the exact
            # object
            assert agent.model_backend.model_type == model.model_type


class TestMCPAgentConnection:
    r"""Tests for MCPAgent connection methods."""

    @pytest.mark.asyncio
    async def test_connect(self):
        r"""Test connect method."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            json.dump({"mcpWebServers": {}}, temp_file)
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.connect = AsyncMock()

                agent = MCPAgent(config_path=temp_file.name)
                await agent.connect()

                # Verify connect was called
                mock_toolkit_instance.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self):
        r"""Test close method."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            json.dump({"mcpWebServers": {}}, temp_file)
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.disconnect = AsyncMock()

                agent = MCPAgent(config_path=temp_file.name)
                await agent.close()

                # Verify disconnect was called
                mock_toolkit_instance.disconnect.assert_called_once()


class TestMCPAgentTools:
    r"""Tests for MCPAgent tools methods."""

    def test_add_mcp_tools_not_connected(self):
        r"""Test add_mcp_tools when server is not connected."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            json.dump({"mcpWebServers": {}}, temp_file)
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.is_connected.return_value = False

                agent = MCPAgent(config_path=temp_file.name)

                with pytest.raises(
                    ConnectionError, match="Server is not connected."
                ):
                    agent.add_mcp_tools()

    def test_add_mcp_tools_with_function_call(self):
        r"""Test add_mcp_tools with function call available."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            json.dump({"mcpWebServers": {}}, temp_file)
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.is_connected.return_value = True
                mock_toolkit_instance.get_text_tools.return_value = (
                    "Text tools description"
                )
                mock_toolkit_instance.get_tools.return_value = [MagicMock()]

                agent = MCPAgent(
                    config_path=temp_file.name,
                    model_function_call_available=True,
                )
                agent.add_tool = MagicMock()

                agent.add_mcp_tools()

                # Verify text tools are set
                assert agent._text_tools is not None
                # Verify add_tool was called
                agent.add_tool.assert_called_once()

    def test_add_mcp_tools_without_function_call(self):
        r"""Test add_mcp_tools without function call available."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            json.dump({"mcpWebServers": {}}, temp_file)
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.is_connected.return_value = True
                mock_toolkit_instance.get_text_tools.return_value = (
                    "Text tools description"
                )

                agent = MCPAgent(
                    config_path=temp_file.name,
                    model_function_call_available=False,
                )
                agent.add_tool = MagicMock()

                agent.add_mcp_tools()

                # Verify text tools are set
                assert agent._text_tools is not None
                # Verify add_tool was not called
                agent.add_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_text_tools_not_connected(self):
        r"""Test get_text_tools when server is not connected."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            json.dump({"mcpWebServers": {}}, temp_file)
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.is_connected.return_value = False

                agent = MCPAgent(config_path=temp_file.name)

                with pytest.raises(
                    ConnectionError, match="Server is not connected."
                ):
                    await agent.get_text_tools()

    @pytest.mark.asyncio
    async def test_get_text_tools(self):
        r"""Test get_text_tools."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            # Add a valid server configuration
            json.dump(
                {
                    "mcpWebServers": {
                        "test-server": {"url": "http://example.com/mcp"}
                    }
                },
                temp_file,
            )
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.is_connected.return_value = True
                mock_toolkit_instance.get_text_tools.return_value = (
                    "Text tools description"
                )

                agent = MCPAgent(config_path=temp_file.name)
                # Properly mock the async method
                agent.add_mcp_tools = AsyncMock()
                agent._text_tools = "Text tools description"

                result = await agent.get_text_tools()

                # Verify add_mcp_tools was called
                agent.add_mcp_tools.assert_called_once()
                # Verify result is correct
                assert result == "Text tools description"


class TestMCPAgentRun:
    r"""Tests for MCPAgent run method."""

    @pytest.mark.asyncio
    async def test_run_not_connected(self):
        r"""Test run when server is not connected."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            json.dump({"mcpWebServers": {}}, temp_file)
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.is_connected.return_value = False

                agent = MCPAgent(config_path=temp_file.name)

                with pytest.raises(
                    ConnectionError, match="Server is not connected."
                ):
                    await agent.run("Test prompt")

    @pytest.mark.asyncio
    async def test_run_with_function_call(self):
        r"""Test run with function call available."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            json.dump({"mcpWebServers": {}}, temp_file)
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.is_connected.return_value = True

                agent = MCPAgent(
                    config_path=temp_file.name,
                    model_function_call_available=True,
                )
                agent.astep = AsyncMock(return_value=MagicMock())

                result = await agent.run("Test prompt")

                # Verify astep was called with correct prompt
                agent.astep.assert_called_once_with("Test prompt")
                assert result == agent.astep.return_value

    @pytest.mark.asyncio
    async def test_run_without_function_call(self):
        r"""Test run without function call available."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            json.dump({"mcpWebServers": {}}, temp_file)
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.is_connected.return_value = True

                # Create a mock server
                mock_server = MagicMock()
                mock_server.call_tool = AsyncMock()
                mock_server.call_tool.return_value.content = [
                    MagicMock(text="Tool result")
                ]
                mock_toolkit_instance.servers = [mock_server]

                # Create a mock response with parsed MCPToolCall
                mock_response = MagicMock()
                mock_tool_call = MCPToolCall(
                    server_idx=0,
                    tool_name="test_tool",
                    tool_args=[
                        MCPArgument(arg_name="arg1", arg_value="value1")
                    ],
                )
                mock_response.msgs = [MagicMock(parsed=mock_tool_call)]

                agent = MCPAgent(
                    config_path=temp_file.name,
                    model_function_call_available=False,
                )
                agent._text_tools = "Text tools description"
                agent.astep = AsyncMock(
                    side_effect=[mock_response, MagicMock()]
                )
                # Verify astep was called twice
                assert agent.astep.call_count == 2
                # Verify server.call_tool was called with correct arguments
                mock_server.call_tool.assert_called_once_with(
                    "test_tool", {"arg1": "value1"}
                )

    @pytest.mark.asyncio
    async def test_run_without_function_call_parse_error(self):
        r"""Test run without function call when parsing fails."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json'
        ) as temp_file:
            json.dump({"mcpWebServers": {}}, temp_file)
            temp_file.flush()

            with patch('camel.agents.mcp_agent.MCPToolkit') as mock_toolkit:
                mock_toolkit_instance = mock_toolkit.return_value
                mock_toolkit_instance.is_connected.return_value = True

                # Create a mock response with no parsed data
                mock_response = MagicMock()
                mock_response.msgs = [MagicMock(parsed=None)]

                agent = MCPAgent(
                    config_path=temp_file.name,
                    model_function_call_available=False,
                )
                agent._text_tools = "Text tools description"
                agent.astep = AsyncMock(return_value=mock_response)

                with pytest.raises(
                    ValueError, match="Failed to parse response as MCPToolCall"
                ):
                    await agent.run("Test prompt")
