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
import os
from pathlib import Path
from typing import Generic, List, Optional, TypeVar, Union

from camel.logger import get_logger
from camel.solvers.base import BaseSolver
from camel.solvers.models import BaseSolverResult
from camel.verifiers.base import BaseVerifier
from camel.verifiers.models import VerificationOutcome

from .base_generator import BaseGenerator
from .models import DataPoint

logger = get_logger(__name__)

InputType = TypeVar('InputType')
OutputType = TypeVar('OutputType')


class GeneratorWithSolver(BaseGenerator, Generic[InputType, OutputType]):
    r"""A generator that uses a solver to generate data points.

    This generator leverages a solver to generate data points. It can
    optionally use a verifier to validate the solutions produced by the solver.

    The generator creates inputs, solves them using the provided solver, and
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

    async def generate_input(self, **kwargs) -> InputType:
        r"""Generate an input to be solved.

        This method should be implemented by subclasses to generate inputs
        appropriate for the specific solver being used.

        Args:
            **kwargs: Additional generation parameters.

        Returns:
            InputType: A newly generated input.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement generate_input()")

    async def _process_solution(
        self, solver_result: BaseSolverResult
    ) -> DataPoint:
        r"""Process a solver result into a data point.

        Args:
            solver_result (BaseSolverResult): The result from the solver.

        Returns:
            DataPoint: A data point created from the solver result.
        """
        # Extract the input and solution from the solver result
        input_data = solver_result.input_data
        solution = solver_result.output_data or ""

        # Create metadata combining input metadata and solver metadata
        metadata = {
            "solver_success": solver_result.success,
            **solver_result.metadata,
        }

        # Add input-related metadata if available
        if hasattr(input_data, "metadata") and input_data.metadata:
            metadata.update(input_data.metadata or {})

        # Add input ID if available
        if hasattr(input_data, "id"):
            metadata["input_id"] = input_data.id

        # Add any additional attributes from input_data that might be useful
        for attr in ["title", "source"]:
            if hasattr(input_data, attr):
                value = getattr(input_data, attr)
                if value is not None:
                    metadata[f"input_{attr}"] = value

        # If code is available, add it to metadata
        if solver_result.code:
            metadata["solution_code"] = solver_result.code

        # Get the problem statement and ground truth if available
        question = getattr(input_data, "problem", str(input_data))
        rationale = getattr(input_data, "ground_truth_solution", "")

        # Create the data point
        return DataPoint(
            question=question,
            final_answer=solution,
            rationale=rationale,
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
            try:
                # Generate an input
                input_data = await self.generate_input(**kwargs)

                # Solve the input using a thread pool to avoid blocking the
                # event loop
                loop = asyncio.get_event_loop()
                solver_result = await loop.run_in_executor(
                    None, self.solver.solve, input_data
                )

                # Verify the solution if a verifier is available
                if self.verifier and solver_result.output_data:
                    # Get the ground truth if available, otherwise pass None
                    ground_truth = getattr(
                        input_data, "ground_truth_solution", None
                    )

                    try:
                        verification_result = await self.verifier.verify(
                            solver_result.output_data,
                            ground_truth,
                        )

                        # Update solver result metadata with verification
                        # results
                        solver_result.metadata["verification"] = {
                            "status": verification_result.status.name.upper(),
                            "duration": verification_result.duration,
                        }

                        # Update success flag based on verification
                        solver_result.success = (
                            verification_result.status
                            == VerificationOutcome.SUCCESS
                        )
                    except Exception as e:
                        logger.error(f"Verification failed with error: {e!s}")
                        solver_result.metadata["verification_error"] = str(e)
                        solver_result.success = False

                # Process the solver result into a data point
                data_point = await self._process_solution(solver_result)
                data_points.append(data_point)

                # Save to cache if cache path is provided
                if self.cache:
                    # Use file locking to prevent race conditions
                    cache_file = self.cache
                    temp_file = cache_file.with_suffix('.tmp')
                    try:
                        with temp_file.open("w", encoding="utf-8") as f:
                            json.dump(
                                data_point.to_dict(), f, ensure_ascii=False
                            )
                            f.write("\n")
                        # Atomic rename operation to avoid partial writes
                        if os.name == 'nt':  # Windows
                            if cache_file.exists():
                                with cache_file.open(
                                    "a", encoding="utf-8"
                                ) as f:
                                    with temp_file.open(
                                        "r", encoding="utf-8"
                                    ) as temp:
                                        f.write(temp.read())
                            else:
                                temp_file.rename(cache_file)
                        else:  # Unix-like systems
                            temp_file.rename(
                                cache_file
                            ) if not cache_file.exists() else temp_file.open(
                                "r"
                            ).read() and cache_file.open("a").write(
                                temp_file.open("r").read()
                            )
                    except Exception as e:
                        logger.error(f"Failed to write to cache: {e!s}")
                    finally:
                        if temp_file.exists():
                            try:
                                temp_file.unlink()
                            except Exception:
                                pass

            except Exception as e:
                logger.error(f"Data point generation failed with error: {e!s}")

        return data_points

    async def cleanup(self) -> None:
        r"""Clean up resources, including the verifier if it exists."""
        if self.verifier and self._verifier_setup:
            await self.verifier.cleanup()
            self._verifier_setup = False

        # Clean up any temporary files that might have been created
        if self.cache:
            temp_file = self.cache.with_suffix('.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
