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

from typing import (
    Any,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from pydantic import BaseModel, Field

InputType = TypeVar('InputType')
OutputType = TypeVar('OutputType')


class Puzzle(BaseModel):
    r"""Base model for logic puzzles from any source.

    Attributes:
        id (str): Unique identifier for the puzzle.
        title (str): Title or name of the puzzle.
        problem (str): The problem statement or description.
        source (str): The source or origin of the puzzle.
        metadata (Dict[str, Any]): Additional metadata about the puzzle.
        clues (Optional[List[str]]): List of clues provided for the puzzle.
            (default: :obj:`None`)
        categories (Optional[List[str]]): Categories or topics the puzzle
            belongs to. (default: :obj:`None`)
        items (Optional[Dict[str, List[str]]]): Dictionary mapping category
            names to their respective items. (default: :obj:`None`)
        ground_truth_solution (Optional[str]): The correct solution to the
            puzzle. (default: :obj:`None`)
    """

    id: str = Field(..., description="Unique identifier for the puzzle.")
    title: str = Field(..., description="Title or name of the puzzle.")
    problem: str = Field(
        ..., description="The problem statement or description."
    )
    source: str = Field(..., description="The source or origin of the puzzle.")
    metadata: Dict[str, Any] = Field(
        ..., description="Additional metadata about the puzzle."
    )

    clues: Optional[List[str]] = Field(
        default=None, description="List of clues provided for the puzzle."
    )
    categories: Optional[List[str]] = Field(
        default=None, description="Categories or topics the puzzle belongs to."
    )
    items: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Dictionary mapping category names to their "
        "respective items.",
    )
    ground_truth_solution: Optional[str] = Field(
        default=None, description="The correct solution to the puzzle."
    )

    def to_dict(self) -> Dict[str, Any]:
        r"""Convert the puzzle to a dictionary for serialization.

        Returns:
            Dict[str, Any]: Dictionary representation of the puzzle
        """
        return self.model_dump(exclude_none=True)


@runtime_checkable
class PuzzleDataLoader(Protocol):
    r"""Protocol for puzzle data loaders.

    This protocol defines the interface that all puzzle data loaders must
    implement. It provides methods for loading puzzles from a data source and
    retrieving them.
    """

    def load(self) -> None:
        r"""Load puzzles from the data source.

        This method should initialize the data loader and load puzzles from
        the underlying data source.
        """
        ...

    def get_puzzles(self) -> Iterator[Puzzle]:
        r"""Get an iterator over puzzles in the data source.

        Returns:
            Iterator[Puzzle]: An iterator over all puzzles in the data source.
        """
        ...

    def get_puzzle_by_id(self, puzzle_id: str) -> Optional[Puzzle]:
        r"""Get a specific puzzle by ID.

        Args:
            puzzle_id (str): The ID of the puzzle to retrieve.

        Returns:
            Optional[Puzzle]: The puzzle with the specified ID, or None if not
                found.
        """
        ...


class BaseSolverResult(BaseModel, Generic[InputType, OutputType]):
    r"""Base model for all solver results.

    This generic class provides a standardized structure for results from any
    solver, regardless of the specific domain (puzzles, math problems, code
    generation, etc.).

    Attributes:
        input_id (str): Unique identifier for the input being processed.
        input_data (InputType): The input data that was processed.
        input_hash (str): Hash of the input for verification purposes.
        code (Optional[str]): The code or approach used to solve the problem.
            (default: :obj:`None`)
        output_data (Optional[OutputType]): The result of executing the
            solution. (default: :obj:`None`)
        success (bool): Whether the solution was successful. (default:
            :obj:`False`)
        metadata (Dict[str, Any]): Additional metadata about the solving
            process. (default: empty dict)
    """

    input_id: str = Field(
        ..., description="Unique identifier for the input being processed."
    )
    input_data: InputType = Field(
        ..., description="The input data that was processed."
    )
    input_hash: str = Field(
        ..., description="Hash of the input for verification purposes."
    )

    code: Optional[str] = Field(
        default=None,
        description="The code or approach used to solve the problem.",
    )
    output_data: Optional[OutputType] = Field(
        default=None, description="The result of executing the solution."
    )
    success: bool = Field(
        default=False, description="Whether the solution was successful."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the solving process.",
    )


class PuzzleSolverResult(BaseSolverResult[Puzzle, str]):
    r"""Result of a puzzle solving operation.

    This class extends BaseSolverResult with puzzle-specific functionality
    while maintaining backward compatibility with existing code.

    Attributes:
        input_id (str): Unique identifier for the puzzle being solved.
        input_data (Puzzle): The puzzle object being solved.
        input_hash (str): Hash of the puzzle for verification purposes.
        code (Optional[str]): The code or solution approach used to solve the
            puzzle. (default: :obj:`None`)
        output_data (Optional[str]): The result of executing the solution code.
            (default: :obj:`None`)
        success (bool): Whether the solution was successful. (default:
            :obj:`False`)
        metadata (Dict[str, Any]): Additional metadata about the solving
            process. (default: empty dict)
    """

    # For backward compatibility
    @property
    def puzzle_id(self) -> str:
        r"""Get the puzzle ID (alias for input_id).

        Returns:
            str: The puzzle ID.
        """
        return self.input_id

    @property
    def puzzle(self) -> Puzzle:
        r"""Get the puzzle object (alias for input_data).

        Returns:
            Puzzle: The puzzle object.
        """
        return self.input_data

    @property
    def puzzle_hash(self) -> str:
        r"""Get the puzzle hash (alias for input_hash).

        Returns:
            str: The puzzle hash.
        """
        return self.input_hash

    @property
    def execution_result(self) -> Optional[str]:
        r"""Get the execution result (alias for output_data).

        Returns:
            Optional[str]: The execution result.
        """
        return self.output_data
