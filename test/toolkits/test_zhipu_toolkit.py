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
from unittest.mock import MagicMock, patch

import pytest
import os
from zhipuai import ZhipuAI

from camel.toolkits.zhipu_toolkit import ZhiPuToolkit
from camel.toolkits import FunctionTool


# Fixture for mock ZhipuAI client
@pytest.fixture
def mock_zhipu_client():
    mock_client = MagicMock(spec=ZhipuAI)
    mock_client.files = MagicMock()
    mock_client.assistant = MagicMock()
    return mock_client


# Fixture for mock environment variables
@pytest.fixture
def mock_env_vars():
    with patch.dict(os.environ, {"ZHIPUAI_API_KEY": "test_api_key"}):
        yield


# Fixture for ZhiPuToolkit with mocked client
@pytest.fixture
def zhipu_toolkit(mock_zhipu_client, mock_env_vars):
    return ZhiPuToolkit(api_key="test_api_key")


def test_init_with_api_key():
    """Test initialization with provided API key."""
    toolkit = ZhiPuToolkit(api_key="test_api_key")
    assert toolkit.client.api_key == "test_api_key"
    assert toolkit.client.base_url == "https://open.bigmodel.cn/api/paas/v4/"


def test_init_with_api_key_and_url():
    """Test initialization with provided API key and URL."""
    toolkit = ZhiPuToolkit(api_key="test_api_key", url="http://test_url")
    assert toolkit.client.api_key == "test_api_key"
    assert toolkit.client.base_url == "http://test_url"


def test_init_from_env_vars(mock_zhipu_client, mock_env_vars):
    """Test initialization using environment variables."""
    toolkit = ZhiPuToolkit()
    assert toolkit.client.api_key == "test_api_key"
    assert toolkit.client.base_url == "https://open.bigmodel.cn/api/paas/v4/"


def test_init_no_api_key():
    """Test initialization without API key raises an error."""
    with pytest.raises(ValueError, match="ZHIPUAI_API_KEY is required."):
        ZhiPuToolkit()


@patch("camel.toolkits.zhipu_toolkit.ZhipuAI.files.create")
@patch("camel.toolkits.zhipu_toolkit.ZhipuAI.assistant.conversation")
def test_call_the_agent_success(
    mock_conversation, mock_file_create, zhipu_toolkit
):
    """Test successful call to the agent."""
    mock_file_create.return_value.id = "test_file_id"
    mock_conversation.return_value = [
        MagicMock(
            choices=[
                MagicMock(
                    delta=MagicMock(
                        content="Test response part 1", tool_calls=None
                    )
                )
            ],
            conversation_id="test_conversation_id",
        ),
        MagicMock(
            choices=[
                MagicMock(
                    delta=MagicMock(
                        content="Test response part 2", tool_calls=None
                    )
                )
            ],
            conversation_id="test_conversation_id",
        ),
    ]
    result = zhipu_toolkit._call_the_agent(
        prompt="Test prompt", assistant_id="test_assistant_id"
    )
    assert result == "Test response part 1Test response part 2"
    mock_conversation.assert_called_once()
    assert zhipu_toolkit.conversation_id == "test_conversation_id"
    assert not mock_file_create.called


@patch("camel.toolkits.zhipu_toolkit.ZhipuAI.files.create")
@patch("camel.toolkits.zhipu_toolkit.ZhipuAI.assistant.conversation")
def test_call_the_agent_with_file(
    mock_conversation, mock_file_create, zhipu_toolkit
):
    """Test calling the agent with a file."""
    mock_file_create.return_value.id = "test_file_id"
    mock_conversation.return_value = [
        MagicMock(
            choices=[
                MagicMock(
                    delta=MagicMock(
                        content="Test response", tool_calls=None
                    )
                )
            ],
            conversation_id="test_conversation_id",
        )
    ]
    with patch("builtins.open", MagicMock(), create=True):
        result = zhipu_toolkit._call_the_agent(
            prompt="Test prompt",
            assistant_id="test_assistant_id",
            file_path="test_file.txt",
        )
    assert result == "Test response"
    mock_file_create.assert_called_once()
    mock_conversation.assert_called_once()
    assert "test_file_id" in zhipu_toolkit.file_ids


@patch("camel.toolkits.zhipu_toolkit.ZhipuAI.files.create")
@patch("camel.toolkits.zhipu_toolkit.ZhipuAI.assistant.conversation")
def test_call_the_agent_file_upload_fails(
    mock_conversation, mock_file_create, zhipu_toolkit
):
    """Test handling of file upload failure."""
    mock_file_create.side_effect = Exception("File upload error")
    with patch("builtins.open", MagicMock(), create=True):
        result = zhipu_toolkit._call_the_agent(
            prompt="Test prompt",
            assistant_id="test_assistant_id",
            file_path="test_file.txt",
        )
    assert "Upload file failed: File upload error" in result
    assert not mock_conversation.called


@patch("camel.toolkits.zhipu_toolkit.ZhipuAI.files.create")
@patch("camel.toolkits.zhipu_toolkit.ZhipuAI.assistant.conversation")
def test_call_the_agent_api_call_fails(
    mock_conversation, mock_file_create, zhipu_toolkit
):
    """Test handling of API call failure."""
    mock_conversation.side_effect = Exception("API call error")
    result = zhipu_toolkit._call_the_agent(
        prompt="Test prompt", assistant_id="test_assistant_id"
    )
    assert "Call the agent failed: API call error" in result
    assert not mock_file_create.called


