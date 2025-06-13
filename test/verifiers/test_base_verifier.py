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
from typing import Optional
from unittest.mock import AsyncMock, patch

import pytest

from camel.utils import with_timeout_async
from camel.verifiers.base import BaseVerifier
from camel.verifiers.models import VerificationOutcome, VerificationResult


class TestVerifier(BaseVerifier):
    r"""Concrete implementation of BaseVerifier for testing."""

    async def _setup(self, **kwargs) -> None:
        self.setup_called = True

    async def _cleanup(self) -> None:
        self.cleanup_called = True

    async def _verify_implementation(
        self, solution: str, ground_truth: Optional[str] = None
    ) -> VerificationResult:
        r"""Simple implementation that returns success or failure based on
        input.
        """
        if "fail" in solution.lower():
            return VerificationResult(
                status=VerificationOutcome.FAILURE,
                result="Verification failed",
            )
        elif "error" in solution.lower():
            raise ValueError("Simulated error in verification")
        elif "timeout" in solution.lower():
            raise asyncio.TimeoutError("Simulated timeout")
        else:
            return VerificationResult(
                status=VerificationOutcome.SUCCESS,
                result="Verification succeeded",
            )


@pytest.fixture
def test_verifier():
    r"""Fixture providing a TestVerifier instance."""
    return TestVerifier(
        max_parallel=2,
        timeout=5.0,
        max_retries=2,
        retry_delay=0.1,
    )


def test_verifier_init():
    r"""Test BaseVerifier initialization with various parameters."""
    verifier = TestVerifier()
    assert verifier._max_parallel is None
    assert verifier._timeout == 180.0
    assert verifier._max_retries == 3
    assert verifier._retry_delay == 1.0
    assert verifier._is_setup is False

    verifier = TestVerifier(
        max_parallel=5,
        timeout=10.0,
        max_retries=2,
        retry_delay=0.5,
    )
    assert verifier._max_parallel == 5
    assert verifier._timeout == 10.0
    assert verifier._max_retries == 2
    assert verifier._retry_delay == 0.5


@pytest.mark.asyncio
async def test_verifier_setup_and_cleanup(test_verifier):
    r"""Test the setup and cleanup methods of BaseVerifier."""
    assert test_verifier._is_setup is False
    await test_verifier.setup()
    assert test_verifier._is_setup is True
    assert test_verifier.setup_called is True

    await test_verifier.cleanup()
    assert test_verifier._is_setup is False
    assert test_verifier.cleanup_called is True


@pytest.mark.asyncio
async def test_verifier_setup_error():
    r"""Test handling of errors during setup."""

    class ErrorVerifier(TestVerifier):
        async def _setup(self, **kwargs) -> None:
            raise RuntimeError("Simulated setup error")

    verifier = ErrorVerifier()

    with pytest.raises(RuntimeError, match="Failed to initialize"):
        await verifier.setup()

    assert verifier._is_setup is False


@pytest.mark.asyncio
async def test_verifier_cleanup_error():
    r"""Test handling of errors during cleanup."""

    class ErrorVerifier(TestVerifier):
        async def _cleanup(self) -> None:
            raise RuntimeError("Simulated cleanup error")

    verifier = ErrorVerifier()
    await verifier.setup()

    with pytest.raises(RuntimeError, match="Failed to cleanup"):
        await verifier.cleanup()

    assert verifier._is_setup is False


@pytest.mark.asyncio
async def test_verify_success(test_verifier):
    r"""Test successful verification."""
    await test_verifier.setup()

    result = await test_verifier.verify(
        solution="This is a successful response",
        reference_answer="Expected response",
    )

    assert result.status == VerificationOutcome.SUCCESS
    assert result.result == "Verification succeeded"
    assert result.duration > 0
    assert result.metadata["attempt"] == 1

    await test_verifier.cleanup()


@pytest.mark.asyncio
async def test_verify_failure(test_verifier):
    r"""Test failed verification."""
    await test_verifier.setup()

    result = await test_verifier.verify(
        solution="This will fail the verification",
        reference_answer="Expected response",
    )

    assert result.status == VerificationOutcome.FAILURE
    assert result.result == "Verification failed"
    assert result.duration > 0
    assert result.metadata["attempt"] == 1

    await test_verifier.cleanup()


@pytest.mark.asyncio
async def test_verify_error_with_retry(test_verifier):
    r"""Test verification with error and retry."""
    await test_verifier.setup()

    test_verifier._max_retries = 1

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await test_verifier.verify(
            solution="This will cause an error",
            reference_answer="Expected response",
        )

        assert result.status == VerificationOutcome.ERROR
        assert result.error_message is not None
        assert "Verification failed" in result.error_message
        assert result.duration > 0
        assert "attempt" in result.metadata

    await test_verifier.cleanup()


