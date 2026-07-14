# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import os
import unittest
from unittest.mock import MagicMock, patch

import httpx
import pytest

from camel.storages.key_value_storages import BaseKeyValueStorage, MemantoStorage
from camel.types import OpenAIBackendRole

AGENT_ID = "my-camel-agent"
BASE_URL = os.getenv("MEMANTO_BASE_URL", "http://127.0.0.1:8000")


def _memanto_server_available() -> bool:
    try:
        response = httpx.get(f"{BASE_URL.rstrip('/')}/health", timeout=3.0)
        return response.status_code == 200
    except Exception:
        return False


class TestMemantoStorage(unittest.TestCase):
    r"""Unit tests for the MemantoStorage class."""

    def setUp(self):
        self.agent_id = "test_agent"
        self.mock_client = MagicMock()
        self.mock_client.recall_recent.return_value = [
            {
                "id": "mem-123",
                "content": "user: hello",
                "type": "context",
                "created_at": "2023-01-01T00:00:00Z",
            }
        ]

        patcher = patch(
            "camel.storages.key_value_storages.memanto.MemantoRESTClient",
            return_value=self.mock_client,
        )
        self.client_patcher = patcher
        self.client_patcher.start()
        self.storage = MemantoStorage(agent_id=self.agent_id)

    def tearDown(self):
        self.client_patcher.stop()

    def test_initialization(self):
        self.assertIsInstance(self.storage, BaseKeyValueStorage)
        self.assertEqual(self.storage.agent_id, self.agent_id)

    def test_initialization_requires_agent_id(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                MemantoStorage()

    def test_save(self):
        records = [
            {
                "message": {"content": "hello"},
                "role_at_backend": OpenAIBackendRole.USER,
            },
            {
                "message": {"content": "hi there"},
                "role_at_backend": OpenAIBackendRole.ASSISTANT,
            },
        ]

        self.storage.save(records)

        self.assertEqual(self.mock_client.remember.call_count, 2)
        first_call = self.mock_client.remember.call_args_list[0]
        self.assertEqual(first_call.kwargs["content"], "user: hello")
        self.assertEqual(first_call.kwargs["memory_type"], "context")

    def test_load(self):
        results = self.storage.load()

        self.mock_client.recall_recent.assert_called_once_with(
            limit=self.storage.recall_limit
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["message"]["content"], "user: hello")
        self.assertEqual(results[0]["agent_id"], self.agent_id)

    def test_clear(self):
        self.storage.clear()
        self.mock_client.clear_all_memories.assert_called_once()

    def test_error_handling_save(self):
        self.mock_client.remember.side_effect = Exception("API Error")
        records = [
            {
                "message": {"content": "hello"},
                "role_at_backend": OpenAIBackendRole.USER,
            }
        ]

        with self.assertLogs(level="ERROR") as log_context:
            self.storage.save(records)

        self.assertTrue(
            any(
                "Error saving memories to Memanto" in message
                for message in log_context.output
            )
        )

    def test_error_handling_load(self):
        self.mock_client.recall_recent.side_effect = Exception("API Error")
        results = self.storage.load()
        self.assertEqual(results, [])


@pytest.mark.skipif(
    not _memanto_server_available(),
    reason="Memanto server is not running at MEMANTO_BASE_URL",
)
class TestMemantoStorageIntegration(unittest.TestCase):
    r"""Live integration tests for MemantoStorage.

    Prerequisites:
        memanto serve
        memanto agent create my-camel-agent
    """

    def setUp(self):
        self.storage = MemantoStorage(
            agent_id=AGENT_ID,
            base_url=BASE_URL,
        )
        self.storage.clear()

    def test_save_and_load(self):
        records = [
            {
                "message": {"content": "CAMEL AI is a multi-agent framework."},
                "role_at_backend": OpenAIBackendRole.USER,
            },
            {
                "message": {"content": "Memanto stores persistent agent memory."},
                "role_at_backend": OpenAIBackendRole.ASSISTANT,
            },
        ]
        self.storage.save(records)

        loaded = self.storage.load()
        contents = [record["message"]["content"] for record in loaded]

        self.assertGreaterEqual(len(contents), 2)
        self.assertTrue(
            any("CAMEL AI" in content for content in contents),
            f"Expected CAMEL message in loaded records: {contents}",
        )


if __name__ == "__main__":
    unittest.main()
