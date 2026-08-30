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
from unittest.mock import Mock, patch

import pytest

from camel.toolkits import Mem0CloudToolkit


@pytest.fixture
def mem0_cloud_toolkit():
    """Create a Mem0CloudToolkit instance for testing."""
    with patch('camel.toolkits.mem0_cloud_toolkit.Mem0Storage'):
        toolkit = Mem0CloudToolkit(agent_id="test-agent")  # Uses default user_id="camel_memory"
        # Mock the memory storage
        toolkit.memory = Mock()
        toolkit.memory._chat_history_block = Mock()
        toolkit.memory._chat_history_block.storage = Mock()
        toolkit.memory._chat_history_block.storage.client = Mock()
        return toolkit


class TestMem0CloudToolkit:
    def test_init(self):
        """Test toolkit initialization."""
        with patch('camel.toolkits.mem0_cloud_toolkit.Mem0Storage'):
            toolkit = Mem0CloudToolkit(
                agent_id="test-agent", user_id="test-user", timeout=30.0
            )
            assert toolkit.agent_id == "test-agent"
            assert toolkit.user_id == "test-user"
            assert toolkit.timeout == 30.0
            assert toolkit.token_limit == 4096  # default value
            assert toolkit.memory is not None

    def test_init_default_user_id(self):
        """Test toolkit initialization with default user_id."""
        with patch('camel.toolkits.mem0_cloud_toolkit.Mem0Storage'):
            toolkit = Mem0CloudToolkit(agent_id="test-agent")
            assert toolkit.agent_id == "test-agent"
            assert toolkit.user_id == "camel_memory"  # default value
            assert toolkit.memory is not None

    def test_init_with_custom_params(self):
        """Test toolkit initialization with custom token parameters."""
        from camel.utils import OpenAITokenCounter
        from camel.types import ModelType
        
        custom_counter = OpenAITokenCounter(ModelType.GPT_4O)
        with patch('camel.toolkits.mem0_cloud_toolkit.Mem0Storage'):
            toolkit = Mem0CloudToolkit(
                agent_id="test-agent", 
                user_id="test-user",
                token_counter=custom_counter,
                token_limit=8192
            )
            assert toolkit.token_counter == custom_counter
            assert toolkit.token_limit == 8192

    def test_add_memory(self, mem0_cloud_toolkit):
        """Test adding a memory record."""
        # Mock the write_records method
        mem0_cloud_toolkit.memory.write_records = Mock()

        content = "Remember that I like coffee in the morning"
        metadata = {"category": "preference"}

        result = mem0_cloud_toolkit.add_memory(content, metadata)

        assert result == "Memory added successfully to Mem0 cloud."
        mem0_cloud_toolkit.memory.write_records.assert_called_once()

        # Verify the record was created with correct content
        call_args = mem0_cloud_toolkit.memory.write_records.call_args[0][0]
        record = call_args[0]  # First record in the list
        assert record.message.content == content
        assert record.message.meta_dict == metadata
        assert record.agent_id == "test-agent"

    def test_add_memory_without_metadata(self, mem0_cloud_toolkit):
        """Test adding a memory record without metadata."""
        mem0_cloud_toolkit.memory.write_records = Mock()

        content = "I work remotely"
        result = mem0_cloud_toolkit.add_memory(content)

        assert result == "Memory added successfully to Mem0 cloud."
        mem0_cloud_toolkit.memory.write_records.assert_called_once()

        # Verify metadata defaults to empty dict
        call_args = mem0_cloud_toolkit.memory.write_records.call_args[0][0]
        record = call_args[0]
        assert record.message.meta_dict == {}

    def test_retrieve_memories(self, mem0_cloud_toolkit):
        """Test retrieving all memories."""
        mock_memories = [
            {"id": "1", "content": "Memory 1"},
            {"id": "2", "content": "Memory 2"},
        ]
        storage = mem0_cloud_toolkit.memory._chat_history_block.storage
        storage.load.return_value = mock_memories

        result = mem0_cloud_toolkit.retrieve_memories()

        assert "Raw API Response:" in result
        assert str(mock_memories) in result
        storage.load.assert_called_once()

    def test_search_memories_success(self, mem0_cloud_toolkit):
        """Test successful memory search."""
        mock_results = {
            "results": [
                {"id": "1", "content": "Coffee preference", "score": 0.95}
            ]
        }
        client = mem0_cloud_toolkit.memory._chat_history_block.storage.client
        client.search.return_value = mock_results

        query = "coffee preferences"
        result = mem0_cloud_toolkit.search_memories(query)

        assert "Raw API Response:" in result
        assert str(mock_results) in result

        # Verify search was called with correct parameters
        search_call = client.search
        search_call.assert_called_once_with(
            query,
            version="v2",
            filters={
                "OR": [{"user_id": "test-user"}, {"agent_id": "test-agent"}]
            },
            output_format="v1.1",
            rerank=True,
            threshold=0.01,
            top_k=10,
            keyword_search=True,
        )

    def test_search_memories_error(self, mem0_cloud_toolkit):
        """Test memory search with API error."""
        error_message = "API connection failed"
        client = mem0_cloud_toolkit.memory._chat_history_block.storage.client
        client.search.side_effect = Exception(error_message)

        result = mem0_cloud_toolkit.search_memories("test query")

        assert "API Error:" in result
        assert error_message in result

    def test_delete_memory(self, mem0_cloud_toolkit):
        """Test deleting a specific memory."""
        memory_id = "test-memory-id"
        client = mem0_cloud_toolkit.memory._chat_history_block.storage.client
        client.delete = Mock()

        result = mem0_cloud_toolkit.delete_memory(memory_id)

        assert f"Memory {memory_id} deleted successfully" in result
        client.delete.assert_called_once_with(memory_id=memory_id)

    def test_delete_memory_error(self, mem0_cloud_toolkit):
        """Test deleting a memory with API error."""
        memory_id = "test-memory-id"
        error_message = "Memory not found"
        client = mem0_cloud_toolkit.memory._chat_history_block.storage.client
        client.delete.side_effect = Exception(error_message)

        result = mem0_cloud_toolkit.delete_memory(memory_id)

        assert "API Error:" in result
        assert error_message in result

    def test_clear_memory(self, mem0_cloud_toolkit):
        """Test clearing all memories."""
        mem0_cloud_toolkit.memory.clear = Mock()

        result = mem0_cloud_toolkit.clear_memory()

        assert (
            result == "All memories have been cleared from Mem0 cloud storage."
        )
        mem0_cloud_toolkit.memory.clear.assert_called_once()

    def test_get_tools(self, mem0_cloud_toolkit):
        """Test getting list of function tools."""
        tools = mem0_cloud_toolkit.get_tools()

        assert len(tools) == 5
        tool_names = [tool.get_function_name() for tool in tools]
        expected_tools = [
            "add_memory",
            "retrieve_memories",
            "search_memories",
            "delete_memory",
            "clear_memory",
        ]
        assert all(name in tool_names for name in expected_tools)

    def test_setup_memory(self):
        """Test memory setup during initialization."""
        with patch(
            'camel.toolkits.mem0_cloud_toolkit.Mem0Storage'
        ) as mock_storage:
            with patch(
                'camel.toolkits.mem0_cloud_toolkit.ChatHistoryMemory'
            ) as mock_chat_memory:
                with patch(
                    'camel.toolkits.mem0_cloud_toolkit.'
                    'ScoreBasedContextCreator'
                ) as mock_context_creator:
                    with patch(
                        'camel.toolkits.mem0_cloud_toolkit.'
                        'OpenAITokenCounter'
                    ) as mock_token_counter:
                        Mem0CloudToolkit(
                            agent_id="test-agent", user_id="test-user"
                        )

                        # Verify all components were initialized correctly
                        mock_storage.assert_called_once_with(
                            agent_id="test-agent", user_id="test-user"
                        )
                        mock_token_counter.assert_called_once()
                        mock_context_creator.assert_called_once()
                        mock_chat_memory.assert_called_once()

    @patch.dict(os.environ, {"MEM0_API_KEY": "test_key"})
    def test_dependencies_required_decorator(self, mem0_cloud_toolkit):
        """Test methods are properly decorated with dependencies_required."""
        # Test that the decorator is applied (this would fail if mem0ai is
        # not installed) but we're mocking the storage so it should work in
        # tests
        try:
            result = mem0_cloud_toolkit.add_memory("test content")
            assert "Memory added successfully" in result
        except ImportError:
            # This is expected if mem0ai is not installed
            pass


