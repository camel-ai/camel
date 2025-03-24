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
import os
import tempfile
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.datasets.generator_with_solver import GeneratorWithSolver
from camel.datasets.models import DataPoint
from camel.solvers.base import BaseSolver
from camel.solvers.models import Puzzle, PuzzleSolverResult
from camel.verifiers.base import BaseVerifier
from camel.verifiers.models import VerificationOutcome, VerificationResult


# Mock implementation of a solver for testing
class MockSolver(BaseSolver):
    def solve(self, input_data: Puzzle) -> PuzzleSolverResult:
        return PuzzleSolverResult(
            input_id=input_data.id,
            input_data=input_data,
            input_hash="mock_hash",
            code="mock_code",
            output_data="mock_solution",
            success=True,
            metadata={"mock_key": "mock_value"},
        )


# Mock implementation of a verifier for testing
class MockVerifier(BaseVerifier):
    async def _setup(self, **kwargs) -> None:
        pass

    async def _cleanup(self) -> None:
        pass

    async def _verify_implementation(
        self, solution: str, ground_truth: Optional[str]
    ) -> VerificationResult:
        return VerificationResult(
            status=VerificationOutcome.SUCCESS,
            result="Verification passed",
            duration=0.1,
            metadata={"verified": True},
        )


# Mock implementation of a generator with solver for testing
class MockGeneratorWithSolver(GeneratorWithSolver):
    async def generate_input(self, **kwargs) -> Puzzle:
        return Puzzle(
            id="mock_id",
            title="Mock Puzzle",
            problem="Solve this mock problem",
            source="mock_source",
            metadata={"difficulty": "easy"},
            ground_truth_solution="mock_ground_truth",
        )


# Mock implementation that raises an exception during input generation
class ErrorGeneratorWithSolver(GeneratorWithSolver):
    async def generate_input(self, **kwargs) -> Puzzle:
        raise ValueError("Mock error during input generation")


# Mock implementation that raises an exception during verification
class MockVerifierWithError(BaseVerifier):
    async def _setup(self, **kwargs) -> None:
        pass

    async def _cleanup(self) -> None:
        pass

    async def _verify_implementation(
        self, solution: str, ground_truth: Optional[str]
    ) -> VerificationResult:
        raise ValueError("Mock error during verification")


@pytest.mark.asyncio
async def test_initialization():
    r"""Test proper initialization of GeneratorWithSolver."""
    # Test with minimal parameters
    solver = MockSolver()
    generator = GeneratorWithSolver(solver=solver)

    assert generator.solver == solver
    assert generator.verifier is None
    assert generator._verifier_setup is False

    # Test with verifier
    verifier = MockVerifier()
    generator = GeneratorWithSolver(solver=solver, verifier=verifier)

    assert generator.solver == solver
    assert generator.verifier == verifier
    assert generator._verifier_setup is False

    # Test with custom seed
    generator = GeneratorWithSolver(solver=solver, seed=123)
    assert generator._seed == 123


@pytest.mark.asyncio
async def test_ensure_verifier_setup():
    r"""Test that verifier setup is properly managed."""
    # Test without verifier
    solver = MockSolver()
    generator = GeneratorWithSolver(solver=solver)

    await generator._ensure_verifier_setup()
    assert generator._verifier_setup is False

    # Test with verifier
    verifier = MockVerifier()
    verifier.setup = AsyncMock()
    generator = GeneratorWithSolver(solver=solver, verifier=verifier)

    await generator._ensure_verifier_setup()
    verifier.setup.assert_called_once()
    assert generator._verifier_setup is True

    # Test that setup is not called twice
    verifier.setup.reset_mock()
    await generator._ensure_verifier_setup()
    verifier.setup.assert_not_called()


