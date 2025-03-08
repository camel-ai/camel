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

import heapq
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

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
    r"""Base class for response extractors with a prioritized strategy system.

    This extractor:
    - Uses a **priority queue** for managing extraction strategies.
    - Tries **each strategy in order of priority** until one succeeds.
    - Supports **async execution** and **dynamic strategy management**.
    """

    def __init__(
        self,
        cache_templates: bool = True,
        max_cache_size: int = 1000,
        extraction_timeout: float = 30.0,
        batch_size: int = 10,
        monitoring_interval: float = 5.0,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        **kwargs,
    ):
        r"""Initialize the extractor with resource constraints and strategies.

        Args:
            cache_templates (bool): Whether to cache extraction templates.
            max_cache_size (int): Maximum number of templates to cache.
            extraction_timeout (float): Timeout for extraction in seconds.
            batch_size (int): Size of batches for parallel extraction.
            monitoring_interval (float): Interval for resource checks.
            cpu_threshold (float): CPU usage threshold for scaling down.
            memory_threshold (float): Memory usage threshold for scaling down.
            **kwargs: Additional parameters.
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

        # Strategy management
        self._strategy_queue: List[Tuple[int, ExtractorStrategy]] = []

    def add_strategy(self, strategy: ExtractorStrategy, priority: int) -> None:
        r"""Add an extraction strategy with a given priority.

        Args:
            strategy (ExtractorStrategy): The extraction strategy to add.
            priority (int): The priority
                (lower values indicate higher priority).
        """
        heapq.heappush(self._strategy_queue, (priority, strategy))

    def remove_strategy(self, strategy: ExtractorStrategy) -> None:
        r"""Remove an extraction strategy and update priority queue.

        Args:
            strategy (ExtractorStrategy): The strategy to remove.
        """
        self._strategy_queue = [
            (p, s) for p, s in self._strategy_queue if s != strategy
        ]
        heapq.heapify(self._strategy_queue)  # Maintain heap order

    async def setup(self) -> None:
        r"""Set up the extractor with necessary resources."""
        if self._is_setup:
            logger.debug(f"{self.__class__.__name__} already initialized")
            return

        try:
            if self._metadata["_cache_templates"]:
                self._template_cache: Dict[str, Any] = {}

            if self._metadata["_batch_size"] > 1:
                self._batch_processor = BatchProcessor(
                    initial_batch_size=self._metadata["_batch_size"],
                    monitoring_interval=self._metadata["_monitoring_interval"],
                    cpu_threshold=self._metadata["_cpu_threshold"],
                    memory_threshold=self._metadata["_memory_threshold"],
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
            BaseExtractor: The initialized extractor instance.
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
        r"""Extract a normalized, comparable part of the LLM response
         using the prioritized fallback strategy.

        Args:
            response (str): The raw response text.

        Returns:
            Optional[Any]: Extracted data if successful, otherwise None.
        """
        if not self._is_setup:
            raise RuntimeError(
                "Extractor must be initialized before extraction"
            )
        if not response or not response.strip():
            raise ValueError("Empty or whitespace-only response")

        for _, strategy in sorted(self._strategy_queue):
            result = await strategy.extract(response)
            if result is not None:
                return result  # Return the first successful extraction

        return None  # No strategy succeeded
