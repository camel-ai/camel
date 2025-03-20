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
import unittest
from unittest.mock import patch, MagicMock

import pytest

from camel.storages import BaseTextStorage, Mem0Storage
from camel.types import OpenAIBackendRole
from camel.memories.records import MemoryRecord


class TestMem0Storage(unittest.TestCase):
    """Unit tests for the Mem0Storage class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.api_key = "test_api_key"
        self.user_id = "test_user"
        self.agent_id = "test_agent"
        self.metadata = {"test_key": "test_value"}
        
        # Create a mock for the Mem0 client
        self.mock_mem0_client = MagicMock()
        self.patcher = patch('camel.storages.text_storages.mem0_cloud.MemoryClient', 
                           return_value=self.mock_mem0_client)
        self.patcher.start()
        
        # Initialize storage with test parameters
        self.storage = Mem0Storage(
            api_key=self.api_key,
            user_id=self.user_id,
            agent_id=self.agent_id,
            metadata=self.metadata,
        )

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        self.patcher.stop()

    def test_initialization(self):
        """Test proper initialization of Mem0Storage."""
        self.assertIsInstance(self.storage, BaseTextStorage)
        self.assertEqual(self.storage.user_id, self.user_id)
        self.assertEqual(self.storage.agent_id, self.agent_id)
        self.assertEqual(self.storage.metadata, self.metadata)

    def test_initialization_without_optional_params(self):
        """Test initialization without optional parameters."""
        storage = Mem0Storage(api_key=self.api_key)
        self.assertIsNotNone(storage)
        self.assertIsNone(storage.user_id)
        self.assertIsNone(storage.agent_id)
        self.assertEqual(storage.metadata, {})

    def test_add_single_memory(self):
        """Test adding a single memory record."""
        memory = "test memory"
        self.storage.add(memory)
        self.mock_mem0_client.add.assert_called_once()
        # Verify that the correct message format was passed
        args, kwargs = self.mock_mem0_client.add.call_args
        self.assertEqual(args[0], [{"role": "user", "content": memory}])

    def test_add_multiple_memories(self):
        """Test adding multiple memory records."""
        memories = [
            {"role": OpenAIBackendRole.USER, "content": "memory1"},
            {"role": OpenAIBackendRole.ASSISTANT, "content": "memory2"},
        ]
        self.storage.add(memories)
        self.mock_mem0_client.add.assert_called_once()
        # Verify that the correct message format was passed
        args, kwargs = self.mock_mem0_client.add.call_args
        expected_messages = [
            {"role": "user", "content": "memory1"},
            {"role": "assistant", "content": "memory2"},
        ]
        self.assertEqual(args[0], expected_messages)

    def test_search(self):
        """Test searching memories."""
        query = "test query"
        limit = 5
        # Mock search result format from the Mem0 client
        self.mock_mem0_client.search.return_value = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000", 
                "memory": "result1", 
                "metadata": {"type": "test1"}, 
                "created_at": "2023-01-01T00:00:00",
                "score": 0.9,
                "agent_id": "test_agent"
            },
            {
                "id": "123e4567-e89b-12d3-a456-426614174001", 
                "memory": "result2", 
                "metadata": {"type": "test2"}, 
                "created_at": "2023-01-02T00:00:00",
                "score": 0.8,
                "agent_id": "test_agent"
            },
        ]
        
        results = self.storage.search(query, limit=limit)
        
        self.mock_mem0_client.search.assert_called_once()
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results, list)
        
        # Check that results are properly transformed to include MemoryRecord objects
        for result in results:
            self.assertIn("memory_record", result)
            self.assertIn("score", result)
            self.assertIsInstance(result["memory_record"], MemoryRecord)
            self.assertIsInstance(result["score"], float)

    def test_get_all(self):
        """Test retrieving all memories."""
        self.mock_mem0_client.getAll.return_value = {
            "memories": [
                {"id": "id1", "memory": "memory1", "created_at": "2023-01-01T00:00:00"},
                {"id": "id2", "memory": "memory2", "created_at": "2023-01-02T00:00:00"},
            ],
            "total": 2,
            "page": 1,
            "page_size": 100
        }
        
        results = self.storage.get_all()
        
        self.mock_mem0_client.getAll.assert_called_once()
        self.assertIsInstance(results, dict)
        self.assertIn("memories", results)
        self.assertIn("total", results)
        self.assertIn("page", results)
        self.assertIn("page_size", results)
        self.assertEqual(len(results["memories"]), 2)

    def test_delete_by_ids(self):
        """Test deleting memories by IDs."""
        memory_ids = ["id1", "id2"]
        self.storage.delete(memory_ids=memory_ids)
        self.mock_mem0_client.batchDelete.assert_called_once()
        # Verify correct format of delete request
        args, kwargs = self.mock_mem0_client.batchDelete.call_args
        expected_delete_data = [{"memory_id": "id1"}, {"memory_id": "id2"}]
        self.assertEqual(args[0], expected_delete_data)

    def test_delete_by_filters(self):
        """Test deleting memories by filters."""
        filters = {"tags": ["test_tag"]}
        self.storage.delete(filters=filters)
        self.mock_mem0_client.delete_users.assert_called_once()

    def test_update(self):
        """Test updating a memory."""
        memory_id = "test_id"
        content = "updated memory"
        metadata = {"new_key": "new_value"}
        self.storage.update(memory_id, content, metadata)
        self.mock_mem0_client.update.assert_called_once()
        
        # Verify correct format of update request
        args, kwargs = self.mock_mem0_client.update.call_args
        self.assertEqual(args[0], memory_id)
        expected_update = {
            "memory_id": memory_id, 
            "text": {"role": "user", "content": content},
            "metadata": metadata
        }
        self.assertEqual(args[1], expected_update)

    def test_update_with_dict_content(self):
        """Test updating a memory with dictionary content."""
        memory_id = "test_id"
        content = {"role": "assistant", "content": "updated memory"}
        self.storage.update(memory_id, content)
        self.mock_mem0_client.update.assert_called_once()
        
        # Verify correct format of update request
        args, kwargs = self.mock_mem0_client.update.call_args
        expected_update = {
            "memory_id": memory_id, 
            "text": content
        }
        self.assertEqual(args[1], expected_update)

    def test_error_handling(self):
        """Test error handling for API failures."""
        self.mock_mem0_client.add.side_effect = Exception("API Error")
        
        result = self.storage.add({"role": OpenAIBackendRole.USER, "content": "test"})
        self.assertIn("error", result)
        self.assertEqual(result["error"], "API Error")

    @pytest.mark.skipif(not os.getenv("MEM0_API_KEY"), 
                       reason="MEM0_API_KEY not set")
    def test_integration(self):
        """Integration test with actual Mem0 API.
        
        This test is skipped unless MEM0_API_KEY environment variable is set.
        """
        api_key = os.getenv("MEM0_API_KEY")
        storage = Mem0Storage(api_key=api_key)
        
        # Test full workflow
        memory = "integration test memory"
        storage.add(memory)
        
        results = storage.search("integration test")
        self.assertGreater(len(results), 0)
        
        storage.delete()  # Clean up


if __name__ == '__main__':
    unittest.main() 