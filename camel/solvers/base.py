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
from typing import Any, Dict, Generic, Optional, TypeVar

from .models import Puzzle, PuzzleDataLoader, PuzzleSolverResult

InputType = TypeVar('InputType')
OutputType = TypeVar('OutputType')


class BaseSolver(ABC, Generic[InputType, OutputType]):
    r"""Abstract base class for general solvers.

    This class provides a foundation for implementing solvers with
    common functionality such as data loading and result storage.
    """

    def __init__(
        self,
        data_loader: Optional[Any] = None,
        model_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ):
        r"""Initialize the solver.

        Args:
            data_loader (Optional[Any]): Data loader to use for
                loading input data. (default: :obj:`None`)
            model_name (Optional[str]): Name of the model to use (if
                applicable). (default: :obj:`None`)
            output_dir (Optional[str]): Directory to save results to.
                (default: :obj:`"output"`)
            **kwargs: Additional keyword arguments for specific solver
                implementations.
        """
        self.data_loader = data_loader
        self.model_name = model_name
        self.output_dir = Path(output_dir) if output_dir else Path("output")
        self.output_dir.mkdir(exist_ok=True)

        # Store additional configuration parameters
        self.config = kwargs

    @abstractmethod
    def solve(self, input_data: InputType) -> OutputType:
        r"""Solve a problem.

        Args:
            input_data (InputType): The input data for the problem.

        Returns:
            OutputType: The solution result.
        """
        pass


class BasePuzzleSolver(BaseSolver[Puzzle, PuzzleSolverResult]):
    r"""Abstract base class for puzzle solvers.

    This class provides a foundation for implementing puzzle solvers with
    common functionality such as data loading and result storage.
    """

    def __init__(
        self,
        data_loader: Optional[PuzzleDataLoader] = None,
        model_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        **kwargs: Dict[str, Any],
    ):
        r"""Initialize the puzzle solver.

        Args:
            data_loader (Optional[PuzzleDataLoader]): Data loader to use for
                loading puzzles. (default: :obj:`None`)
            model_name (Optional[str]): Name of the model to use (if
                applicable). (default: :obj:`None`)
            output_dir (Optional[str]): Directory to save results to.
                (default: :obj:`"output"`)
            **kwargs: Additional keyword arguments for specific puzzle solver
                implementations.
        """
        super().__init__(data_loader, model_name, output_dir, **kwargs)

    @abstractmethod
    def solve(self, input_data: Puzzle) -> PuzzleSolverResult:
        r"""Solve a puzzle (implementation of the generic solve method).

        Args:
            input_data (Puzzle): The puzzle to solve.

        Returns:
            PuzzleSolverResult: The solution result.
        """
        pass
