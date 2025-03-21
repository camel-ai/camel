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
import asyncio
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Union

from pydantic import ValidationError
from torch.utils.data import IterableDataset

from camel.logger import get_logger

from .models import DataPoint

logger = get_logger(__name__)


class BaseGenerator(abc.ABC, IterableDataset):
    r"""Abstract base class for data generators.

    This class defines the interface for generating synthetic datapoints.
    Concrete implementations should provide specific generation strategies.
    """

    def __init__(
        self,
        seed: int = 42,
        cache: Union[str, Path, None] = None,
        data_path: Union[str, Path, None] = None,
        **kwargs,
    ):
        r"""Initialize the base generator.

        Args:
            seed (int): Random seed for reproducibility. (default: :obj:`42`)
            cache (Union[str, Path, None]): Optional path to save generated
                datapoints during iteration. If None is provided, datapoints
                will be discarded every 100 generations.
            data_path (Union[str, Path, None]): Optional path to a JSONL file
                to initialize the dataset from.
            **kwargs: Additional generator parameters.
        """
        self._rng = random.Random(seed)
        self.cache = Path(cache) if cache else None

        self._data: List[DataPoint] = []
        self._batch_to_save: List[DataPoint] = []

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

        If a `data_path` was provided during initialization, those datapoints
        are yielded first. When self._data is empty, 20 new datapoints
        are generated. Every 100 yields, the batch is appended to the
        JSONL file or discarded if `cache` is None.

        Yields:
            DataPoint: A single datapoint.
        """

        async def generator():
            while True:
                if not self._data:
                    new_datapoints = await self.generate_new(20)
                    self._data.extend(new_datapoints)
                datapoint = self._data.pop(0)
                yield datapoint
                self._batch_to_save.append(datapoint)
                if len(self._batch_to_save) == 100:
                    if self.cache:
                        with self.cache.open("a", encoding="utf-8") as f:
                            for dp in self._batch_to_save:
                                json.dump(dp.to_dict(), f, ensure_ascii=False)
                                f.write("\n")
                    self._batch_to_save = []

        return generator()

    def __iter__(self):
        r"""Synchronous iterator for PyTorch IterableDataset compatibility.

        If a `data_path` was provided during initialization, those datapoints
        are yielded first. When self._data is empty, 20 new datapoints
        are generated. Every 100 yields, the batch is appended to the
        JSONL file or discarded if `cache` is None.

        Yields:
            DataPoint: A single datapoint.
        """
        try:
            if asyncio.get_event_loop().is_running():
                raise RuntimeError(
                    "Cannot use synchronous iteration (__iter__) in an async "
                    "context; use 'async for' with __aiter__ instead"
                )
        except RuntimeError as e:
            if "no running event loop" not in str(e):
                raise

        while True:
            if not self._data:
                new_datapoints = asyncio.run(self.generate_new(20))
                self._data.extend(new_datapoints)
            datapoint = self._data.pop(0)
            yield datapoint
            self._batch_to_save.append(datapoint)
            if len(self._batch_to_save) == 100:
                if self.cache:
                    with self.cache.open("a", encoding="utf-8") as f:
                        for dp in self._batch_to_save:
                            json.dump(dp.to_dict(), f, ensure_ascii=False)
                            f.write("\n")
                self._batch_to_save = []

    def sample(self) -> DataPoint:
        r"""Returns the next datapoint from the current dataset
        synchronously.

        Raises:
            RuntimeError: If called in an async context.

        Returns:
            DataPoint: The next DataPoint.

        Note:
            This method is intended for synchronous contexts.
            Use 'async_sample' in asynchronous contexts to
            avoid blocking or runtime errors.
        """
        try:
            if asyncio.get_event_loop().is_running():
                raise RuntimeError(
                    "Cannot use synchronous sampling (sample) "
                    "in an async context; use async_sample instead"
                )
        except RuntimeError as e:
            if "no running event loop" not in str(e):
                raise

        return next(iter(self))

    async def async_sample(self) -> DataPoint:
        r"""Returns the next datapoint from the current dataset asynchronously.

        Returns:
            DataPoint: The next datapoint.

        Note:
            This method is intended for asynchronous contexts. Use 'sample'
            in synchronous contexts.
        """

        async_iter = self.__aiter__()
        return await async_iter.__anext__()

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
            - Appends to the file if it already exists.
            - Ensures compatibility with large datasets by using JSONL format.
        """
        if not self._data:
            raise ValueError("Dataset is empty. No data to save.")

        file_path = Path(file_path)

        try:
            with file_path.open("a", encoding="utf-8") as f:
                for datapoint in self._data:
                    json.dump(datapoint.to_dict(), f, ensure_ascii=False)
                    f.write("\n")
            logger.info(f"Dataset saved successfully to {file_path}")
        except IOError as e:
            logger.error(f"Error writing to file {file_path}: {e}")
            raise

    def flush(self, file_path: Union[str, Path]) -> None:
        r"""Flush the current data to a JSONL file and clear the data.

        Args:
            file_path (Union[str, Path]): Path to save the JSONL file.

        Notes:
            - Uses `save_to_jsonl` to save `self._data`.
        """

        self.save_to_jsonl(file_path)
        self._data = []
        logger.info(f"Data flushed to {file_path} and cleared from the memory")

    def _init_from_jsonl(self, file_path: Path) -> List[Dict[str, Any]]:
        r"""Load and parse a dataset from a JSONL file.

        Args:
            file_path (Path): Path to the JSONL file.

        Returns:
            List[Dict[str, Any]]: A list of datapoint dictionaries.

        Raises:
            FileNotFoundError: If the specified JSONL file does not exist.
            ValueError: If a line contains invalid JSON or is not a dictionary.
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
                        f"Invalid JSON on line {line_number} "
                        f"in file {file_path}: {e}"
                    )
                if not isinstance(record, dict):
                    raise ValueError(
                        f"Expected a dictionary at line {line_number}, "
                        f"got {type(record).__name__}"
                    )
                raw_data.append(record)
        logger.info(
            f"Successfully loaded {len(raw_data)} items from {file_path}"
        )
        return raw_data
