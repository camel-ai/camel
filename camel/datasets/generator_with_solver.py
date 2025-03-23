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
import json
from pathlib import Path
from typing import List, Optional, Union

from camel.logger import get_logger
from camel.solvers.base import BaseSolver
from camel.solvers.models import Puzzle, SolverResult
from camel.verifiers.base import BaseVerifier

from .base_generator import BaseGenerator
from .models import DataPoint

logger = get_logger(__name__)


class GeneratorWithSolver(BaseGenerator):
    r"""A generator that uses a solver to generate data points.

    This generator leverages a puzzle solver to generate data points. It can
    optionally use a verifier to validate the solutions produced by the solver.

    The generator creates puzzles, solves them using the provided solver, and
    optionally verifies the solutions using the provided verifier.
    """

    def __init__(
        self,
        solver: BaseSolver,
        verifier: Optional[BaseVerifier] = None,
        seed: int = 42,
        cache: Union[str, Path, None] = None,
        data_path: Union[str, Path, None] = None,
        **kwargs,
    ):
        r"""Initialize the generator with a solver and optional verifier.

        Args:
            solver (BaseSolver): The solver to use for generating solutions.
            verifier (Optional[BaseVerifier]): Optional verifier to validate
                solutions. If provided, solutions will be verified before
                being returned.
            seed (int): Random seed for reproducibility. (default: :obj:`42`)
            cache (Union[str, Path, None]): Optional path to save generated
                datapoints during iteration. (default: :obj:`None`)
            data_path (Union[str, Path, None]): Optional path to a JSONL file
                to initialize the dataset from. (default: :obj:`None`)
            **kwargs: Additional generator parameters.
        """
        # If cache is provided and exists but data_path is not provided,
        # use the cache as the data_path
        if cache and not data_path:
            cache_path = Path(cache)
            if cache_path.exists():
                data_path = cache

        super().__init__(seed=seed, cache=cache, data_path=data_path, **kwargs)
        self.solver = solver
        self.verifier = verifier
        self._verifier_setup = False
        self._seed = seed

    async def _ensure_verifier_setup(self) -> None:
        r"""Ensure the verifier is set up if it exists."""
        if self.verifier and not self._verifier_setup:
            await self.verifier.setup()
            self._verifier_setup = True

    async def generate_puzzle(self, **kwargs) -> Puzzle:
        r"""Generate a puzzle to be solved.

        This method should be implemented by subclasses to generate puzzles
        appropriate for the specific solver being used.

        Args:
            **kwargs: Additional generation parameters.

        Returns:
            Puzzle: A newly generated puzzle.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError(
            "Subclasses must implement generate_puzzle()"
        )

    async def _process_solution(
        self, solver_result: SolverResult
    ) -> DataPoint:
        r"""Process a solver result into a data point.

        Args:
            solver_result (SolverResult): The result from the solver.

        Returns:
            DataPoint: A data point created from the solver result.
        """
        # Extract the puzzle and solution from the solver result
        puzzle = solver_result.puzzle
        solution = solver_result.execution_result or ""

        # Create metadata combining puzzle metadata and solver metadata
        metadata = {
            "puzzle_id": puzzle.id,
            "puzzle_title": puzzle.title,
            "puzzle_source": puzzle.source,
            "solver_success": solver_result.success,
            **puzzle.metadata,
            **solver_result.metadata,
        }

        # If code is available, add it to metadata
        if solver_result.code:
            metadata["solution_code"] = solver_result.code

        # Create the data point
        return DataPoint(
            question=puzzle.problem,
            final_answer=solution,
            rationale=puzzle.ground_truth_solution,
            metadata=metadata,
        )

    async def generate_new(self, n: int, **kwargs) -> List[DataPoint]:
        r"""Generate n new datapoints using the solver.

        Args:
            n (int): Number of datapoints to generate.
            **kwargs: Additional generation parameters.

        Returns:
            List[DataPoint]: A list of newly generated datapoints.
        """
        # Ensure verifier is set up if it exists
        await self._ensure_verifier_setup()

        data_points = []
        for _ in range(n):
            # Generate a puzzle
            puzzle = await self.generate_puzzle(**kwargs)

            # Solve the puzzle using a thread pool to avoid blocking the event
            # loop
            loop = asyncio.get_event_loop()
            solver_result = await loop.run_in_executor(
                None, self.solver.solve_puzzle, puzzle
            )

            # Verify the solution if a verifier is available
            if self.verifier and solver_result.execution_result:
                verification_result = await self.verifier.verify(
                    solver_result.execution_result,
                    puzzle.ground_truth_solution,
                )

                # Update solver result metadata with verification results
                solver_result.metadata["verification"] = {
                    "status": verification_result.status.name.upper(),
                    "duration": verification_result.duration,
                }

                # Update success flag based on verification
                solver_result.success = (
                    verification_result.status.name.upper() == "SUCCESS"
                )

            # Process the solver result into a data point
            data_point = await self._process_solution(solver_result)
            data_points.append(data_point)

            # Save to cache if cache path is provided
            if self.cache:
                with self.cache.open("a", encoding="utf-8") as f:
                    json.dump(data_point.to_dict(), f, ensure_ascii=False)
                    f.write("\n")

        return data_points

    async def cleanup(self) -> None:
        r"""Clean up resources, including the verifier if it exists."""
        if self.verifier and self._verifier_setup:
            await self.verifier.cleanup()
            self._verifier_setup = False
