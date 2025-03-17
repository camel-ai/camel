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
from typing import Any, Dict, List, Union
from pydantic import ValidationError

from camel.logger import get_logger

from .models import DataPoint

logger = get_logger(__name__)


class BaseGenerator(abc.ABC):
    r"""Abstract base class for data generators.

    This class defines the interface for generating synthetic datapoints.
    Concrete implementations should provide specific generation strategies.
    """

    def __init__(
        self,
        save_to: Union[str, Path],
        seed: int = 42,
        data_path: Union[str, Path, None] = None,
        **kwargs,
    ):
        r"""Initialize the base generator.

        Args:
            save_to (Union[str, Path]): Path to save generated datapoints during iteration.
            seed (int): Random seed for reproducibility. (default: :obj:`42`)
            data_path (Union[str, Path, None]): Optional path to a JSONL file to
                initialize the dataset from.
            **kwargs: Additional generator parameters.
        """
        self._rng = random.Random(seed)
        self.save_to = Path(save_to)

        self._data: List[DataPoint] = []

        if data_path:
            file_path = Path(data_path)
            raw_data = self._init_from_jsonl(file_path)
            try:
                data_points = [DataPoint(**item) for item in raw_data]
                self._data.extend(data_points)
            except ValidationError as e:
                raise ValueError(
                    f"Failed to create DataPoint from JSONL data: {e}"
                )

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

    def __aiter__(self):
        r"""Async iterator that yields datapoints dynamically.

        Yields one datapoint at a time. If data_path was provided, yields those first.
        When self._data is empty, generates 20 new datapoints. Every 100 yields appends
        the batch to the specified JSONL file.
        """
        batch_to_save = []

        async def generator():
            nonlocal batch_to_save
            while True:
                if not self._data:
                    new_datapoints = await self.generate_new(20)
                    self._data.extend(new_datapoints)
                datapoint = self._data.pop(0)
                yield datapoint
                batch_to_save.append(datapoint)
                if len(batch_to_save) == 100:
                    with self.save_to.open("a", encoding="utf-8") as f:
                        for dp in batch_to_save:
                            json.dump(dp.to_dict(), f)
                            f.write("\n")
                    batch_to_save = []

        return generator()

    def sample(self) -> DataPoint:
        r"""Sample a random datapoint from the current dataset."""
        if len(self._data) == 0:
            raise RuntimeError("Dataset is empty, cannot sample.")
        idx = self._rng.randint(0, len(self._data) - 1)
        return self._data[idx]

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
                    json.dump(datapoint.to_dict(), f, ensure_ascii=False)
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

    def _init_from_jsonl(self, file_path: Path) -> List[Dict[str, Any]]:
        r"""Load and parse a dataset from a JSONL file.

        Args:
            file_path (Path): Path to the JSONL file.

        Returns:
            List[Dict[str, Any]]: A list of datapoint dictionaries.

        Raises:
            FileNotFoundError: If the specified JSONL file does not exist.
            ValueError: If a line in the file contains invalid JSON or is not a dictionary.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"JSONL file not found: {file_path}")

        raw_data = []
        logger.debug(f"Loading JSONL from {file_path}")
        with file_path.open('r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue  # Skip blank lines
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Invalid JSON on line {line_number} in file {file_path}: {e}"
                    )
                if not isinstance(record, dict):
                    raise ValueError(
                        f"Expected a dictionary at line {line_number}, got {type(record).__name__}"
                    )
                raw_data.append(record)
        logger.info(
            f"Successfully loaded {len(raw_data)} items from {file_path}"
        )
        return raw_data
