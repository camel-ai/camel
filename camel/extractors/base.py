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
from types import TracebackType
from typing import Any, Dict, List, Optional, Type

from camel.logger import get_logger
from camel.utils import BatchProcessor

logger = get_logger(__name__)


class BaseExtractorStrategy(ABC):
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


class BaseExtractor:
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
        pipeline: List[List[BaseExtractorStrategy]],
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
            pipeline (List[List[BaseExtractorStrategy]]):
                A fixed list of lists where each list represents a stage
                containing extractor strategies executed in order.
            cache_templates (bool): Whether to cache extraction templates.
                (default: :obj:`True`)
            max_cache_size (int): Maximum number of templates to cache.
                (default: :obj:`1000`)
            extraction_timeout (float): Maximum time for extraction in seconds.
                (default: :obj:`30.0`)
            batch_size (int): Size of batches for parallel extraction.
                (default: :obj:`10`)
            monitoring_interval (float): Interval in seconds between resource
                checks. (default: :obj:`5.0`)
            cpu_threshold (float): CPU usage percentage threshold for scaling
                down. (default: :obj:`80.0`)
            memory_threshold (float): Memory usage percentage threshold for
                scaling down. (default: :obj:`85.0`)
            **kwargs: Additional extractor parameters.
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
        r"""Set up the extractor with necessary resources.

        This method:
        1. Initializes template cache if enabled
        2. Sets up any parallel processing resources
        3. Validates extraction patterns

        Raises:
            RuntimeError: If initialization fails
        """
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
        r"""Clean up extractor resources.

        This method handles cleanup of resources and resets the extractor
        state.
        It ensures:
        1. All resources are properly released
        2. Template cache is cleared
        3. Parallel processing resources are shutdown
        4. State is reset to initial
        5. Cleanup happens even if errors occur

        Raises:
            RuntimeError: If cleanup fails (after resetting initialization
                state).
        """
        if not self._is_setup:
            logger.debug(
                f"{self.__class__.__name__} not initialized, skipping cleanup"
            )
            return

        errors = []
        try:
            # Clear template cache
            if hasattr(self, '_template_cache'):
                try:
                    self._template_cache.clear()
                except Exception as e:
                    errors.append(f"Failed to clear template cache: {e}")

            # Shutdown parallel processing
            if self._batch_processor is not None:
                try:
                    # Get final performance metrics before cleanup
                    metrics = self._batch_processor.get_performance_metrics()
                    logger.info(f"Batch processor final metrics: {metrics}")
                except Exception as e:
                    errors.append(
                        f"Failed to get batch processor metrics: {e}"
                    )

            # Preserve init config in metadata
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

    async def __aenter__(self) -> "BaseExtractor":
        r"""Async context manager entry.

        Returns:
            BaseExtractor: The initialized extractor instance.
        """
        await self.setup()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        r"""Async context manager exit.

        Args:
            exc_type (Optional[Type[BaseException]]): Exception type if an
                error occurred.
            exc_val (Optional[BaseException]): Exception value if an error
                occurred.
            exc_tb (Optional[TracebackType]): Exception traceback if an error
                occurred.
        """
        await self.cleanup()

    async def extract(self, response: str) -> Optional[str]:
        r"""Extracts a normalized, comparable part of the LLM response
        using the fixed multi-stage strategy pipeline.

        Args:
            response (str): The raw response text.

        Returns:
            Optional[str]: Extracted data if successful, otherwise None.

        Raises:
            ValueError: If response is empty or invalid.
            RuntimeError: If extractor is not initialized.
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