@pytest.mark.asyncio
async def test_verify_timeout(test_verifier):
    r"""Test verification timeout."""
    await test_verifier.setup()

    # dont verify directly
    with (
        patch.object(
            test_verifier,
            "_verify_implementation",
            side_effect=asyncio.TimeoutError("Simulated timeout"),
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await test_verifier.verify(
            solution="This will timeout",
            reference_answer="Expected response",
        )

    assert result.status == VerificationOutcome.TIMEOUT
    assert "Verification timed out after all retries" in result.error_message

    await test_verifier.cleanup()


@pytest.mark.asyncio
async def test_verify_not_setup():
    r"""Test verification when verifier is not set up."""
    verifier = TestVerifier()

    verifier.setup = AsyncMock()
    verifier._verify_implementation = AsyncMock(
        return_value=VerificationResult(
            status=VerificationOutcome.SUCCESS, result="Success"
        )
    )

    await verifier.verify(solution="Test", reference_answer="Expected")

    verifier.setup.assert_called_once()


@pytest.mark.asyncio
async def test_verify_batch(test_verifier):
    r"""Test batch verification."""
    await test_verifier.setup()

    test_verifier._verify_implementation = AsyncMock(
        return_value=VerificationResult(
            status=VerificationOutcome.SUCCESS,
            result="Verification succeeded",
        )
    )

    async def mock_verify(solution, ground_truth):
        if "fail" in solution.lower():
            return VerificationResult(
                status=VerificationOutcome.FAILURE,
                result="Verification failed",
            )
        return VerificationResult(
            status=VerificationOutcome.SUCCESS,
            result="Verification succeeded",
        )

    with patch.object(test_verifier, "verify", side_effect=mock_verify):
        test_verifier.verify_batch = (
            lambda *args, **kwargs: BaseVerifier.verify_batch(
                test_verifier, *args, **kwargs
            )
        )

        solutions = ["Success 1", "Success 2", "This will fail"]
        reference_answers = ["reference"] * len(solutions)
        results = await test_verifier.verify_batch(
            solutions, reference_answers
        )

        assert len(results) == 3
        assert results[0].status == VerificationOutcome.SUCCESS
        assert results[1].status == VerificationOutcome.SUCCESS
        assert results[2].status == VerificationOutcome.FAILURE

    await test_verifier.cleanup()


@pytest.mark.asyncio
async def test_verify_batch_with_error_handling(test_verifier):
    r"""Test batch verification with error handling."""
    await test_verifier.setup()

    test_verifier._verify_implementation = AsyncMock(
        return_value=VerificationResult(
            status=VerificationOutcome.SUCCESS,
            result="Verification succeeded",
        )
    )

    async def mock_verify(solution, ground_truth):
        if "error" in solution.lower():
            raise ValueError("Simulated error in verification")
        return VerificationResult(
            status=VerificationOutcome.SUCCESS,
            result="Verification succeeded",
        )

    with patch.object(test_verifier, "verify", side_effect=mock_verify):
        test_verifier.verify_batch = (
            lambda *args, **kwargs: BaseVerifier.verify_batch(
                test_verifier, *args, **kwargs
            )
        )

        solutions = ["Success", "This will cause an error"]
        ground_truthes = ["Expected 1", "Expected 2"]

        with pytest.raises(
            RuntimeError, match="One or more verifications failed"
        ):
            await test_verifier.verify_batch(
                solutions, ground_truthes, raise_on_error=True
            )

        results = await test_verifier.verify_batch(solutions, ground_truthes)
        assert len(results) == 2
        assert results[0].status == VerificationOutcome.SUCCESS
        assert results[1].status == VerificationOutcome.ERROR

    await test_verifier.cleanup()


@pytest.mark.asyncio
async def test_verify_batch_concurrency_limiting(test_verifier):
    r"""Test that batch verification properly limits concurrency."""
    await test_verifier.setup()

    class MockSemaphore:
        def __init__(self, value):
            self.value = value
            self.count = 0
            self.max_count = 0

        async def __aenter__(self):
            self.count += 1
            self.max_count = max(self.max_count, self.count)

        async def __aexit__(self, *args):
            self.count -= 1

    solutions = ["Success 1", "Success 2", "Success 3"]
    ground_truthes = ["Expected 1", "Expected 2", "Expected 3"]

    mock_sem = MockSemaphore(1)

    async def patched_verify_batch(
        verifier, solutions, ground_truthes, raise_on_error=False
    ):
        results = []
        for solution, ground_truth in zip(solutions, ground_truthes):
            async with mock_sem:
                await asyncio.sleep(0.01)  # Simulate processing time
                results.append(await verifier.verify(solution, ground_truth))
        return results

    test_verifier.verify_batch = lambda *args, **kwargs: patched_verify_batch(
        test_verifier, *args, **kwargs
    )

    await test_verifier.verify_batch(solutions, ground_truthes)

    assert mock_sem.max_count == 1

    await test_verifier.cleanup()


@pytest.mark.asyncio
async def test_full_verification_flow():
    r"""Test the full verification flow from setup to cleanup."""
    verifier = TestVerifier(timeout=1.0, max_retries=1, retry_delay=0.1)

    try:
        await verifier.setup()
        assert verifier._is_setup is True

        success_result = await verifier.verify(
            solution="This should succeed", reference_answer="Expected"
        )
        assert success_result.status == VerificationOutcome.SUCCESS

        failure_result = await verifier.verify(
            solution="This will fail", reference_answer="Expected"
        )
        assert failure_result.status == VerificationOutcome.FAILURE

        with patch("asyncio.sleep", new_callable=AsyncMock):
            error_result = await verifier.verify(
                solution="This will cause an error",
                reference_answer="Expected",
            )
            assert error_result.status == VerificationOutcome.ERROR

    finally:
        await verifier.cleanup()
        assert verifier._is_setup is False


@pytest.mark.asyncio
async def test_with_timeout_function():
    """Test the with_timeout function handles completions and\
         timeouts correctly"""

    # Test normal operation (successful completion)
    mock_coro = AsyncMock()
    mock_coro.return_value = "success"
    result = await with_timeout_async(mock_coro(), context="test operation")
    assert result == "success"

    # Test timeout handling
    mock_timeout_coro = AsyncMock()
    mock_timeout_coro.side_effect = asyncio.TimeoutError("Simulated timeout")

    with pytest.raises(asyncio.TimeoutError) as exc_info:
        await with_timeout_async(
            mock_timeout_coro(), context="test timeout operation"
        )

    assert "Timed out while test timeout operation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_timeout_in_extractor_setup():
    """Test timeout handling during extractor setup"""
    mock_extractor = AsyncMock()
    mock_extractor.setup.side_effect = asyncio.TimeoutError(
        "Simulated timeout in extractor setup"
    )

    verifier = TestVerifier()
    verifier.extractor = mock_extractor

    with pytest.raises(RuntimeError) as exc_info:
        await verifier.setup()

    assert "Failed to initialize" in str(exc_info.value)
    mock_extractor.setup.assert_called_once()


@pytest.mark.asyncio
async def test_timeout_in_verify_implementation(test_verifier):
    """Test timeout during verify implementation"""
    await test_verifier.setup()

    # Test that a TimeoutError in _verify_implementation is handled with retry
    with (
        patch.object(
            test_verifier,
            "_verify_implementation",
            side_effect=[
                asyncio.TimeoutError("Simulated timeout"),
                VerificationResult(
                    status=VerificationOutcome.SUCCESS,
                    result="Success after retry",
                ),
            ],
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await test_verifier.verify("solution", "reference")

    assert result.status == VerificationOutcome.SUCCESS
    assert result.result == "Success after retry"
    assert result.metadata["attempt"] == 2  # Second attempt succeeded

    await test_verifier.cleanup()


@pytest.mark.asyncio
async def test_repeated_timeout_in_verify_implementation(test_verifier):
    """Test multiple consecutive timeouts leading to timeout outcome"""
    await test_verifier.setup()
    test_verifier._max_retries = 2  # Set max retries to 2

    # Simulate repeated timeouts exceeding max_retries
    with (
        patch.object(
            test_verifier,
            "_verify_implementation",
            side_effect=asyncio.TimeoutError("Simulated timeout"),
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await test_verifier.verify("solution", "reference")

    # After max retries are exhausted, should return TIMEOUT outcome
    assert result.status == VerificationOutcome.TIMEOUT
    assert "Verification timed out after all retries" in result.error_message
    assert result.metadata["attempt"] == 2  # Attempted max_retries times

    await test_verifier.cleanup()


@pytest.mark.asyncio
async def test_timeout_in_batch_verification(test_verifier):
    """Test timeout handling in batch verification"""
    await test_verifier.setup()

    # Create a mix of successful and timeout solutions
    solutions = ["solution1", "solution2", "timeout"]
    reference_answers = ["reference"] * len(solutions)

    # Mock the verify method to simulate a timeout for specific solutions
    original_verify = test_verifier.verify

    async def mock_verify(solution, reference=None):
        if "timeout" in solution:
            raise asyncio.TimeoutError("Simulated timeout")
        return await original_verify(solution, reference)

    with patch.object(test_verifier, "verify", side_effect=mock_verify):
        results = await test_verifier.verify_batch(
            solutions, reference_answers
        )

    # Should have 3 results
    assert len(results) == 3

    # Check individual results
    success_results = [
        r for r in results if r.status == VerificationOutcome.SUCCESS
    ]

    non_success_results = [
        r for r in results if r.status != VerificationOutcome.SUCCESS
    ]
    assert len(non_success_results) == 1
    assert len(success_results) == 2
    await test_verifier.cleanup()
