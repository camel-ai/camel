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
import os
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits.zhipu_toolkit import ZhiPuToolkit


# Fixtures
@pytest.fixture
def mock_zhipuai_client():
    return MagicMock()


@pytest.fixture
def mock_zhipu_toolkit(mock_zhipuai_client):
    r"""Fixture for toolkit with mocked dependencies"""
    with patch('zhipuai.ZhipuAI', return_value=mock_zhipuai_client):
        toolkit = ZhiPuToolkit(api_key="test_api_key")
        toolkit.client = mock_zhipuai_client
        toolkit.file_ids = []
        toolkit.conversation_id = None
        yield toolkit


# --------------------------
# Test initialization
# --------------------------
def test_init_with_provided_api_key():
    r"""Test initialization with explicitly provided API key"""
    with patch('zhipuai.ZhipuAI') as mock_zhipuai:
        ZhiPuToolkit(api_key="provided_api_key")
        mock_zhipuai.assert_called_once_with(
            api_key="provided_api_key",
            base_url="https://open.bigmodel.cn/api/paas/v4/",
        )


def test_init_with_env_api_key():
    r"""Test initialization with API key from environment variable"""
    with patch.dict(os.environ, {"ZHIPUAI_API_KEY": "env_api_key"}):
        with patch('zhipuai.ZhipuAI') as mock_zhipuai:
            ZhiPuToolkit()
            mock_zhipuai.assert_called_once_with(
                api_key="env_api_key",
                base_url="https://open.bigmodel.cn/api/paas/v4/",
            )


def test_init_with_custom_url():
    r"""Test initialization with custom base URL"""
    with patch('zhipuai.ZhipuAI') as mock_zhipuai:
        ZhiPuToolkit(api_key="test_api_key", url="https://custom.url")
        mock_zhipuai.assert_called_once_with(
            api_key="test_api_key", base_url="https://custom.url"
        )


# --------------------------
# Test _call_the_agent method
# --------------------------
def test_call_the_agent_success(mock_zhipu_toolkit):
    r"""Test successful call to the agent"""
    # Setup mock response for the conversation
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.delta.content = "Success response"
    mock_response.choices = [mock_choice]
    mock_response.conversation_id = "test_conversation_id"

    # Set up the mock to return our generator of responses
    mock_zhipu_toolkit.client.assistant.conversation.return_value = [
        mock_response
    ]

    # Execute the method
    result = mock_zhipu_toolkit._call_the_agent(
        prompt="Test prompt", assistant_id="test_assistant_id"
    )

    # Verify
    mock_zhipu_toolkit.client.assistant.conversation.assert_called_once_with(
        assistant_id="test_assistant_id",
        conversation_id=None,
        model="glm-4-assistant",
        messages=[
            {
                "role": "user",
                "content": [{"type": "text", "text": "Test prompt"}],
            }
        ],
        stream=True,
        attachments=None,
        metadata=None,
    )
    assert result == "Success response"
    assert mock_zhipu_toolkit.conversation_id == "test_conversation_id"


def test_call_the_agent_with_file(mock_zhipu_toolkit):
    r"""Test calling the agent with a file upload"""
    # Setup mock file upload response
    mock_file_response = MagicMock()
    mock_file_response.id = "test_file_id"
    mock_zhipu_toolkit.client.files.create.return_value = mock_file_response

    # Setup mock conversation response
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.delta.content = "File analysis result"
    mock_response.choices = [mock_choice]
    mock_response.conversation_id = "test_conversation_id"
    mock_zhipu_toolkit.client.assistant.conversation.return_value = [
        mock_response
    ]

    # Mock open function
    with patch('builtins.open', MagicMock()):
        # Execute
        result = mock_zhipu_toolkit._call_the_agent(
            prompt="Analyze this file",
            assistant_id="test_assistant_id",
            file_path="test_file.txt",
        )

    # Verify
    mock_zhipu_toolkit.client.files.create.assert_called_once()
    mock_zhipu_toolkit.client.assistant.conversation.assert_called_once()
    assert mock_zhipu_toolkit.file_ids == ["test_file_id"]
    assert result == "File analysis result"
    assert mock_zhipu_toolkit.conversation_id == "test_conversation_id"