@pytest.mark.asyncio
async def test_process_solution():
    r"""Test processing of solver results into data points."""
    solver = MockSolver()
    generator = GeneratorWithSolver(solver=solver)

    puzzle = Puzzle(
        id="test_id",
        title="Test Puzzle",
        problem="Test Problem",
        source="test_source",
        metadata={"test_key": "test_value"},
        ground_truth_solution="expected_solution",
    )

    solver_result = PuzzleSolverResult(
        input_id=puzzle.id,
        input_data=puzzle,
        input_hash="test_hash",
        code="test_code",
        output_data="actual_solution",
        success=True,
        metadata={"solver_key": "solver_value"},
    )

    data_point = await generator._process_solution(solver_result)

    assert isinstance(data_point, DataPoint)
    assert data_point.question == puzzle.problem
    assert data_point.final_answer == "actual_solution"
    assert data_point.rationale == puzzle.ground_truth_solution
    assert data_point.metadata["input_id"] == puzzle.id
    assert data_point.metadata["input_title"] == puzzle.title
    assert data_point.metadata["input_source"] == puzzle.source
    assert data_point.metadata["solver_success"] is True
    assert data_point.metadata["test_key"] == "test_value"
    assert data_point.metadata["solver_key"] == "solver_value"
    assert data_point.metadata["solution_code"] == "test_code"

    # Test with a non-puzzle input (more general case)
    custom_input = Puzzle(
        id="custom_id",
        title="Custom Puzzle",
        problem="Custom problem",
        source="custom_source",
        metadata={"custom_key": "custom_value"},
    )

    custom_result = PuzzleSolverResult(
        input_id="custom_id",
        input_data=custom_input,  # Using a Puzzle object
        input_hash="custom_hash",
        code="custom_code",
        output_data="custom_solution",
        success=True,
        metadata={"solver_custom_key": "solver_custom_value"},
    )

    custom_data_point = await generator._process_solution(custom_result)

    assert isinstance(custom_data_point, DataPoint)
    assert custom_data_point.question == custom_input.problem
    assert custom_data_point.final_answer == "custom_solution"
    assert custom_data_point.rationale is None
    assert custom_data_point.metadata["input_id"] == "custom_id"
    assert custom_data_point.metadata["input_title"] == "Custom Puzzle"
    assert custom_data_point.metadata["input_source"] == "custom_source"
    assert custom_data_point.metadata["solver_success"] is True
    assert custom_data_point.metadata["custom_key"] == "custom_value"
    assert (
        custom_data_point.metadata["solver_custom_key"]
        == "solver_custom_value"
    )
    assert custom_data_point.metadata["solution_code"] == "custom_code"


@pytest.mark.asyncio
async def test_generate_new():
    r"""Test generation of new data points."""
    solver = MockSolver()
    generator = MockGeneratorWithSolver(solver=solver)

    # Test generation of a single data point
    data_points = await generator.generate_new(1)

    assert len(data_points) == 1
    assert isinstance(data_points[0], DataPoint)
    assert data_points[0].question == "Solve this mock problem"
    assert data_points[0].final_answer == "mock_solution"

    # Test generation of multiple data points
    data_points = await generator.generate_new(3)

    assert len(data_points) == 3
    for data_point in data_points:
        assert isinstance(data_point, DataPoint)
        assert data_point.question == "Solve this mock problem"
        assert data_point.final_answer == "mock_solution"


@pytest.mark.asyncio
async def test_generate_new_with_verifier():
    r"""Test generation with verification."""
    solver = MockSolver()
    verifier = MockVerifier()
    verifier.verify = AsyncMock(
        return_value=VerificationResult(
            status=VerificationOutcome.SUCCESS,
            result="Verification passed",
            duration=0.1,
            metadata={"verified": True},
        )
    )

    generator = MockGeneratorWithSolver(solver=solver, verifier=verifier)

    data_points = await generator.generate_new(1)

    assert len(data_points) == 1
    verifier.verify.assert_called_once()
    assert data_points[0].metadata["verification"]["status"] == "SUCCESS"


@pytest.mark.asyncio
async def test_generate_new_with_verification_failure():
    r"""Test generation with verification failure."""
    solver = MockSolver()
    verifier = MockVerifier()
    verifier.verify = AsyncMock(
        return_value=VerificationResult(
            status=VerificationOutcome.FAILURE,
            result="Verification failed",
            duration=0.1,
            metadata={"verified": False},
        )
    )

    generator = MockGeneratorWithSolver(solver=solver, verifier=verifier)

    data_points = await generator.generate_new(1)

    assert len(data_points) == 1
    verifier.verify.assert_called_once()
    assert data_points[0].metadata["verification"]["status"] == "FAILURE"
    assert data_points[0].metadata["solver_success"] is False


