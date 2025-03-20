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
from datetime import datetime
from uuid import UUID

from camel.memories import (
    AgentMemory,
    BaseContextCreator,
    Mem0Memory,
    MemoryRecord,
    ContextRecord,
)
from camel.messages import BaseMessage
from camel.storages import Mem0Storage
from camel.types import OpenAIBackendRole, RoleType


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

    def test_agent_id_property(self):
        """Test agent_id property and setter."""
        # Set agent_id
        test_id = "new_agent_id"
        self.memory.agent_id = test_id
        # Verify it was set correctly
        self.assertEqual(self.memory.agent_id, test_id)

    def test_initialization_without_storage(self):
        """Test initialization without providing storage."""
        with patch('camel.memories.agent_memories.Mem0Storage') as mock_storage_class:
            memory = Mem0Memory(
                context_creator=self.context_creator,
                api_key=self.api_key,
            )
            mock_storage_class.assert_called_once_with(
                api_key=self.api_key,
                agent_id=None,
                user_id=None,
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
        
        # Create mock memory records
        mock_memory_record1 = MemoryRecord(
            uuid=UUID("123e4567-e89b-12d3-a456-426614174000"),
            message=BaseMessage(
                role_name="user",
                role_type=RoleType.USER,
                meta_dict={},
                content="test content 1"
            ),
            role_at_backend=OpenAIBackendRole.USER,
            extra_info={"type": "test1"},
            timestamp=datetime.fromisoformat("2023-01-01T00:00:00").timestamp(),
            agent_id="test_agent"
        )
        
        mock_memory_record2 = MemoryRecord(
            uuid=UUID("123e4567-e89b-12d3-a456-426614174001"),
            message=BaseMessage(
                role_name="assistant",
                role_type=RoleType.ASSISTANT,
                meta_dict={},
                content="test content 2"
            ),
            role_at_backend=OpenAIBackendRole.ASSISTANT,
            extra_info={"type": "test2"},
            timestamp=datetime.fromisoformat("2023-01-02T00:00:00").timestamp(),
            agent_id="test_agent"
        )
        
        # Mock the storage.search return value in the format expected by Mem0Memory.retrieve
        self.mock_storage.search.return_value = [
            {"memory_record": mock_memory_record1, "score": 0.9},
            {"memory_record": mock_memory_record2, "score": 0.8},
        ]

        results = self.memory.retrieve()

        self.mock_storage.search.assert_called_once_with(
            query="test topic",
            limit=self.retrieve_limit,
        )
        
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], ContextRecord)
        self.assertEqual(results[0].memory_record, mock_memory_record1)
        self.assertEqual(results[0].score, 0.9)
        self.assertEqual(results[1].memory_record, mock_memory_record2)
        self.assertEqual(results[1].score, 0.8)

    def test_write_records(self):
        """Test writing memory records."""
        # Create test messages
        user_message = BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict={},
            content="test user content"
        )
        
        assistant_message = BaseMessage(
            role_name="assistant",
            role_type=RoleType.ASSISTANT,
            meta_dict={},
            content="test assistant content"
        )
        
        # Create memory records
        records = [
            MemoryRecord(
                role_at_backend=OpenAIBackendRole.USER,
                message=user_message
            ),
            MemoryRecord(
                role_at_backend=OpenAIBackendRole.ASSISTANT,
                message=assistant_message
            ),
        ]

        self.memory.write_records(records)

        # Verify current topic is updated from user message
        self.assertEqual(self.memory._current_topic, "test user content")

        # Verify storage.add is called with correct format
        self.mock_storage.add.assert_called_once()
        call_args = self.mock_storage.add.call_args[0][0]
        
        self.assertEqual(len(call_args), 2)
        self.assertEqual(call_args[0]["role"], OpenAIBackendRole.USER)
        self.assertEqual(call_args[0]["content"], "test user content")
        self.assertEqual(call_args[1]["role"], OpenAIBackendRole.ASSISTANT)
        self.assertEqual(call_args[1]["content"], "test assistant content")

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