@patch("camel.toolkits.zhipu_toolkit.ZhipuAI.assistant.conversation")
def test_call_the_agent_with_tool_calls(mock_conversation, zhipu_toolkit):
    """Test parsing response with tool calls."""
    mock_conversation.return_value = [
        MagicMock(
            choices=[
                MagicMock(
                    delta=MagicMock(
                        content=None,
                        tool_calls=[
                            MagicMock(
                                id="call_123",
                                type="function",
                                function=MagicMock(
                                    name="get_current_weather",
                                    arguments='{"location": "Beijing"}',
                                ),
                            )
                        ],
                    )
                )
            ],
            conversation_id="test_conversation_id",
        ),
        MagicMock(
            choices=[
                MagicMock(
                    delta=MagicMock(
                        content=None,
                        tool_calls=[
                            MagicMock(
                                id="call_123",
                                type="function",
                                function=MagicMock(
                                    outputs=[{"name": "temperature", "value": "25"}]
                                ),
                            )
                        ],
                    )
                )
            ],
            conversation_id="test_conversation_id",
        ),
    ]
    result = zhipu_toolkit._call_the_agent(
        prompt="Test prompt", assistant_id="test_assistant_id"
    )
    assert "{'name': 'temperature', 'value': '25'}" in result


@patch("camel.toolkits.zhipu_toolkit.ZhiPuToolkit._call_the_agent")
def test_draw_mindmap(mock_call_agent, zhipu_toolkit):
    """Test draw_mindmap method."""
    zhipu_toolkit.draw_mindmap(prompt="Test mindmap prompt")
    mock_call_agent.assert_called_once_with(
        prompt="Test mindmap prompt",
        assistant_id="664dd7bd5bb3a13ba0f81668",
        file_path=None,
    )


@patch("camel.toolkits.zhipu_toolkit.ZhiPuToolkit._call_the_agent")
def test_draw_flowchart(mock_call_agent, zhipu_toolkit):
    """Test draw_flowchart method."""
    zhipu_toolkit.draw_flowchart(prompt="Test flowchart prompt", file_path="test.txt")
    mock_call_agent.assert_called_once_with(
        prompt="Test flowchart prompt",
        assistant_id="664dd7bd5bb3a13ba0f81668",
        file_path="test.txt",
    )


@patch("camel.toolkits.zhipu_toolkit.ZhiPuToolkit._call_the_agent")
def test_data_analysis(mock_call_agent, zhipu_toolkit):
    """Test data_analysis method."""
    zhipu_toolkit.data_analysis(prompt="Test data analysis prompt")
    mock_call_agent.assert_called_once_with(
        prompt="Test data analysis prompt",
        assistant_id="65a265419d72d299a9230616",
        file_path=None,
    )


@patch("camel.toolkits.zhipu_toolkit.ZhiPuToolkit._call_the_agent")
def test_ai_drawing(mock_call_agent, zhipu_toolkit):
    """Test ai_drawing method."""
    zhipu_toolkit.ai_drawing(prompt="Test drawing prompt", file_path="image.png")
    mock_call_agent.assert_called_once_with(
        prompt="Test drawing prompt",
        assistant_id="66437ef3d920bdc5c60f338e",
        file_path="image.png",
    )


@patch("camel.toolkits.zhipu_toolkit.ZhiPuToolkit._call_the_agent")
def test_ai_search(mock_call_agent, zhipu_toolkit):
    """Test ai_search method."""
    zhipu_toolkit.ai_search(prompt="Test search prompt")
    mock_call_agent.assert_called_once_with(
        prompt="Test search prompt",
        assistant_id="659e54b1b8006379b4b2abd6",
        file_path=None,
    )


@patch("camel.toolkits.zhipu_toolkit.ZhiPuToolkit._call_the_agent")
def test_ppt_generation(mock_call_agent, zhipu_toolkit):
    """Test ppt_generation method."""
    zhipu_toolkit.ppt_generation(prompt="Test PPT prompt", file_path="report.pdf")
    assert mock_call_agent.call_count == 2
    mock_call_agent.assert_any_call(
        prompt="Test PPT prompt",
        assistant_id="65d2f07bb2c10188f885bd89",
        file_path="report.pdf",
    )
    mock_call_agent.assert_any_call(
        prompt="生成PPT",
        assistant_id="65d2f07bb2c10188f885bd89",
        file_path="report.pdf",
        conversation_id=zhipu_toolkit.conversation_id,
    )


def test_get_tools(zhipu_toolkit):
    """Test get_tools method."""
    tools = zhipu_toolkit.get_tools()
    assert isinstance(tools, list)
    assert len(tools) == 6
    tool_names = [tool.name for tool in tools]
    assert "draw_mindmap" in tool_names
    assert "draw_flowchart" in tool_names
    assert "data_analysis" in tool_names
    assert "ai_drawing" in tool_names
    assert "ai_search" in tool_names
    assert "ppt_generation" in tool_names
    assert any(tool.func == zhipu_toolkit.draw_mindmap for tool in tools)
    assert any(tool.func == zhipu_toolkit.draw_flowchart for tool in tools)
    assert any(tool.func == zhipu_toolkit.data_analysis for tool in tools)
    assert any(tool.func == zhipu_toolkit.ai_drawing for tool in tools)
    assert any(tool.func == zhipu_toolkit.ai_search for tool in tools)
    assert any(tool.func == zhipu_toolkit.ppt_generation for tool in tools)