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
from .models import Response, VerificationResult, VerificationStatus

logger = get_logger(__name__)

class Verifier(ABC):
    r"""Base verifier class with optional setup, 
    teardown, and batch verification."""

    def __init__(
        self,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        r"""Initialize the verifier.

        Args:
            timeout: Max time in seconds for verification.
            max_retries: Number of times to retry on failure.
            retry_delay: Delay between retries.
        """
        self._is_setup = False
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay

    async def setup(self) -> None:
        r"""Set up resources if needed."""
        if self._is_setup:
            return
        try:
            await self._setup()
            self._is_setup = True
            logger.info(f"{self.__class__.__name__} setup complete")
        except Exception as e:
            logger.error(f"Setup failed: {e}", exc_info=True)
            raise RuntimeError(f"Setup failed: {e}") from e

    async def teardown(self) -> None:
        r"""Release resources if needed."""
        if not self._is_setup:
            return
        try:
            await self._teardown()
            self._is_setup = False
            logger.info(f"{self.__class__.__name__} teardown complete")
        except Exception as e:
            logger.error(f"Teardown failed: {e}", exc_info=True)

    async def verify(self, result: Response) -> VerificationResult:
        r"""Perform verification with retry logic."""
        attempt = 0
        start_time = time.time()

        while attempt < self._max_retries:
            try:
                if self._timeout:
                    verification_result = await asyncio.wait_for(
                        self._verify_implementation(result),
                        timeout=self._timeout,
                    )
                else:
                    verification_result = await self._verify_implementation(result)

                verification_result.duration = time.time() - start_time
                return verification_result

            except asyncio.TimeoutError:
                attempt += 1
                if attempt >= self._max_retries:
                    return VerificationResult(
                        status=VerificationStatus.TIMEOUT,
                        error_message="Verification timed out.",
                        duration=time.time() - start_time,
                    )
                await asyncio.sleep(self._retry_delay)

            except Exception as e:
                attempt += 1
                if attempt >= self._max_retries:
                    return VerificationResult(
                        status=VerificationStatus.ERROR,
                        error_message=f"Verification failed: {e}",
                        duration=time.time() - start_time,
                    )
                await asyncio.sleep(self._retry_delay)

        return VerificationResult(
            status=VerificationStatus.ERROR,
            error_message="Unexpected error occurred.",
            duration=time.time() - start_time,
        )

    @abstractmethod
    async def _verify_implementation(self, result: Response) -> VerificationResult:
        r"""Subclasses must implement the verification logic."""
        raise NotImplementedError()

    async def batch_verify(self, results: List[Response]) -> List[VerificationResult]:
        r"""Optional batch verification.

        This method can be overridden in subclasses to process 
        multiple verifications in parallel. By default, it just 
        calls `verify()` sequentially.
        """
        return [await self.verify(result) for result in results]

    async def _setup(self) -> None:
        """Optional setup for subclasses."""
        pass

    async def _teardown(self) -> None:
        """Optional teardown for subclasses."""
        pass
