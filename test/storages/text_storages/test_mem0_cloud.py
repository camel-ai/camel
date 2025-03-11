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
from typing import Dict, Any, List
from unittest.mock import patch, MagicMock

import pytest

from camel.storages import BaseMemoryStorage, Mem0Storage


class TestMem0Storage(unittest.TestCase):
    """Unit tests for the Mem0Storage class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.api_key = "test_api_key"
        self.user_id = "test_user"
        self.agent_id = "test_agent"
        self.run_id = "test_run"
        self.metadata = {"test_key": "test_value"}
        
        # Create a mock for the Mem0 client
        self.mock_mem0_client = MagicMock()
        self.patcher = patch('camel.storages.text_storages.mem0_cloud.Mem0Client', 
                           return_value=self.mock_mem0_client)
        self.patcher.start()
        
        # Initialize storage with test parameters
        self.storage = Mem0Storage(
            api_key=self.api_key,
            user_id=self.user_id,
            agent_id=self.agent_id,
            run_id=self.run_id,
            metadata=self.metadata,
        )

    def tearDown(self):
        """Clean up test fixtures after each test method."""
        self.patcher.stop()

    def test_initialization(self):
        """Test proper initialization of Mem0Storage."""
        self.assertIsInstance(self.storage, BaseMemoryStorage)
        self.assertEqual(self.storage.user_id, self.user_id)
        self.assertEqual(self.storage.agent_id, self.agent_id)
        self.assertEqual(self.storage.run_id, self.run_id)
        self.assertEqual(self.storage.metadata, self.metadata)

    def test_initialization_without_optional_params(self):
        """Test initialization without optional parameters."""
        storage = Mem0Storage(api_key=self.api_key)
        self.assertIsNotNone(storage)
        self.assertIsNone(storage.user_id)
        self.assertIsNone(storage.agent_id)
        self.assertIsNone(storage.run_id)
        self.assertEqual(storage.metadata, {})

    def test_add_single_memory(self):
        """Test adding a single memory record."""
        memory = {"text": "test memory", "metadata": {"type": "test"}}
        self.storage.add(memory)
        self.mock_mem0_client.add.assert_called_once()

    def test_add_multiple_memories(self):
        """Test adding multiple memory records."""
        memories = [
            {"text": "memory1", "metadata": {"type": "test1"}},
            {"text": "memory2", "metadata": {"type": "test2"}},
        ]
        self.storage.add(memories)
        self.mock_mem0_client.add.assert_called_once()

    def test_search(self):
        """Test searching memories."""
        query = "test query"
        limit = 5
        self.mock_mem0_client.search.return_value = [
            {"text": "result1", "metadata": {"score": 0.9}},
            {"text": "result2", "metadata": {"score": 0.8}},
        ]
        
        results = self.storage.search(query, limit=limit)
        
        self.mock_mem0_client.search.assert_called_once()
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results, list)

    def test_get_all(self):
        """Test retrieving all memories."""
        self.mock_mem0_client.get_all.return_value = [
            {"text": "memory1"},
            {"text": "memory2"},
        ]
        
        results = self.storage.get_all()
        
        self.mock_mem0_client.get_all.assert_called_once()
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results, list)

    def test_delete(self):
        """Test deleting memories."""
        self.storage.delete()
        self.mock_mem0_client.delete.assert_called_once()

    def test_update(self):
        """Test updating a memory."""
        memory_id = "test_id"
        updates = {"text": "updated memory"}
        self.storage.update(memory_id, updates)
        self.mock_mem0_client.update.assert_called_once_with(memory_id, updates)

    def test_batch_update(self):
        """Test batch updating memories."""
        updates = [
            {"id": "id1", "updates": {"text": "update1"}},
            {"id": "id2", "updates": {"text": "update2"}},
        ]
        self.storage.batch_update(updates)
        self.mock_mem0_client.batch_update.assert_called_once()

    def test_get_users(self):
        """Test retrieving users."""
        self.mock_mem0_client.get_users.return_value = ["user1", "user2"]
        users = self.storage.get_users()
        self.mock_mem0_client.get_users.assert_called_once()
        self.assertEqual(len(users), 2)
        self.assertIsInstance(users, list)

    def test_error_handling(self):
        """Test error handling for API failures."""
        self.mock_mem0_client.add.side_effect = Exception("API Error")
        
        with self.assertRaises(Exception):
            self.storage.add({"text": "test"})

    @pytest.mark.skipif(not os.getenv("MEM0_API_KEY"), 
                       reason="MEM0_API_KEY not set")
    def test_integration(self):
        """Integration test with actual Mem0 API.
        
        This test is skipped unless MEM0_API_KEY environment variable is set.
        """
        api_key = os.getenv("MEM0_API_KEY")
        storage = Mem0Storage(api_key=api_key)
        
        # Test full workflow
        memory = {"text": "integration test memory"}
        storage.add(memory)
        
        results = storage.search("integration test")
        self.assertGreater(len(results), 0)
        
        storage.delete()  # Clean up


if __name__ == '__main__':
    unittest.main() 