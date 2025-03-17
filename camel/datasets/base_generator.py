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

import abc
import json
import random
from pathlib import Path
from typing import List, Union

from camel.logger import get_logger

from .models import DataPoint

logger = get_logger(__name__)


class BaseGenerator(abc.ABC):
    r"""Abstract base class for data generators.

    This class defines the interface for generating synthetic datapoints.
    Concrete implementations should provide specific generation strategies.
    """

    def __init__(self, seed: int = 42, **kwargs):
        r"""Initialize the base generator.

        Args:
            seed (int): Random seed for reproducibility. (default: :obj:`42`)
            **kwargs: Additional generator parameters.
        """
        self._rng = random.Random(seed)

        self._data: List[DataPoint] = []

    @abc.abstractmethod
    async def generate_new(self, n: int, **kwargs) -> List[DataPoint]:
        r"""Generate n new datapoints.

        Args:
            n (int): Number of datapoints to generate.
            **kwargs: Additional generation parameters.

        Returns:
            List[DataPoint]: A list of newly generated datapoints.
        """
        pass

    def __len__(self) -> int:
        r"""Return the size of the generated dataset."""
        return len(self._data)

    def __getitem__(self, idx: int) -> DataPoint:
        r"""Retrieve a datapoint by index.

        Args:
            idx (int): Index of the datapoint.

        Returns:
            DataPoint: The datapoint corresponding to the given index.

        Raises:
            IndexError: If idx is out of bounds.
        """
        if idx < 0 or idx >= len(self._data):
            raise IndexError(
                f"Index {idx} out of bounds for dataset of "
                f"size {len(self._data)}"
            )
        return self._data[idx]

    def sample(self) -> DataPoint:
        if len(self._data) == 0:
            raise RuntimeError("Dataset is empty, cannot sample.")
        idx = self._rng.randint(0, len(self._data) - 1)
        return self[idx]

    def save_to_jsonl(self, file_path: Union[str, Path]) -> None:
        r"""Saves the generated datapoints to a JSONL (JSON Lines) file.

        Each datapoint is stored as a separate JSON object on a new line.

        Args:
            file_path (Union[str, Path]): Path to save the JSONL file.

        Raises:
            ValueError: If no datapoints have been generated.
            IOError: If there is an issue writing to the file.

        Notes:
            - Uses `self._data`, which contains the generated datapoints.
            - Overwrites the file if it already exists.
            - Ensures compatibility with large datasets by using JSONL format.
        """
        if not self._data:
            raise ValueError("Dataset is empty. No data to save.")

        file_path = Path(file_path)

        try:
            with file_path.open("w", encoding="utf-8") as f:
                for datapoint in self._data:
                    json.dump(datapoint.to_dict(), f)
                    f.write("\n")  # Ensure each entry is on a new line
            logger.info(f"Dataset saved successfully to {file_path}")
        except IOError as e:
            logger.error(f"Error writing to file {file_path}: {e}")
            raise

    def flush(self, file_path: Union[str, Path]) -> None:
        r"""Flush the current data to a JSONL file and clear the data.

        Args:
            file_path (Union[str, Path]): Path to save the JSONL file.

        Notes:
            - Uses save_to_jsonl for the saving process.
        """

        self.save_to_jsonl(file_path)
        self._data = []
        logger.info(
            f"Data flushed to {file_path} and cleared from the memmory"
        )
