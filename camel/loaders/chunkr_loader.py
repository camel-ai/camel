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

import asyncio
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

if TYPE_CHECKING:
    from chunkr_ai.models import Configuration

from camel.loaders.base_loader import BaseLoader
from camel.logger import get_logger
from camel.utils import api_keys_required

logger = get_logger(__name__)


class ChunkrLoaderConfig:
    r"""Defines the parameters for configuring the task."""

    def __init__(
        self,
        chunk_processing: int = 512,
        high_resolution: bool = True,
        ocr_strategy: str = "Auto",
        **kwargs,
    ):
        self.chunk_processing = chunk_processing
        self.high_resolution = high_resolution
        self.ocr_strategy = ocr_strategy
        self.kwargs = kwargs


class ChunkrLoader(BaseLoader):
    r"""Chunkr Loader adhering to the unified BaseLoader interface."""

    @api_keys_required(
        [
            ("api_key", "CHUNKR_API_KEY"),
        ]
    )
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = "https://api.chunkr.ai/api/v1/task",
        **kwargs: Any,
    ) -> None:
        if config:
            api_key = config.get('api_key', api_key)
            url = config.get('url', url)

        super().__init__(config=config)

        from chunkr_ai import Chunkr

        self._api_key = api_key or os.environ.get("CHUNKR_API_KEY")
        self.url = url
        self._chunkr = Chunkr(api_key=self._api_key)

    @property
    def supported_formats(self) -> set[str]:
        return {"pdf", "jpg", "jpeg", "png", "doc", "docx"}

    def _load_single(
        self, source: Union[str, Path], **kwargs: Any
    ) -> Dict[str, Any]:
        r"""Synchronous wrapper that submits the task and waits for the output."""  # noqa: E501
        file_path = str(source)
        chunkr_config = kwargs.get("chunkr_config")

        async def _process_and_poll():
            task_id = await self.submit_task(file_path, chunkr_config)
            return await self.get_task_output(task_id)

        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                import nest_asyncio  # type: ignore[import-untyped]

                nest_asyncio.apply()

            result = loop.run_until_complete(_process_and_poll())
            return {"content": result, "source": file_path}
        except Exception as e:
            raise RuntimeError(f"Failed to load {file_path} via Chunkr: {e}")

    async def submit_task(
        self,
        file_path: str,
        chunkr_config: Optional[ChunkrLoaderConfig] = None,
    ) -> str:
        r"""Submits a file to the Chunkr API and returns the task ID."""
        chunkr_config = self._to_chunkr_configuration(
            chunkr_config or ChunkrLoaderConfig()
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
        r"""Polls the Chunkr API to check the task status and returns the task result."""  # noqa: E501
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
        r"""Pretty prints the JSON response."""
        from datetime import datetime

        return json.dumps(
            response_json,
            default=lambda o: o.isoformat()
            if isinstance(o, datetime)
            else None,
            indent=4,
        )

    def _to_chunkr_configuration(
        self, chunkr_config: ChunkrLoaderConfig
    ) -> "Configuration":
        r"""Converts the ChunkrLoaderConfig to Chunkr Configuration."""
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
            **chunkr_config.kwargs,
        )
