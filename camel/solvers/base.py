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

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from .models import Puzzle, PuzzleDataLoader, SolverResult


@runtime_checkable
class PuzzleSolver(Protocol):
    r"""Protocol for puzzle solvers.

    This protocol defines the interface that all puzzle solvers must implement,
    providing a standard way to solve puzzles regardless of the underlying
    implementation.
    """

    def solve_puzzle(self, puzzle: Puzzle) -> SolverResult:
        r"""Solve a single puzzle.

        Args:
            puzzle (Puzzle): The puzzle to solve.

        Returns:
            SolverResult: Solution result containing puzzle data, code,
                execution result, and success status.
        """
        ...


class BaseSolver(ABC, PuzzleSolver):
    r"""Abstract base class for puzzle solvers.

    This class provides a foundation for implementing puzzle solvers with
    common functionality such as data loading and result storage.
    """

    def __init__(
        self,
        data_loader: Optional[PuzzleDataLoader] = None,
        model_name: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        r"""Initialize the solver.

        Args:
            data_loader (Optional[PuzzleDataLoader]): Data loader to use for
                loading puzzles. (default: :obj:`None`)
            model_name (Optional[str]): Name of the model to use (if
                applicable). (default: :obj:`None`)
            output_dir (Optional[str]): Directory to save results to.
                (default: :obj:`"output"`)
        """
        self.data_loader = data_loader
        self.model_name = model_name
        self.output_dir = Path(output_dir) if output_dir else Path("output")
        self.output_dir.mkdir(exist_ok=True)

    @abstractmethod
    def solve_puzzle(self, puzzle: Puzzle) -> SolverResult:
        r"""Solve a single puzzle.

        Args:
            puzzle (Puzzle): The puzzle to solve.

        Returns:
            SolverResult: Solution result containing puzzle data, code,
                execution result, and success status.
        """
        pass
