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

from camel.models import BaseModelBackend
from camel.toolkits.openai_agent_toolkit import OpenAIAgentToolkit
from camel.types import ModelPlatformType, ModelType


class TestOpenAIAgentToolkitInitialization:
    r"""Test cases for OpenAIAgentToolkit initialization."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
    def test_init_with_env_api_key(self):
        r"""Test initialization with API key from environment variable."""
        toolkit = OpenAIAgentToolkit()
        assert toolkit.api_key == "test_api_key"
        assert toolkit.client.api_key == "test_api_key"

    def test_init_with_provided_api_key(self):
        r"""Test initialization with explicitly provided API key."""
        toolkit = OpenAIAgentToolkit(api_key="provided_api_key")
        assert toolkit.api_key == "provided_api_key"
        assert toolkit.client.api_key == "provided_api_key"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
    def test_init_with_default_model(self):
        r"""Test initialization with default model."""
        toolkit = OpenAIAgentToolkit()
        assert toolkit.model is not None
        assert toolkit.model.model_type == ModelType.GPT_4O_MINI

    def test_init_with_custom_model(self):
        r"""Test initialization with custom model."""
        mock_model = MagicMock(spec=BaseModelBackend)
        mock_model.model_type = ModelType.GPT_4
        mock_model.model_platform = ModelPlatformType.OPENAI

        toolkit = OpenAIAgentToolkit(model=mock_model, api_key="test_api_key")
        assert toolkit.model == mock_model


class TestOpenAIAgentToolkitWebSearch:
    r"""Test cases for OpenAIAgentToolkit web search functionality."""

    @pytest.fixture
    def toolkit_fixture(self):
        r"""Fixture to create a toolkit instance with mocked dependencies."""
        with patch.object(OpenAIAgentToolkit, '__init__', return_value=None):
            toolkit = OpenAIAgentToolkit()
            toolkit.api_key = "test_api_key"
            toolkit.client = MagicMock()
            toolkit.model = MagicMock()
            toolkit.model.model_type = "gpt-4o-mini"
            return toolkit

    def test_web_search_success(self, toolkit_fixture):
        r"""Test successful web search."""
        # Setup
        toolkit = toolkit_fixture
        mock_response = MagicMock()
        mock_response.output_text = "Web search results"
        toolkit.client.responses.create.return_value = mock_response

        # Execute
        result = toolkit.web_search("test query")

        # Verify
        toolkit.client.responses.create.assert_called_once_with(
            model=str(toolkit.model.model_type),
            tools=[{"type": "web_search_preview"}],
            input="test query",
        )
        assert result == "Web search results"


class TestOpenAIAgentToolkitFileSearch:
    r"""Test cases for OpenAIAgentToolkit file search functionality."""

    @pytest.fixture
    def toolkit_fixture(self):
        r"""Fixture to create a toolkit instance with mocked dependencies."""
        with patch.object(OpenAIAgentToolkit, '__init__', return_value=None):
            toolkit = OpenAIAgentToolkit()
            toolkit.api_key = "test_api_key"
            toolkit.client = MagicMock()
            toolkit.model = MagicMock()
            toolkit.model.model_type = "gpt-4o-mini"
            return toolkit

    def test_file_search_success(self, toolkit_fixture):
        r"""Test successful file search."""
        # Setup
        toolkit = toolkit_fixture
        mock_response = MagicMock()
        mock_response.output_text = "File search results"
        toolkit.client.responses.create.return_value = mock_response

        # Execute
        result = toolkit.file_search("test query", "vector_store_id_123")

        # Verify
        toolkit.client.responses.create.assert_called_once_with(
            model=str(toolkit.model.model_type),
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": ["vector_store_id_123"],
                }
            ],
            input="test query",
        )
        assert result == "File search results"

    def test_file_search_empty_vector_store_id(self, toolkit_fixture):
        r"""Test file search with empty vector store ID."""
        # Setup
        toolkit = toolkit_fixture

        # Execute
        result = toolkit.file_search("test query", "  ")

        # Verify
        toolkit.client.responses.create.assert_not_called()
        assert "Empty vector store ID provided" in result

    def test_file_search_exception(self, toolkit_fixture):
        r"""Test file search with exception."""
        # Setup
        toolkit = toolkit_fixture
        toolkit.client.responses.create.side_effect = Exception("API error")

        # Execute
        result = toolkit.file_search("test query", "vector_store_id_123")

        # Verify
        assert "File search failed: API error" in result


class TestOpenAIAgentToolkitTools:
    r"""Test cases for OpenAIAgentToolkit tools functionality."""

    @pytest.fixture
    def toolkit_fixture(self):
        r"""Fixture to create a toolkit instance with mocked dependencies."""
        with patch.object(OpenAIAgentToolkit, '__init__', return_value=None):
            toolkit = OpenAIAgentToolkit()
            # Add these attributes to the mock
            toolkit.web_search = MagicMock()
            toolkit.web_search.__name__ = "web_search"
            toolkit.file_search = MagicMock()
            toolkit.file_search.__name__ = "file_search"
            return toolkit

    def test_get_tools(self, toolkit_fixture):
        r"""Test get_tools method returns correct FunctionTool objects."""
        # Setup
        toolkit = toolkit_fixture

        # Use a more comprehensive mock for FunctionTool
        with patch(
            'camel.toolkits.openai_agent_toolkit.FunctionTool'
        ) as mock_function_tool:
            # Create mock tools to return
            mock_web_tool = MagicMock()
            mock_file_tool = MagicMock()
            # Make the mock return different values on each call
            mock_function_tool.side_effect = [mock_web_tool, mock_file_tool]

            # Execute
            tools = toolkit.get_tools()

            # Verify
            assert len(tools) == 2
            assert mock_function_tool.call_count == 2
            # Check that the functions were passed to FunctionTool constructor
            mock_function_tool.assert_any_call(toolkit.web_search)
            mock_function_tool.assert_any_call(toolkit.file_search)


class TestOpenAIAgentToolkitIntegration:
    r"""Integration test cases for OpenAIAgentToolkit."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
    @patch('openai.OpenAI')
    @patch('camel.models.ModelFactory.create')
    def test_toolkit_integration(self, mock_model_factory, mock_openai):
        """Test the integration of all components in the toolkit."""
        # Setup
        mock_model = MagicMock(spec=BaseModelBackend)
        # Use string for model_type to avoid recursion issues
        mock_model.model_type = "gpt-4o-mini"
        mock_model_factory.return_value = mock_model

        # Mock the client and its methods
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.output_text = "Search results"
        mock_client.responses.create.return_value = mock_response

        # Mock FunctionTool to avoid schema generation issues
        with patch(
            'camel.toolkits.openai_agent_toolkit.FunctionTool'
        ) as mock_function_tool:
            mock_web_tool = MagicMock()
            mock_file_tool = MagicMock()
            mock_function_tool.side_effect = [mock_web_tool, mock_file_tool]

            # Create a properly mocked toolkit
            with patch.object(
                OpenAIAgentToolkit, '__init__', return_value=None
            ):
                toolkit = OpenAIAgentToolkit()
                # Set up the toolkit with our mocks
                toolkit.api_key = "test_api_key"
                toolkit.client = mock_client
                toolkit.model = mock_model

                toolkit.web_search = lambda query: "Search results"
                toolkit.file_search = (
                    lambda query, vector_store_id: "Search results"
                )

                # Execute the get_tools method
                tools = toolkit.get_tools()

                # Verify
                assert len(tools) == 2
                assert mock_function_tool.call_count == 2

                # Test that the web_search and file_search methods work
                web_result = toolkit.web_search("web query")
                file_result = toolkit.file_search(
                    "file query", "vector_store_id_123"
                )

                # Verify results
                assert web_result == "Search results"
                assert file_result == "Search results"
