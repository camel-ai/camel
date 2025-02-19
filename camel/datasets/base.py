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
from typing import Any, Dict, Iterator, Optional

from pydantic import BaseModel, Field


class DataPoint(BaseModel):
    r"""A single data point in the dataset.

    Attributes:
        question: The question to pose to the LLM
        ground_truth: The ground truth answer for verification
        metadata: Additional metadata about the data point
    """

    question: str = Field(..., description="The question to pose to the LLM")
    ground_truth: Any = Field(
        ..., description="The ground truth answer for verification"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata about the data point"
    )


class BaseDataset(ABC):
    r"""A dataset contains questions and ground truth data for training.
    It can be either static (e.g., MATH dataset) or generative
    (using an LLM to generate questions).
    """

    def __init__(self, **kwargs):
        r"""Initialize the dataset.

        Args:
            **kwargs: Additional dataset parameters
        """
        self._current_index = 0
        self._metadata = kwargs
        self._is_initialized = False

    @abstractmethod
    async def cleanup(self) -> None:
        r"""Clean up dataset resources.

        This method handles cleanup of resources and resets the dataset state.
        It ensures:
        1. All resources are properly released
        2. State is reset to initial
        3. Cleanup happens even if errors occur
        """
        if not self._is_initialized:
            return

        try:
            # Reset dataset state
            self._current_index = 0

            # Clear any cached data
            self._metadata = {}

        finally:
            # Always mark as uninitialized, even if cleanup fails
            self._is_initialized = False

    @abstractmethod
    def __len__(self) -> int:
        r"""Return the size of the dataset."""
        pass

    @abstractmethod
    def __getitem__(self, idx: int) -> DataPoint:
        r"""Get an item from the dataset.

        Args:
            idx: Index of the item to get

        Returns:
            DataPoint containing question, ground truth, and metadata

        Raises:
            IndexError: If idx is out of bounds
            ValidationError: If data point is invalid
        """
        pass

    def __iter__(self) -> Iterator[DataPoint]:
        r"""Create an iterator over the dataset."""
        return self

    def __next__(self) -> DataPoint:
        r"""Get the next item from the dataset."""
        if self._current_index >= len(self):
            self._current_index = 0
            raise StopIteration
        item = self[self._current_index]
        self._current_index += 1
        return item

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Get dataset metadata."""
        return self._metadata.copy()

    def reset(self) -> None:
        r"""Reset the dataset iterator."""
        self._current_index = 0
