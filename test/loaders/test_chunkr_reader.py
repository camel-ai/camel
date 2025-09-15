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

import json
import unittest
from unittest.mock import AsyncMock, patch

from chunkr_ai.models import Status

from camel.loaders import ChunkrReader, ChunkrReaderConfig


class TestChunkrReader(unittest.TestCase):
    def setUp(self):
        with patch('chunkr_ai.Chunkr'):
            self.reader = ChunkrReader(api_key="fake_api_key")

    @patch('chunkr_ai.Chunkr')
    async def test_submit_task_success(self, mock_chunkr_class):
        mock_chunkr_instance = mock_chunkr_class.return_value
        mock_task = AsyncMock()
        mock_task.task_id = "12345"
        mock_chunkr_instance.create_task = AsyncMock(return_value=mock_task)

        task_id = await self.reader.submit_task("fake_path.pdf")

        self.assertEqual(task_id, "12345")
        mock_chunkr_instance.create_task.assert_called_once()

    @patch('chunkr_ai.Chunkr')
    async def test_submit_task_with_config(self, mock_chunkr_class):
        mock_chunkr_instance = mock_chunkr_class.return_value
        mock_task = AsyncMock()
        mock_task.task_id = "12345"
        mock_chunkr_instance.create_task = AsyncMock(return_value=mock_task)

        config = ChunkrReaderConfig()
        config.chunk_processing = 1024

        task_id = await self.reader.submit_task("fake_path.pdf", config)

        self.assertEqual(task_id, "12345")
        mock_chunkr_instance.create_task.assert_called_once()

    @patch('chunkr_ai.Chunkr')
    async def test_submit_task_failure(self, mock_chunkr_class):
        mock_chunkr_instance = mock_chunkr_class.return_value
        mock_chunkr_instance.create_task = AsyncMock(side_effect=Exception())

        with self.assertRaises(ValueError) as context:
            await self.reader.submit_task("fake_path.pdf")

        self.assertIn("Failed to submit task", str(context.exception))
        mock_chunkr_instance.create_task.assert_called_once()

    @patch('chunkr_ai.Chunkr')
    async def test_get_task_output_success(self, mock_chunkr_class):
        mock_chunkr_instance = mock_chunkr_class.return_value
        mock_task = AsyncMock()
        mock_task.status = Status.SUCCEEDED
        mock_task.json.return_value = {"status": "Succeeded"}
        mock_task.poll = AsyncMock()
        mock_chunkr_instance.get_task = AsyncMock(return_value=mock_task)

        result = await self.reader.get_task_output("test_task_id")

        expected_result = json.dumps({"status": "Succeeded"}, indent=4)
        self.assertEqual(result, expected_result)
        mock_chunkr_instance.get_task.assert_called_once_with("test_task_id")
        mock_task.poll.assert_called_once()

    @patch('chunkr_ai.Chunkr')
    async def test_get_task_output_failed(self, mock_chunkr_class):
        mock_chunkr_instance = mock_chunkr_class.return_value
        mock_task = AsyncMock()
        mock_task.status = Status.FAILED
        mock_task.poll = AsyncMock()
        mock_chunkr_instance.get_task = AsyncMock(return_value=mock_task)

        result = await self.reader.get_task_output("test_task_id")

        self.assertEqual(result, None)
        mock_chunkr_instance.get_task.assert_called_once_with("test_task_id")
        mock_task.poll.assert_called_once()

    @patch('chunkr_ai.Chunkr')
    async def test_get_task_output_get_task_error(self, mock_chunkr_class):
        mock_chunkr_instance = mock_chunkr_class.return_value
        mock_chunkr_instance.get_task = AsyncMock(side_effect=Exception())

        with self.assertRaises(ValueError) as context:
            await self.reader.get_task_output("test_task_id")

        self.assertIn("Failed to get task by task id", str(context.exception))
        mock_chunkr_instance.get_task.assert_called_once_with("test_task_id")

    @patch('chunkr_ai.Chunkr')
    async def test_get_task_output_poll_error(self, mock_chunkr_class):
        mock_chunkr_instance = mock_chunkr_class.return_value
        mock_task = AsyncMock()
        mock_task.poll = AsyncMock(side_effect=Exception())
        mock_chunkr_instance.get_task = AsyncMock(return_value=mock_task)

        with self.assertRaises(ValueError) as context:
            await self.reader.get_task_output("test_task_id")

        self.assertIn("Failed to retrieve task status", str(context.exception))
        mock_chunkr_instance.get_task.assert_called_once_with("test_task_id")
        mock_task.poll.assert_called_once()


if __name__ == "__main__":
    unittest.main()