class TestMem0CloudToolkitIntegration:
    """Integration tests with mocked external dependencies."""

    @patch('camel.toolkits.mem0_cloud_toolkit.Mem0Storage')
    @patch.dict(os.environ, {"MEM0_API_KEY": "test_key"})
    def test_full_workflow(self, mock_storage_class):
        """Test a complete workflow: add, search, retrieve, delete."""
        # Setup mocks
        mock_storage = Mock()
        mock_storage_class.return_value = mock_storage

        # Create toolkit
        toolkit = Mem0CloudToolkit(
            agent_id="workflow-agent", user_id="workflow-user"
        )

        # Mock memory methods
        toolkit.memory = Mock()
        toolkit.memory.write_records = Mock()
        toolkit.memory.clear = Mock()
        toolkit.memory._chat_history_block = Mock()
        toolkit.memory._chat_history_block.storage = Mock()
        toolkit.memory._chat_history_block.storage.load.return_value = []
        toolkit.memory._chat_history_block.storage.client = Mock()
        client = toolkit.memory._chat_history_block.storage.client
        client.search.return_value = {"results": []}

        # Test workflow
        # 1. Add memory
        add_result = toolkit.add_memory("I prefer tea over coffee")
        assert "successfully" in add_result

        # 2. Search memories
        search_result = toolkit.search_memories("tea preference")
        assert "Raw API Response" in search_result

        # 3. Retrieve all memories
        retrieve_result = toolkit.retrieve_memories()
        assert "Raw API Response" in retrieve_result

        # 4. Delete specific memory
        delete_result = toolkit.delete_memory("test-memory-id")
        assert "deleted successfully" in delete_result

        # 5. Clear all memories
        clear_result = toolkit.clear_memory()
        assert "cleared" in clear_result

        # Verify all methods were called
        toolkit.memory.write_records.assert_called_once()
        client.search.assert_called_once()
        toolkit.memory._chat_history_block.storage.load.assert_called_once()
        toolkit.memory.clear.assert_called_once()

