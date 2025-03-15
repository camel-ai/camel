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

import unittest
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from camel.memories import (
    AgentMemory,
    BaseContextCreator,
    Mem0Memory,
    MemoryRecord,
    ContextRecord,
)
from camel.messages import BaseMessage
from camel.storages import BaseMemoryStorage, Mem0Storage
from camel.types import OpenAIBackendRole


class MockContextCreator(BaseContextCreator):
    """Mock context creator for testing."""

    def create_context(self, records: List[ContextRecord]) -> str:
        return "mock context"


class TestMem0Memory(unittest.TestCase):
    """Unit tests for the Mem0Memory class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.context_creator = MockContextCreator()
        self.api_key = "test_api_key"
        self.user_id = "test_user"
        self.agent_id = "test_agent"
        self.run_id = "test_run"
        self.metadata = {"test_key": "test_value"}
        self.retrieve_limit = 5

        # Create a mock for the Mem0Storage
        self.mock_storage = Mock(spec=Mem0Storage)
        
        # Initialize memory with test parameters
        self.memory = Mem0Memory(
            context_creator=self.context_creator,
            storage=self.mock_storage,
            api_key=self.api_key,
            user_id=self.user_id,
            agent_id=self.agent_id,
            run_id=self.run_id,
            metadata=self.metadata,
            retrieve_limit=self.retrieve_limit,
        )

    def test_initialization(self):
        """Test proper initialization of Mem0Memory."""
        self.assertIsInstance(self.memory, AgentMemory)
        self.assertEqual(self.memory._context_creator, self.context_creator)
        self.assertEqual(self.memory._storage, self.mock_storage)
        self.assertEqual(self.memory._retrieve_limit, self.retrieve_limit)
        self.assertEqual(self.memory._current_topic, "")

    def test_initialization_without_storage(self):
        """Test initialization without providing storage."""
        with patch('camel.memories.agent_memories.Mem0Storage') as mock_storage_class:
            memory = Mem0Memory(
                context_creator=self.context_creator,
                api_key=self.api_key,
            )
            mock_storage_class.assert_called_once_with(
                api_key=self.api_key,
                user_id=None,
                agent_id=None,
                run_id=None,
                metadata=None,
            )
            self.assertIsNotNone(memory._storage)

    def test_retrieve_empty_topic(self):
        """Test retrieve with empty current topic."""
        results = self.memory.retrieve()
        self.assertEqual(results, [])
        self.mock_storage.search.assert_not_called()

    def test_retrieve_with_topic(self):
        """Test retrieve with a current topic."""
        self.memory._current_topic = "test topic"
        mock_memories = [
            {
                "text": {
                    "role": OpenAIBackendRole.USER,
                    "content": "test content 1"
                },
                "metadata": {"score": 0.9}
            },
            {
                "text": {
                    "role": OpenAIBackendRole.ASSISTANT,
                    "content": "test content 2"
                },
                "metadata": {"score": 0.8}
            }
        ]
        self.mock_storage.search.return_value = mock_memories

        results = self.memory.retrieve()

        self.mock_storage.search.assert_called_once_with(
            query="test topic",
            limit=self.retrieve_limit,
        )
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], ContextRecord)
        self.assertEqual(results[0].role_at_backend, OpenAIBackendRole.USER)
        self.assertEqual(results[0].content, "test content 1")

    def test_retrieve_with_string_text(self):
        """Test retrieve with memories containing string text."""
        self.memory._current_topic = "test topic"
        mock_memories = [
            {
                "text": "plain text memory",
                "metadata": {"score": 0.9}
            }
        ]
        self.mock_storage.search.return_value = mock_memories

        results = self.memory.retrieve()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].role_at_backend, OpenAIBackendRole.USER)
        self.assertEqual(results[0].content, "plain text memory")

    def test_write_records(self):
        """Test writing memory records."""
        mock_message = Mock(spec=BaseMessage)
        mock_message.content = "test content"
        
        records = [
            MemoryRecord(role_at_backend=OpenAIBackendRole.USER,
                        message=mock_message),
            MemoryRecord(role_at_backend=OpenAIBackendRole.ASSISTANT,
                        message=mock_message),
        ]

        self.memory.write_records(records)

        # Verify current topic is updated from user message
        self.assertEqual(self.memory._current_topic, "test content")

        # Verify storage.add is called with correct format
        self.mock_storage.add.assert_called_once()
        call_args = self.mock_storage.add.call_args[0][0]
        self.assertEqual(len(call_args), 2)
        self.assertEqual(call_args[0]["role"], OpenAIBackendRole.USER)
        self.assertEqual(call_args[0]["content"], "test content")

    def test_get_context_creator(self):
        """Test getting the context creator."""
        creator = self.memory.get_context_creator()
        self.assertEqual(creator, self.context_creator)

    def test_clear(self):
        """Test clearing the memory."""
        self.memory.clear()
        self.mock_storage.delete.assert_called_once()

    def test_error_handling(self):
        """Test error handling during operations."""
        self.mock_storage.search.side_effect = Exception("API Error")
        self.memory._current_topic = "test topic"
        
        with self.assertRaises(Exception):
            self.memory.retrieve()


if __name__ == '__main__':
    unittest.main() 