def test_call_the_agent_tool_calls(mock_zhipu_toolkit):
    r"""Test call with tool calls in the response"""
    # Setup complex mock response with tool_calls
    mock_tool_call = MagicMock()
    mock_output_item = MagicMock()
    mock_output_item.__str__.return_value = "Tool output"
    mock_attr = MagicMock()
    mock_attr.outputs = [mock_output_item]
    # Set up the structure to match what's checked in the code
    type(mock_tool_call).function = mock_attr

    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.delta.tool_calls = [mock_tool_call]
    mock_response.choices = [mock_choice]
    mock_response.conversation_id = "test_conversation_id"

    mock_zhipu_toolkit.client.assistant.conversation.return_value = [
        mock_response
    ]

    # Execute
    result = mock_zhipu_toolkit._call_the_agent(
        prompt="Use a tool", assistant_id="test_assistant_id"
    )

    # Verify
    assert result == "Tool output"
    assert mock_zhipu_toolkit.conversation_id == "test_conversation_id"


def test_call_the_agent_file_upload_failure(mock_zhipu_toolkit):
    r"""Test handling of file upload failure"""
    # Setup
    mock_zhipu_toolkit.client.files.create.side_effect = Exception(
        "Upload failed"
    )

    # Mock open function
    with patch('builtins.open', MagicMock()):
        # Execute
        result = mock_zhipu_toolkit._call_the_agent(
            prompt="Analyze this file",
            assistant_id="test_assistant_id",
            file_path="test_file.txt",
        )

    # Verify
    mock_zhipu_toolkit.client.files.create.assert_called_once()
    mock_zhipu_toolkit.client.assistant.conversation.assert_not_called()
    assert "Upload file failed: Upload failed" in result


def test_call_the_agent_conversation_failure(mock_zhipu_toolkit):
    r"""Test handling of conversation API failure"""
    # Setup
    mock_zhipu_toolkit.client.assistant.conversation.side_effect = Exception(
        "API error"
    )

    # Execute
    result = mock_zhipu_toolkit._call_the_agent(
        prompt="Test prompt", assistant_id="test_assistant_id"
    )

    # Verify
    mock_zhipu_toolkit.client.assistant.conversation.assert_called_once()
    assert "Call the agent failed: API error" in result


# --------------------------
# Test specific assistant functions
# --------------------------
def test_draw_mindmap(mock_zhipu_toolkit):
    r"""Test draw_mindmap method"""
    # Setup
    with patch.object(
        mock_zhipu_toolkit, '_call_the_agent', return_value="Mindmap created"
    ) as mock_call:
        # Execute
        result = mock_zhipu_toolkit.draw_mindmap("Create a mindmap about AI")

        # Verify
        mock_call.assert_called_once_with(
            prompt="Create a mindmap about AI",
            assistant_id="664dd7bd5bb3a13ba0f81668",
            file_path=None,
        )
        assert result == "Mindmap created"


def test_draw_mindmap_with_file(mock_zhipu_toolkit):
    r"""Test draw_mindmap method with file reference"""
    # Setup
    with patch.object(
        mock_zhipu_toolkit,
        '_call_the_agent',
        return_value="Mindmap created with file",
    ) as mock_call:
        # Execute
        result = mock_zhipu_toolkit.draw_mindmap(
            "Create a mindmap based on this file", file_path="reference.txt"
        )

        # Verify
        mock_call.assert_called_once_with(
            prompt="Create a mindmap based on this file",
            assistant_id="664dd7bd5bb3a13ba0f81668",
            file_path="reference.txt",
        )
        assert result == "Mindmap created with file"


def test_draw_flowchart(mock_zhipu_toolkit):
    r"""Test draw_flowchart method"""
    # Setup
    with patch.object(
        mock_zhipu_toolkit, '_call_the_agent', return_value="Flowchart created"
    ) as mock_call:
        # Execute
        result = mock_zhipu_toolkit.draw_flowchart(
            "Create a flowchart about data processing"
        )

        # Verify
        mock_call.assert_called_once_with(
            prompt="Create a flowchart about data processing",
            assistant_id="664dd7bd5bb3a13ba0f81668",
            file_path=None,
        )
        assert result == "Flowchart created"


