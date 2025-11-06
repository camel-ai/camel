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
from unittest.mock import AsyncMock, MagicMock, patch

from chunkr_ai.models import Status

from camel.loaders import ChunkrReader, ChunkrReaderConfig


class TestChunkrReader(unittest.IsolatedAsyncioTestCase):
    @patch('chunkr_ai.Chunkr')
    def setUp(self, mock_chunkr_class):
        self.reader = ChunkrReader(api_key="fake_api_key")
        self.mock_chunkr = self.reader._chunkr

    @patch('chunkr_ai.Chunkr')
    async def test_submit_task_success(self, mock_chunkr_class):
        mock_chunkr_instance = self.mock_chunkr
        mock_task = AsyncMock()
        mock_task.task_id = "12345"
        mock_chunkr_instance.create_task = AsyncMock(return_value=mock_task)

        task_id = await self.reader.submit_task("fake_path.pdf")

        self.assertEqual(task_id, "12345")
        mock_chunkr_instance.create_task.assert_called_once()

    @patch('chunkr_ai.Chunkr')
    async def test_submit_task_with_config(self, mock_chunkr_class):
        mock_chunkr_instance = self.mock_chunkr
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
        mock_chunkr_instance = self.mock_chunkr
        mock_chunkr_instance.create_task = AsyncMock(side_effect=Exception())

        with self.assertRaises(ValueError) as context:
            await self.reader.submit_task("fake_path.pdf")

        self.assertIn("Failed to submit task", str(context.exception))
        mock_chunkr_instance.create_task.assert_called_once()

    @patch('chunkr_ai.Chunkr')
    async def test_get_task_output_success(self, mock_chunkr_class):
        mock_chunkr_instance = self.mock_chunkr
        mock_task = AsyncMock()
        mock_task.status = Status.SUCCEEDED
        mock_task.json = MagicMock(return_value={"status": "Succeeded"})
        mock_task.poll = AsyncMock()
        mock_chunkr_instance.get_task = AsyncMock(return_value=mock_task)

        result = await self.reader.get_task_output("test_task_id")

        expected_result = json.dumps({"status": "Succeeded"}, indent=4)
        self.assertEqual(result, expected_result)
        mock_chunkr_instance.get_task.assert_called_once_with("test_task_id")
        mock_task.poll.assert_called_once()

    @patch('chunkr_ai.Chunkr')
    async def test_get_task_output_failed(self, mock_chunkr_class):
        mock_chunkr_instance = self.mock_chunkr
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
        mock_chunkr_instance = self.mock_chunkr
        mock_chunkr_instance.get_task = AsyncMock(side_effect=Exception())

        with self.assertRaises(ValueError) as context:
            await self.reader.get_task_output("test_task_id")

        self.assertIn("Failed to get task by task id", str(context.exception))
        mock_chunkr_instance.get_task.assert_called_once_with("test_task_id")

    @patch('chunkr_ai.Chunkr')
    async def test_get_task_output_poll_error(self, mock_chunkr_class):
        mock_chunkr_instance = self.mock_chunkr
        mock_task = AsyncMock()
        mock_task.poll = AsyncMock(side_effect=Exception())
        mock_chunkr_instance.get_task = AsyncMock(return_value=mock_task)

        with self.assertRaises(ValueError) as context:
            await self.reader.get_task_output("test_task_id")

        self.assertIn("Failed to retrieve task status", str(context.exception))
        mock_chunkr_instance.get_task.assert_called_once_with("test_task_id")
        mock_task.poll.assert_called_once()

    def test_chunkr_reader_config_defaults(self):
        """Test ChunkrReaderConfig with default values."""
        config = ChunkrReaderConfig()

        self.assertEqual(config.chunk_processing, 512)
        self.assertEqual(config.high_resolution, True)
        self.assertEqual(config.ocr_strategy, "Auto")
        self.assertEqual(config.kwargs, {})

    def test_chunkr_reader_config_custom_values(self):
        """Test ChunkrReaderConfig with custom values."""
        config = ChunkrReaderConfig(
            chunk_processing=1024,
            high_resolution=False,
            ocr_strategy="All",
        )

        self.assertEqual(config.chunk_processing, 1024)
        self.assertEqual(config.high_resolution, False)
        self.assertEqual(config.ocr_strategy, "All")

    def test_chunkr_reader_config_with_kwargs(self):
        """Test ChunkrReaderConfig with additional kwargs."""
        config = ChunkrReaderConfig(
            chunk_processing=2048,
            expires_in=3600,
            pipeline="custom_pipeline",
        )

        self.assertEqual(config.chunk_processing, 2048)
        self.assertEqual(config.kwargs["expires_in"], 3600)
        self.assertEqual(config.kwargs["pipeline"], "custom_pipeline")

    @patch('chunkr_ai.models.Configuration')
    @patch('chunkr_ai.models.ChunkProcessing')
    @patch('chunkr_ai.models.OcrStrategy')
    def test_to_chunkr_configuration_auto_strategy(
        self, mock_ocr_strategy, mock_chunk_processing, mock_configuration
    ):
        """Test _to_chunkr_configuration with Auto OCR strategy."""
        config = ChunkrReaderConfig(
            chunk_processing=512, high_resolution=True, ocr_strategy="Auto"
        )

        mock_chunk_processing_instance = MagicMock()
        mock_chunk_processing.return_value = mock_chunk_processing_instance
        mock_ocr_strategy.AUTO = "AUTO"

        self.reader._to_chunkr_configuration(config)

        mock_chunk_processing.assert_called_once_with(target_length=512)
        mock_configuration.assert_called_once_with(
            chunk_processing=mock_chunk_processing_instance,
            high_resolution=True,
            ocr_strategy="AUTO",
        )

    @patch('chunkr_ai.models.Configuration')
    @patch('chunkr_ai.models.ChunkProcessing')
    @patch('chunkr_ai.models.OcrStrategy')
    def test_to_chunkr_configuration_with_kwargs(
        self, mock_ocr_strategy, mock_chunk_processing, mock_configuration
    ):
        """Test _to_chunkr_configuration with additional kwargs."""
        config = ChunkrReaderConfig(
            chunk_processing=512,
            high_resolution=True,
            ocr_strategy="Auto",
            expires_in=7200,
            pipeline="test_pipeline",
        )

        mock_chunk_processing_instance = MagicMock()
        mock_chunk_processing.return_value = mock_chunk_processing_instance
        mock_ocr_strategy.AUTO = "AUTO"

        self.reader._to_chunkr_configuration(config)

        mock_chunk_processing.assert_called_once_with(target_length=512)
        mock_configuration.assert_called_once_with(
            chunk_processing=mock_chunk_processing_instance,
            high_resolution=True,
            ocr_strategy="AUTO",
            expires_in=7200,
            pipeline="test_pipeline",
        )


if __name__ == "__main__":
    unittest.main()
