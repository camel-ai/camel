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

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.utils import BatchProcessor

logger = get_logger(__name__)


class ExtractorStrategy(ABC):
    r"""Abstract base class for extraction strategies."""

    @abstractmethod
    async def extract(self, text: str) -> Optional[str]:
        r"""Asynchronously extracts relevant parts from text.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: Extracted str if successful, otherwise None.
        """
        pass


class Extractor:
    r"""Base class for response extractors with a fixed strategy pipeline.

    This extractor:
    - Uses a **fixed multi-stage pipeline** of extraction strategies.
    - Tries **each strategy in order** within a stage until one succeeds.
    - Feeds the **output of one stage into the next** for processing.
    - Supports **async execution** for efficient processing.
    - Provides **batch processing and resource monitoring** options.
    """

    def __init__(
        self,
        pipeline: List[List[ExtractorStrategy]],
        cache_templates: bool = True,
        max_cache_size: int = 1000,
        extraction_timeout: float = 30.0,
        batch_size: int = 10,
        monitoring_interval: float = 5.0,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        **kwargs,
    ):
        r"""Initialize the extractor with a multi-stage strategy pipeline.

        Args:
            pipeline (List[List[ExtractorStrategy]]):
                A fixed list of lists where each list represents a stage
                containing extractor strategies executed in order.
            cache_templates (bool, optional):
                Whether to enable caching for extraction templates.
                Defaults to True.
            max_cache_size (int, optional):
                Maximum number of cached templates. Defaults to 1000.
            extraction_timeout (float, optional):
                Maximum time allowed for an extraction in seconds.
                Defaults to 30.0.
            batch_size (int, optional):
                Number of responses processed in parallel per batch.
                Defaults to 10.
            monitoring_interval (float, optional):
                Interval (in seconds) for checking resource usage.
                Defaults to 5.0.
            cpu_threshold (float, optional):
                CPU usage percentage threshold for scaling down operations.
                Defaults to 80.0.
            memory_threshold (float, optional):
                Memory usage percentage threshold for scaling down operations.
                Defaults to 85.0.
            **kwargs:
                Additional keyword arguments for future extensions.
        """

        self._metadata = {
            'cache_templates': cache_templates,
            'max_cache_size': max_cache_size,
            'extraction_timeout': extraction_timeout,
            'batch_size': batch_size,
            'monitoring_interval': monitoring_interval,
            'cpu_threshold': cpu_threshold,
            'memory_threshold': memory_threshold,
            **kwargs,
        }

        self._is_setup = False
        self._cache: Dict[str, Any] = {}
        self._batch_processor: Optional[BatchProcessor] = None

        self._pipeline = pipeline

    async def setup(self) -> None:
        r"""Set up the extractor with necessary resources."""
        if self._is_setup:
            logger.debug(f"{self.__class__.__name__} already initialized")
            return

        try:
            if self._metadata["cache_templates"]:
                self._template_cache: Dict[str, Any] = {}

            if self._metadata["batch_size"] > 1:
                self._batch_processor = BatchProcessor(
                    initial_batch_size=self._metadata["batch_size"],
                    monitoring_interval=self._metadata["monitoring_interval"],
                    cpu_threshold=self._metadata["cpu_threshold"],
                    memory_threshold=self._metadata["memory_threshold"],
                )

            self._is_setup = True
            logger.info(f"{self.__class__.__name__} initialized successfully")

        except Exception as e:
            error_msg = f"Error during {self.__class__.__name__} setup: {e}"
            logger.error(error_msg)
            await self.cleanup()
            raise RuntimeError(error_msg) from e

    async def cleanup(self) -> None:
        r"""Clean up extractor resources."""
        if not self._is_setup:
            logger.debug(
                f"{self.__class__.__name__} not initialized, skipping cleanup"
            )
            return

        errors = []
        try:
            if hasattr(self, '_template_cache'):
                try:
                    self._template_cache.clear()
                except Exception as e:
                    errors.append(f"Failed to clear template cache: {e}")

            if self._batch_processor is not None:
                try:
                    metrics = self._batch_processor.get_performance_metrics()
                    logger.info(f"Batch processor final metrics: {metrics}")
                except Exception as e:
                    errors.append(
                        f"Failed to get batch processor metrics: {e}"
                    )

            if not errors:
                logger.info(
                    f"{self.__class__.__name__} cleaned up successfully"
                )

        except Exception as e:
            errors.append(f"Unexpected error during cleanup: {e}")

        finally:
            self._is_setup = False
            self._batch_processor = None

        if errors:
            error_msg = f"Errors during cleanup: {'; '.join(errors)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    async def __aenter__(self) -> "Extractor":
        r"""Async context manager entry.

        Returns:
            Extractor: The initialized extractor instance.
        """
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        r"""Async context manager exit.

        Args:
            exc_type (Optional[Type[BaseException]]): The exception type.
            exc_val (Optional[BaseException]): The exception instance.
            exc_tb (Optional[TracebackType]): The exception traceback.
        """
        await self.cleanup()

    async def extract(self, response: str) -> Optional[str]:
        r"""Extracts a normalized, comparable part of the LLM response
        using the fixed multi-stage strategy pipeline.

        Args:
            response (str): The raw response text.

        Returns:
            Optional[str]: Extracted data if successful, otherwise None.
        """
        if not self._is_setup:
            raise RuntimeError(
                "Extractor must be initialized before extraction"
            )
        if not response or not response.strip():
            raise ValueError("Empty or whitespace-only response")

        current_input = response  # Initial input

        for stage in self._pipeline:
            stage_success = (
                False  # Track if any strategy in the stage succeeds
            )

            for strategy in stage:
                try:
                    # Apply the extraction timeout
                    result = await asyncio.wait_for(
                        strategy.extract(current_input),
                        timeout=self._metadata["extraction_timeout"],
                    )

                    if result is not None:
                        current_input = result  # Feed into next stage
                        stage_success = True
                        break  # Move to next stage if valid extraction occurs

                except asyncio.TimeoutError:
                    logger.warning(
                        f"Strategy {strategy.__class__.__name__} timed out "
                        f"after {self._metadata['extraction_timeout']} seconds"
                    )
                except Exception as e:
                    logger.warning(
                        f"Strategy {strategy.__class__.__name__} failed: {e}"
                    )

            if not stage_success:
                logger.debug(
                    "No strategy in stage succeeded, stopping extraction."
                )
                return None  # Stop processing if the stage fails

        return current_input  # Final processed output
