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
import os
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from chunkr_ai.models import Configuration

from camel.logger import get_logger
from camel.utils import api_keys_required

logger = get_logger(__name__)


class ChunkrReaderConfig:
    r"""Defines the parameters for configuring the task.

    Args:
        chunk_processing (int, optional): The target chunk length.
            (default: :obj:`512`)
        high_resolution (bool, optional): Whether to use high resolution OCR.
            (default: :obj:`True`)
        ocr_strategy (str, optional): The OCR strategy. Defaults to 'Auto'.
    """

    def __init__(
        self,
        chunk_processing: int = 512,
        high_resolution: bool = True,
        ocr_strategy: str = "Auto",
    ):
        self.chunk_processing = chunk_processing
        self.high_resolution = high_resolution
        self.ocr_strategy = ocr_strategy


class ChunkrReader:
    r"""Chunkr Reader for processing documents and returning content
    in various formats.

    Args:
        api_key (Optional[str], optional): The API key for Chunkr API. If not
            provided, it will be retrieved from the environment variable
            `CHUNKR_API_KEY`. (default: :obj:`None`)
        url (Optional[str], optional): The url to the Chunkr service.
            (default: :obj:`https://api.chunkr.ai/api/v1/task`)
        **kwargs (Any): Additional keyword arguments for request headers.
    """

    @api_keys_required(
        [
            ("api_key", "CHUNKR_API_KEY"),
        ]
    )
    def __init__(
        self,
        api_key: Optional[str] = None,
        url: Optional[str] = "https://api.chunkr.ai/api/v1/task",
    ) -> None:
        from chunkr_ai import Chunkr

        self._api_key = api_key or os.getenv('CHUNKR_API_KEY')
        self._chunkr = Chunkr(api_key=self._api_key)

    async def submit_task(
        self,
        file_path: str,
        chunkr_config: Optional[ChunkrReaderConfig] = None,
    ) -> str:
        r"""Submits a file to the Chunkr API and returns the task ID.

        Args:
            file_path (str): The path to the file to be uploaded.
            chunkr_config (ChunkrReaderConfig, optional): The configuration
                for the Chunkr API. Defaults to None.

        Returns:
            str: The task ID.
        """
        chunkr_config = self._to_chunkr_configuration(
            chunkr_config or ChunkrReaderConfig()
        )

        try:
            task = await self._chunkr.create_task(
                file=file_path, config=chunkr_config
            )
            logger.info(
                f"Task submitted successfully. Task ID: {task.task_id}"
            )
            return task.task_id
        except Exception as e:
            logger.error(f"Failed to submit task: {e}")
            raise ValueError(f"Failed to submit task: {e}") from e

    async def get_task_output(self, task_id: str) -> str | None:
        r"""Polls the Chunkr API to check the task status and returns the task
        result.

        Args:
            task_id (str): The task ID to check the status for.

        Returns:
            Optional[str]: The formatted task result in JSON format, or `None`
                if the task fails or is canceld.
        """
        from chunkr_ai.models import Status

        try:
            task = await self._chunkr.get_task(task_id)
        except Exception as e:
            logger.error(f"Failed to get task by task id: {task_id}: {e}")
            raise ValueError(
                f"Failed to get task by task id: {task_id}: {e}"
            ) from e

        try:
            await task.poll()
            if task.status == Status.SUCCEEDED:
                logger.info(f"Task {task_id} completed successfully.")
                return self._pretty_print_response(task.json())
            elif task.status == Status.FAILED:
                logger.warning(
                    f"Task {task_id} encountered an error: {task.message}"
                )
                return None
            else:
                logger.warning(f"Task {task_id} was manually cancelled.")
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve task status: {e}")
            raise ValueError(f"Failed to retrieve task status: {e}") from e

    def _pretty_print_response(self, response_json: dict) -> str:
        r"""Pretty prints the JSON response.

        Args:
            response_json (dict): The response JSON to pretty print.

        Returns:
            str: Formatted JSON as a string.
        """
        from datetime import datetime

        return json.dumps(
            response_json,
            default=lambda o: o.isoformat()
            if isinstance(o, datetime)
            else None,
            indent=4,
        )

    def _to_chunkr_configuration(
        self, chunkr_config: ChunkrReaderConfig
    ) -> "Configuration":
        r"""Converts the ChunkrReaderConfig to Chunkr Configuration.

        Args:
            chunkr_config (ChunkrReaderConfig):
                The ChunkrReaderConfig to convert.

        Returns:
            Configuration: Chunkr SDK configuration.
        """
        from chunkr_ai.models import (
            ChunkProcessing,
            Configuration,
            OcrStrategy,
        )

        return Configuration(
            chunk_processing=ChunkProcessing(
                target_length=chunkr_config.chunk_processing
            ),
            high_resolution=chunkr_config.high_resolution,
            ocr_strategy={
                "Auto": OcrStrategy.AUTO,
                "All": OcrStrategy.ALL,
            }.get(chunkr_config.ocr_strategy, OcrStrategy.ALL),
        )
