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
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from camel.logger import get_logger
from camel.utils import BatchProcessor

from .models import (
    VerificationOutcome,
    VerificationResult,
    VerifierInput,
)

logger = get_logger(__name__)


class BaseVerifier(ABC):
    r"""Base class for all verifiers.

    Example:
        ```python
        verifier = MyVerifier()
        await verifier.setup()
        result = await verifier.verify(response)
        await verifier.cleanup()
        ```

    Key Features:
    - Async verification with retry logic
    - Comprehensive error handling and logging
    - Configurable batch processing
    - Resource monitoring for adaptive scaling
    """

    def __init__(
        self,
        max_parallel: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        initial_batch_size: Optional[int] = None,
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        **kwargs,
    ):
        r"""Initialize the verifier with configuration parameters.

        Args:
            max_parallel: Maximum number of parallel verifications. If None,
                determined dynamically based on system resources.
                (default: :obj:`None`)
            timeout: Timeout in seconds for each verification. (default:
                :obj:`None`)
            max_retries: Maximum number of retry attempts. (default: :obj:`3`)
            retry_delay: Delay between retries in seconds. (default:
                :obj:`1.0`)
            initial_batch_size: Initial size for batch processing. If None,
                defaults to 10. (default: :obj:`None`)
            cpu_threshold: CPU usage percentage threshold for scaling down.
                (default: :obj:`80.0`)
            memory_threshold: Memory usage percentage threshold for scaling
                down. (default: :obj:`85.0`)
            **kwargs: Additional verifier parameters.
        """
        self._is_setup: bool = False
        self._max_parallel: Optional[int] = max_parallel
        self._timeout: Optional[float] = timeout
        self._max_retries: int = max_retries
        self._retry_delay: float = retry_delay
        self._initial_batch_size: Optional[int] = initial_batch_size
        self._cpu_threshold: float = cpu_threshold
        self._memory_threshold: float = memory_threshold
        self._batch_processor: BatchProcessor = BatchProcessor()

    async def setup(self) -> None:
        r"""Set up the verifier with necessary resources.

        Initializes:
        1. Batch processor with validated parameters
        2. Any verifier-specific resources

        Raises:
            RuntimeError: If setup fails or resources cannot be initialized.
        """
        if self._is_setup:
            logger.debug(f"{self.__class__.__name__} already initialized")
            return

        try:
            batch_size = max(1, self._initial_batch_size or 10)
            max_parallel = max(1, self._max_parallel or 1)
            self._batch_processor = BatchProcessor()

            logger.info(
                f"{self.__class__.__name__} initialized with "
                f"batch_size={batch_size}, max_parallel={max_parallel}"
            )

            await self._setup()
            self._is_setup = True

        except Exception as e:
            error_msg = (
                f"Failed to initialize {self.__class__.__name__}: {e!s}"
            )
            logger.error(error_msg, exc_info=True)
            await self.cleanup()
            raise RuntimeError(error_msg) from e

    @abstractmethod
    async def _setup(self) -> None:
        r"""Implement verifier-specific setup logic."""
        pass

    async def cleanup(self) -> None:
        r"""Clean up verifier resources.

        Ensures:
        1. Batch processor is reset
        2. All internal states are cleared

        Raises:
            RuntimeError: If cleanup fails.
        """
        if not self._is_setup:
            return

        try:
            self._batch_processor = BatchProcessor()
            await self._cleanup()
            logger.info(f"{self.__class__.__name__} cleaned up successfully")

        except Exception as e:
            error_msg = f"Failed to cleanup {self.__class__.__name__}: {e!s}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

        finally:
            self._is_setup = False

    @abstractmethod
    async def _cleanup(self) -> None:
        r"""Implement verifier-specific cleanup logic."""
        pass

    async def verify(self, result: VerifierInput) -> VerificationResult:
        r"""Perform verification with full error handling.

        Verifies correctness, expected output, reasoning, and symbolic
        consistency.

        Args:
            result: The response to verify.

        Returns:
            VerificationResult: Structured result containing:
                - status: SUCCESS/FAILURE/ERROR/TIMEOUT
                - result: Verification outcome description
                - duration: Time taken for verification
                - metadata: Additional details
                - error_message: Error description if applicable

        Raises:
            RuntimeError: If verification fails unexpectedly.
            asyncio.TimeoutError: If verification times out.
        """
        if not self._is_setup:
            logger.warning(
                f"{self.__class__.__name__} not set up, calling setup()"
            )
            await self.setup()

        attempt = 0
        start_time = time.time()

        while attempt < self._max_retries:
            try:
                verification_result = (
                    await asyncio.wait_for(
                        self._verify_implementation(result),
                        timeout=self._timeout,
                    )
                    if self._timeout
                    else await self._verify_implementation(result)
                )

                verification_result.duration = time.time() - start_time
                verification_result.metadata["attempt"] = attempt + 1
                return verification_result

            except asyncio.TimeoutError:
                attempt += 1
                if attempt == self._max_retries:
                    return VerificationResult(
                        status=VerificationOutcome.TIMEOUT,
                        result="",
                        error_message="Verification timed out "
                        "after all retries.",
                        duration=time.time() - start_time,
                        metadata={"attempt": attempt},
                    )
                logger.warning(
                    f"Verification timeout on attempt {attempt}, retrying..."
                )
                await asyncio.sleep(self._retry_delay)

            except Exception as e:
                attempt += 1
                if attempt == self._max_retries:
                    return VerificationResult(
                        status=VerificationOutcome.ERROR,
                        result="",
                        error_message=f"Verification failed: {e!s}",
                        duration=time.time() - start_time,
                        metadata={"attempt": attempt},
                    )
                await asyncio.sleep(self._retry_delay)

        return VerificationResult(
            status=VerificationOutcome.ERROR,
            result="",
            error_message="Unexpected code path reached",
            duration=time.time() - start_time,
            metadata={"attempt": attempt},
        )

    @abstractmethod
    async def _verify_implementation(
        self, result: VerifierInput
    ) -> VerificationResult:
        r"""Implement the actual verification logic.

        Args:
            result: The response to verify.

        Returns:
            VerificationResult: Containing the verification outcome.

        Raises:
            NotImplementedError: Must be implemented in subclasses.
        """
        raise NotImplementedError(
            "Subclasses must implement _verify_implementation()"
        )