@pytest.mark.asyncio
async def test_generate_new_with_verification_error():
    r"""Test generation with verification error."""
    solver = MockSolver()
    verifier = MockVerifier()

    # Patch the verify method to raise an exception
    async def verify_with_error(*args, **kwargs):
        raise ValueError("Mock verification error")

    verifier.verify = verify_with_error

    generator = MockGeneratorWithSolver(solver=solver, verifier=verifier)

    data_points = await generator.generate_new(1)

    assert len(data_points) == 1
    assert "verification_error" in data_points[0].metadata
    assert data_points[0].metadata["solver_success"] is False


@pytest.mark.asyncio
async def test_generate_new_with_input_error():
    r"""Test generation with input generation error."""
    solver = MockSolver()
    generator = ErrorGeneratorWithSolver(solver=solver)

    data_points = await generator.generate_new(1)

    assert len(data_points) == 0


@pytest.mark.asyncio
async def test_cleanup():
    r"""Test proper cleanup of resources."""
    solver = MockSolver()
    verifier = MockVerifier()
    verifier.cleanup = AsyncMock()

    # Create a temporary file to test cache cleanup
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(os.path.join(temp_dir, "cache.jsonl"))

        generator = GeneratorWithSolver(
            solver=solver, verifier=verifier, cache=cache_path
        )
        generator._verifier_setup = True

        # Create a temp file to simulate a partial write
        temp_file = cache_path.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            f.write("test")

        await generator.cleanup()

        verifier.cleanup.assert_called_once()
        assert generator._verifier_setup is False
        assert not temp_file.exists()  # Temp file should be cleaned up

    # Test cleanup when verifier is not set up
    verifier.cleanup.reset_mock()
    generator._verifier_setup = False

    await generator.cleanup()

    verifier.cleanup.assert_not_called()


@pytest.mark.asyncio
async def test_cache_functionality():
    r"""Test that caching works correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(os.path.join(temp_dir, "cache.jsonl"))

        solver = MockSolver()
        generator = MockGeneratorWithSolver(solver=solver, cache=cache_path)

        # Generate some data points
        await generator.generate_new(2)

        # Check that the cache file exists
        assert cache_path.exists()

        # Create a new generator with the same cache
        new_generator = MockGeneratorWithSolver(
            solver=solver, cache=cache_path
        )

        # Check that the cached data points are loaded
        assert len(new_generator._data) == 2


@pytest.mark.asyncio
async def test_cache_error_handling():
    r"""Test that cache errors are handled gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(os.path.join(temp_dir, "cache.jsonl"))

        # Make the directory read-only after creation
        os.chmod(temp_dir, 0o555)

        try:
            solver = MockSolver()
            generator = MockGeneratorWithSolver(
                solver=solver, cache=cache_path
            )

            # This should not raise an exception even though writing to cache
            # will fail
            data_points = await generator.generate_new(1)

            assert len(data_points) == 1
            # Cache file should not exist due to permissions
            assert not cache_path.exists()
        finally:
            # Restore permissions to allow cleanup
            os.chmod(temp_dir, 0o755)


@pytest.mark.asyncio
async def test_abstract_method_implementation():
    r"""Test that abstract methods must be implemented."""
    solver = MockSolver()
    generator = GeneratorWithSolver(solver=solver)

    with pytest.raises(NotImplementedError):
        await generator.generate_input()


@pytest.mark.asyncio
async def test_run_in_executor():
    r"""Test that solve method is run in an executor."""
    solver = MockSolver()
    solver.solve = MagicMock(
        return_value=PuzzleSolverResult(
            input_id="test_id",
            input_data=Puzzle(
                id="test_id",
                title="Test Puzzle",
                problem="Test Problem",
                source="test_source",
                metadata={},
            ),
            input_hash="test_hash",
            success=True,
        )
    )

    generator = MockGeneratorWithSolver(solver=solver)

    with patch('asyncio.get_event_loop') as mock_get_loop:
        mock_loop = MagicMock()
        mock_get_loop.return_value = mock_loop
        mock_loop.run_in_executor.return_value = asyncio.Future()
        mock_loop.run_in_executor.return_value.set_result(
            PuzzleSolverResult(
                input_id="test_id",
                input_data=Puzzle(
                    id="test_id",
                    title="Test Puzzle",
                    problem="Test Problem",
                    source="test_source",
                    metadata={},
                ),
                input_hash="test_hash",
                success=True,
            )
        )

        await generator.generate_new(1)

        mock_loop.run_in_executor.assert_called_once()