def test_data_analysis(mock_zhipu_toolkit):
    r"""Test data_analysis method"""
    # Setup
    with patch.object(
        mock_zhipu_toolkit,
        '_call_the_agent',
        return_value="Data analysis results",
    ) as mock_call:
        # Execute
        result = mock_zhipu_toolkit.data_analysis(
            "Analyze this dataset", file_path="data.csv"
        )

        # Verify
        mock_call.assert_called_once_with(
            prompt="Analyze this dataset",
            assistant_id="65a265419d72d299a9230616",
            file_path="data.csv",
        )
        assert result == "Data analysis results"


def test_ai_drawing(mock_zhipu_toolkit):
    r"""Test ai_drawing method"""
    # Setup
    with patch.object(
        mock_zhipu_toolkit, '_call_the_agent', return_value="Image created"
    ) as mock_call:
        # Execute
        result = mock_zhipu_toolkit.ai_drawing("Draw a sunset over mountains")

        # Verify
        mock_call.assert_called_once_with(
            prompt="Draw a sunset over mountains",
            assistant_id="66437ef3d920bdc5c60f338e",
            file_path=None,
        )
        assert result == "Image created"


def test_ai_search(mock_zhipu_toolkit):
    r"""Test ai_search method"""
    # Setup
    with patch.object(
        mock_zhipu_toolkit, '_call_the_agent', return_value="Search results"
    ) as mock_call:
        # Execute
        result = mock_zhipu_toolkit.ai_search("Find information about Python")

        # Verify
        mock_call.assert_called_once_with(
            prompt="Find information about Python",
            assistant_id="659e54b1b8006379b4b2abd6",
            file_path=None,
        )
        assert result == "Search results"


def test_ppt_generation(mock_zhipu_toolkit):
    r"""Test ppt_generation method"""
    # Setup
    mock_zhipu_toolkit.conversation_id = None
    side_effect_values = ["Initial response", "PPT generated"]

    with patch.object(
        mock_zhipu_toolkit, '_call_the_agent', side_effect=side_effect_values
    ) as mock_call:
        # Set conversation_id after first call
        def side_effect(*args, **kwargs):
            result = side_effect_values.pop(0)
            mock_zhipu_toolkit.conversation_id = "test_conversation_id"
            return result

        mock_call.side_effect = side_effect

        # Execute
        result = mock_zhipu_toolkit.ppt_generation(
            "Create a presentation about climate change"
        )

        # Verify
        assert mock_call.call_count == 2
        # First call
        mock_call.assert_any_call(
            prompt="Create a presentation about climate change",
            assistant_id="65d2f07bb2c10188f885bd89",
            file_path=None,
        )
        # Second call
        mock_call.assert_any_call(
            prompt='生成PPT',
            assistant_id="65d2f07bb2c10188f885bd89",
            file_path=None,
            conversation_id="test_conversation_id",
        )
        assert result == "PPT generated"


# --------------------------
# Test get_tools method
# --------------------------
def test_get_tools(mock_zhipu_toolkit):
    r"""Test get_tools method returns correct FunctionTool objects"""
    # Setup
    with patch('camel.toolkits.FunctionTool') as mock_function_tool:
        # Create mock tools to return
        mock_tools = [MagicMock() for _ in range(6)]
        mock_function_tool.side_effect = mock_tools

        # Execute
        tools = mock_zhipu_toolkit.get_tools()

        # Verify
        assert len(tools) == 6
        assert mock_function_tool.call_count == 6

        # Check that all functions were passed to FunctionTool constructor
        mock_function_tool.assert_any_call(mock_zhipu_toolkit.draw_mindmap)
        mock_function_tool.assert_any_call(mock_zhipu_toolkit.draw_flowchart)
        mock_function_tool.assert_any_call(mock_zhipu_toolkit.data_analysis)
        mock_function_tool.assert_any_call(mock_zhipu_toolkit.ai_drawing)
        mock_function_tool.assert_any_call(mock_zhipu_toolkit.ai_search)
        mock_function_tool.assert_any_call(mock_zhipu_toolkit.ppt_generation)
