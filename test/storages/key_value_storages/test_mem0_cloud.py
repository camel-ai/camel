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
from unittest.mock import MagicMock, patch

import pytest

from camel.storages.key_value_storages import BaseKeyValueStorage, Mem0Storage
from camel.types import OpenAIBackendRole


class TestMem0Storage(unittest.TestCase):
    r"""Unit tests for the Mem0Storage class."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.api_key = "test_api_key"
        self.user_id = "test_user"
        self.agent_id = "test_agent"
        self.metadata = {"test_key": "test_value"}

        # Create a mock for the Mem0 client
        self.mock_mem0_client = MagicMock()
        self.patcher = patch(
            'mem0.MemoryClient', return_value=self.mock_mem0_client
        )
        self.patcher.start()

        # Initialize storage with test parameters
        self.storage = Mem0Storage(
            api_key=self.api_key,
            agent_id=self.agent_id,
            user_id=self.user_id,
            metadata=self.metadata,
        )

    def tearDown(self):
        r"""Clean up test fixtures after each test method."""
        self.patcher.stop()

    def test_initialization(self):
        r"""Test proper initialization of Mem0Storage."""
        self.assertIsInstance(self.storage, BaseKeyValueStorage)
        self.assertEqual(self.storage.user_id, self.user_id)
        self.assertEqual(self.storage.agent_id, self.agent_id)
        self.assertEqual(self.storage.metadata, self.metadata)

    def test_initialization_required_agent_id(self):
        r"""Test initialization with required agent_id parameter."""
        storage = Mem0Storage(api_key=self.api_key, agent_id="required_agent")
        self.assertIsNotNone(storage)
        self.assertIsNone(storage.user_id)
        self.assertEqual(storage.agent_id, "required_agent")
        self.assertEqual(storage.metadata, {})

    def test_save(self):
        r"""Test saving records to Mem0 storage."""
        # Create test records
        records = [
            {
                "message": {"content": "test message 1"},
                "role_at_backend": OpenAIBackendRole.USER,
            },
            {
                "message": {"content": "test message 2"},
                "role_at_backend": OpenAIBackendRole.ASSISTANT,
            },
        ]

        # Test the save method
        self.storage.save(records)

        # Verify that client.add was called with correct parameters
        self.mock_mem0_client.add.assert_called_once()
        args, kwargs = self.mock_mem0_client.add.call_args

        # Check that messages were formatted correctly
        expected_messages = [
            {"role": "user", "content": "test message 1"},
            {"role": "assistant", "content": "test message 2"},
        ]
        self.assertEqual(args[0], expected_messages)

        # Check that options were passed correctly
        self.assertEqual(kwargs.get("agent_id"), self.agent_id)
        self.assertEqual(kwargs.get("user_id"), self.user_id)
        self.assertEqual(kwargs.get("metadata"), self.metadata)

    def test_load(self):
        r"""Test loading records from Mem0 storage."""
        # Setup mock return value
        mock_results = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "memory": "test memory 1",
                "metadata": {"key1": "value1"},
                "created_at": "2023-01-01T00:00:00",
                "agent_id": self.agent_id,
            },
            {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "memory": "test memory 2",
                "metadata": {"key2": "value2"},
                "created_at": "2023-01-02T00:00:00",
                "agent_id": self.agent_id,
            },
        ]
        self.mock_mem0_client.get_all.return_value = mock_results

        # Call load method
        results = self.storage.load()

        # Verify client.get_all was called with correct parameters
        self.mock_mem0_client.get_all.assert_called_once()
        args, kwargs = self.mock_mem0_client.get_all.call_args
        self.assertEqual(kwargs.get("version"), "v2")

        # Check that results were transformed correctly
        self.assertEqual(len(results), 2)
        for idx, result in enumerate(results):
            self.assertIn("uuid", result)
            self.assertIn("message", result)
            self.assertIn("role_at_backend", result)
            self.assertIn("extra_info", result)
            self.assertIn("timestamp", result)
            self.assertIn("agent_id", result)

            # Verify specific fields
            self.assertEqual(result["agent_id"], self.agent_id)
            self.assertEqual(
                result["message"]["content"], mock_results[idx]["memory"]
            )

    def test_clear(self):
        r"""Test clearing all records from Mem0 storage."""
        # Call clear method
        self.storage.clear()

        # Verify client.delete_users was called with correct parameters
        self.mock_mem0_client.delete_users.assert_called_once()
        args, kwargs = self.mock_mem0_client.delete_users.call_args

        # Check that filters were built correctly
        filters = {
            'AND': [{'agent_id': self.agent_id}, {'user_id': self.user_id}]
        }
        for key, value in filters.items():
            self.assertIn(key, kwargs)
            self.assertEqual(kwargs[key], value)

    def test_error_handling_save(self):
        r"""Test error handling for save method."""
        self.mock_mem0_client.add.side_effect = Exception("API Error")

        records = [
            {
                "message": {"content": "test message"},
                "role_at_backend": OpenAIBackendRole.USER,
            }
        ]

        # The method doesn't return anything, it just logs the error
        with self.assertLogs(level='ERROR') as log_context:
            self.storage.save(records)

        # Check that the error was logged
        self.assertTrue(
            any(
                "Error adding memory: API Error" in message
                for message in log_context.output
            )
        )

    def test_error_handling_load(self):
        r"""Test error handling for load method."""
        self.mock_mem0_client.get_all.side_effect = Exception("API Error")

        results = self.storage.load()
        self.assertEqual(results, [])

    def test_error_handling_clear(self):
        r"""Test error handling for clear method."""
        self.mock_mem0_client.delete_users.side_effect = Exception("API Error")

        # The method doesn't return anything, it just logs the error
        with self.assertLogs(level='ERROR') as log_context:
            self.storage.clear()

        # Check that the error was logged
        self.assertTrue(
            any(
                "Error deleting memories: API Error" in message
                for message in log_context.output
            )
        )

    def test_prepare_messages(self):
        r"""Test message preparation helper method."""
        records = [
            {
                "message": {"content": "test message 1"},
                "role_at_backend": OpenAIBackendRole.USER,
            },
            {
                "message": {"content": "test message 2"},
                "role_at_backend": OpenAIBackendRole.ASSISTANT,
            },
        ]

        messages = self.storage._prepare_messages(records)

        expected_messages = [
            {"role": "user", "content": "test message 1"},
            {"role": "assistant", "content": "test message 2"},
        ]

        self.assertEqual(messages, expected_messages)

    @pytest.mark.skipif(
        not os.getenv("MEM0_API_KEY"), reason="MEM0_API_KEY not set"
    )
    def test_integration(self):
        r"""Integration test with actual Mem0 API.

        This test is skipped unless MEM0_API_KEY environment variable is set.
        """
        api_key = os.getenv("MEM0_API_KEY")
        agent_id = "integration_test_agent"
        storage = Mem0Storage(api_key=api_key, agent_id=agent_id)

        # Test full workflow
        records = [
            {
                "message": {"content": "integration test memory"},
                "role_at_backend": OpenAIBackendRole.USER,
            }
        ]

        # Save record
        storage.save(records)

        # Load records
        loaded_records = storage.load()
        self.assertGreater(len(loaded_records), 0)

        # Clear storage
        storage.clear()


if __name__ == '__main__':
    unittest.main()