async def verify_batch(
    self, results: List[VerifierInput], raise_on_error: bool = False
) -> List[VerificationResult]:
    r"""Verify multiple results in parallel with controlled concurrency.

    Args:
        results: List of responses to verify.
        raise_on_error: Whether to raise an exception if any verification
            fails. (default: :obj:`False`)

    Returns:
        List[VerificationResult]: One for each input response.

    Raises:
        RuntimeError: If any verification fails and raise_on_error is True.
        asyncio.TimeoutError: If verifications time out and max retries
            exceeded.
    """
    if not self._is_setup:
        logger.warning(
            f"{self.__class__.__name__} not set up, calling setup()"
        )
        await self.setup()

    # Get current batch parameters from processor with defaults if not
    #  present
    max_workers = getattr(
        self._batch_processor, 'max_workers', self._max_parallel or 1
    )
    batch_size = getattr(
        self._batch_processor, 'batch_size', self._initial_batch_size or 10
    )
    semaphore = asyncio.Semaphore(max(1, max_workers))

    async def _verify_with_semaphore(
        response: VerifierInput,
    ) -> VerificationResult:
        start_time = time.time()
        try:
            async with semaphore:
                verification_result = await self.verify(response)
            processing_time = time.time() - start_time
            success = verification_result.status == VerificationOutcome.SUCCESS
            self._batch_processor.adjust_batch_size(success, processing_time)
            return verification_result
        except Exception as e:
            processing_time = time.time() - start_time
            self._batch_processor.adjust_batch_size(False, processing_time)
            logger.error(f"Verification failed: {e!s}", exc_info=True)
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message=str(e),
                metadata={"error_type": type(e).__name__},
            )

    # Process in batches
    all_results: List[VerificationResult] = []
    for i in range(0, len(results), batch_size):
        batch = results[i : i + batch_size]
        verification_tasks = [
            _verify_with_semaphore(result) for result in batch
        ]
        try:
            batch_results = await asyncio.gather(*verification_tasks)
            all_results.extend(batch_results)
        except Exception as e:
            logger.error(f"Batch verification failed: {e!s}", exc_info=True)
            if raise_on_error:
                raise RuntimeError(f"Batch verification failed: {e!s}") from e

    if raise_on_error and any(
        r.status in {VerificationOutcome.ERROR, VerificationOutcome.TIMEOUT}
        for r in all_results
    ):
        error_msg = "One or more verifications failed"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    return all_results
