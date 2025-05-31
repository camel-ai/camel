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
from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp.server.fastmcp import Context

from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.toolkits import FunctionTool
from services.agent_mcp.agent_config import agents_dict, description_dict
from services.agent_mcp.agent_mcp_server import (
    get_agent_info,
    get_agents_info,
    get_available_tools,
    get_chat_history,
    reset,
    set_output_language,
    step,
)


@pytest.fixture
def mock_agent():
    mock_tool = FunctionTool(lambda query: "Mock response")
    agent = Mock()
    agent.agent_id = "test_agent"
    agent.model_type = "test_model"
    agent.output_language = "en"
    agent.chat_history = [
        {'role': 'system', 'content': 'You are a helpful assistant.'}
    ]
    agent.tool_dict = {"test_tool": mock_tool}
    agent.astep = AsyncMock()
    agent.reset = Mock()
    return agent


@pytest.fixture
def mock_context():
    context = Mock(spec=Context)
    context.info = AsyncMock()
    return context


@pytest.fixture
def mock_message():
    message = Mock(spec=BaseMessage)
    message.to_dict.return_value = {
        "role": "assistant",
        "content": "Test response",
    }
    return message


@pytest.fixture
def mock_response(mock_message):
    response = Mock(spec=ChatAgentResponse)
    response.msgs = [mock_message]
    response.terminated = False
    response.info = {}
    return response


@pytest.mark.asyncio
async def test_step_success(mock_agent, mock_response, mock_context):
    with patch.dict(agents_dict, {"test": mock_agent}):
        mock_agent.astep.return_value = mock_response
        result = await step("test", "Hello", mock_context)

        assert result["status"] == "success"
        assert len(result["messages"]) == 1
        assert result["messages"][0]["content"] == "Test response"
        assert not result["terminated"]
        assert result["info"] == {}

        mock_agent.astep.assert_called_once_with("Hello", None)
        mock_context.info.assert_called_once()


@pytest.mark.asyncio
async def test_step_with_format(mock_agent, mock_response, mock_context):
    response_format = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
    }

    with patch.dict(agents_dict, {"test": mock_agent}):
        mock_agent.astep.return_value = mock_response
        result = await step("test", "Hello", mock_context, response_format)

        assert result["status"] == "success"
        mock_agent.astep.assert_called_once()
        mock_context.info.assert_called_once()


@pytest.mark.asyncio
async def test_step_agent_not_found(mock_context):
    # Ensure agents_dict is empty
    with patch.dict(agents_dict, {}, clear=True):
        result = await step("nonexistent", "Hello", mock_context)
        assert result["status"] == "error"
        assert "not found" in result["message"]


@pytest.mark.asyncio
async def test_reset(mock_agent, mock_context):
    with patch.dict(agents_dict, {"test": mock_agent}):
        result = await reset(mock_context)

        assert result["status"] == "success"
        assert "successfully" in result["message"]
        mock_agent.reset.assert_called_once()
        mock_context.info.assert_called_once()


@pytest.mark.asyncio
async def test_set_output_language(mock_agent, mock_context):
    with patch.dict(agents_dict, {"test": mock_agent}):
        result = await set_output_language("fr", mock_context)

        assert result["status"] == "success"
        assert "fr" in result["message"]
        assert mock_agent.output_language == "fr"
        mock_context.info.assert_called_once()


def test_get_agents_info():
    result = get_agents_info()
    assert result == description_dict


def test_get_chat_history(mock_agent):
    with patch.dict(agents_dict, {"test": mock_agent}):
        result = get_chat_history("test")
        assert result["status"] == "success"
        assert result["chat_history"] == mock_agent.chat_history


def test_get_chat_history_agent_not_found():
    with patch.dict(agents_dict, {}, clear=True):
        result = get_chat_history("nonexistent")
        assert result["status"] == "error"
        assert "not found" in result["message"]


def test_get_agent_info(mock_agent):
    test_description = "Test agent description"
    with (
        patch.dict(agents_dict, {"test": mock_agent}),
        patch.dict(description_dict, {"test": test_description}),
    ):
        result = get_agent_info("test")

        assert result["agent_id"] == "test_agent"
        assert result["model_type"] == "test_model"
        assert result["output_language"] == "en"
        assert result["description"] == test_description


def test_get_agent_info_agent_not_found():
    with patch.dict(agents_dict, {}, clear=True):
        result = get_agent_info("nonexistent")
        assert result["status"] == "error"
        assert "not found" in result["message"]


def test_get_available_tools(mock_agent):
    with patch.dict(agents_dict, {"test": mock_agent}):
        result = get_available_tools("test")
        assert result == mock_agent.tool_dict


def test_get_available_tools_agent_not_found():
    with patch.dict(agents_dict, {}, clear=True):
        result = get_available_tools("nonexistent")
        assert result["status"] == "error"
        assert "not found" in result["message"]
