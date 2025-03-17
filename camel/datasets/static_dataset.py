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
import json
import random
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sized,
    Union,
)

from datasets import Dataset as HFDataset
from pydantic import ValidationError
from torch.utils.data import Dataset

from camel.logger import get_logger

from .models import DataPoint

logger = get_logger(__name__)


class StaticDataset(Dataset):
    r"""A static dataset containing a list of datapoints.
    Ensures that all items adhere to the DataPoint schema.
    This dataset extends :obj:`Dataset` from PyTorch and should
    be used when its size is fixed at runtime.

    This class can initialize from Hugging Face Datasets,
    PyTorch Datasets, JSON file paths, or lists of dictionaries,
    converting them into a consistent internal format.
    """

    def __init__(
        self,
        data: Union[HFDataset, Dataset, Path, List[Dict[str, Any]]],
        seed: int = 42,
        min_samples: int = 1,
        strict: bool = False,
        **kwargs,
    ):
        r"""Initialize the static dataset and validate integrity.

        Args:
            data (Union[HFDataset, Dataset, Path, List[Dict[str, Any]]]):
                Input data, which can be one of the following:
                - A Hugging Face Dataset (:obj:`HFDataset`).
                - A PyTorch Dataset (:obj:`torch.utils.data.Dataset`).
                - A :obj:`Path` object representing a JSON or JSONL file.
                - A list of dictionaries with :obj:`DataPoint`-compatible
                  fields.
            seed (int): Random seed for reproducibility.
                (default: :obj:`42`)
            min_samples (int): Minimum required number of samples.
                (default: :obj:`1`)
            strict (bool): Whether to raise an error on invalid
                datapoints (:obj:`True`) or skip/filter them (:obj:`False`).
                (default: :obj:`False`)
            **kwargs: Additional dataset parameters.

        Raises:
            TypeError: If the input data type is unsupported.
            ValueError: If the dataset contains fewer than :obj:`min_samples`
                datapoints or if validation fails.
            FileNotFoundError: If the specified JSON file path does not exist.
            json.JSONDecodeError: If the JSON file contains invalid formatting.
        """

        # Store all parameters in metadata dict for compatibility
        self._metadata = {
            **kwargs,
        }
        self._rng = random.Random(seed)
        self._strict = strict

        self.data: List[DataPoint] = self._init_data(data)
        self._length = len(self.data)

        if self._length < min_samples:
            raise ValueError(
                "The dataset does not contain enough samples. "
                f"Need {max(0, min_samples)}, got {self._length}"
            )

    def _init_data(
        self, data: Union[HFDataset, Dataset, Path, List[Dict[str, Any]]]
    ) -> List[DataPoint]:
        r"""Convert input data from various formats into a list of
        :obj:`DataPoint` instances.

        Args:
            data (Union[HFDataset, Dataset, Path, List[Dict[str, Any]]]): Input
                dataset in one of the supported formats.

        Returns:
            List[DataPoint]: A list of validated :obj:`DataPoint`
                instances.

        Raises:
            TypeError: If the input data type is unsupported.
            ValueError: If the Path has an unsupported file extension.
        """

        if isinstance(data, HFDataset):
            raw_data = self._init_from_hf_dataset(data)
        elif isinstance(data, Dataset):
            raw_data = self._init_from_pytorch_dataset(data)
        elif isinstance(data, Path):
            if data.suffix == ".jsonl":
                raw_data = self._init_from_jsonl_path(data)
            elif data.suffix == ".json":
                raw_data = self._init_from_json_path(data)
            else:
                raise ValueError(
                    f"Unsupported file extension: {data.suffix}."
                    " Please enter a .json or .jsonl object."
                )

        elif isinstance(data, list):
            raw_data = self._init_from_list(data)
        else:
            raise TypeError("Unsupported data type")

        def create_datapoint(
            item: Dict[str, Any], idx: int
        ) -> Optional[DataPoint]:
            # Add type checks for required fields to make mypy happy
            question = item.get('question')
            if not isinstance(question, str):
                if self._strict:
                    raise ValueError(
                        f"Sample at index {idx} has invalid 'question': "
                        f"expected str, got {type(question)}"
                    )
                else:
                    logger.warning(
                        f"Skipping sample at index {idx}: invalid 'question'"
                    )
                    return None

            rationale = item.get('rationale')
            if not isinstance(rationale, str):
                if self._strict:
                    raise ValueError(
                        f"Sample at index {idx} has invalid 'rationale': "
                        f"expected str, got {type(rationale)}"
                    )
                else:
                    logger.warning(
                        f"Skipping sample at index {idx}: invalid 'rationale'"
                    )
                    return None

            final_answer = item.get('final_answer')
            if not isinstance(final_answer, str):
                if self._strict:
                    raise ValueError(
                        f"Sample at index {idx} has invalid 'final_answer': "
                        f"expected str, got {type(final_answer)}"
                    )
                else:
                    logger.warning(
                        f"Skipping sample at index {idx}: "
                        "invalid 'final_answer'"
                    )
                    return None

            try:
                return DataPoint(
                    question=question,
                    rationale=rationale,
                    final_answer=final_answer,
                    metadata=item.get('metadata'),
                )
            except ValidationError as e:
                if self._strict:
                    raise ValueError(
                        f"Sample at index {idx} validation error: {e}"
                    )
                else:
                    logger.warning(
                        f"Skipping invalid sample at index {idx} "
                        f"due to validation error: {e}"
                    )
                    return None

        unfiltered_data = [
            create_datapoint(item, i) for i, item in enumerate(raw_data)
        ]
        return [dp for dp in unfiltered_data if dp is not None]

    def __len__(self) -> int:
        r"""Return the size of the dataset."""
        return self._length

    def __getitem__(self, idx: int) -> DataPoint:
        r"""Retrieve a datapoint by index.

        Args:
            idx (int): Index of the datapoint.

        Returns:
            DataPoint: The datapoint corresponding to the given index.

        Raises:
            IndexError: If :obj:`idx` is out of bounds (negative or greater
                than dataset length - 1).
        """

        if idx < 0 or idx >= self._length:
            raise IndexError(
                f"Index {idx} out of bounds for dataset of size {self._length}"
            )
        return self.data[idx]

    def sample(self) -> DataPoint:
        r"""Sample a random datapoint from the dataset.

        Returns:
            DataPoint: A randomly sampled :obj:`DataPoint`.

        Raises:
            RuntimeError: If the dataset is empty and no samples can be drawn.
        """

        if self._length == 0:
            raise RuntimeError("Dataset is empty, cannot sample.")
        idx = self._rng.randint(0, self._length - 1)
        return self[idx]

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Retrieve dataset metadata.

        Returns:
            Dict[str, Any]: A copy of the dataset metadata dictionary.
        """

        return self._metadata.copy()

    def _init_from_hf_dataset(self, data: HFDataset) -> List[Dict[str, Any]]:
        r"""Convert a Hugging Face dataset into a list of dictionaries.

        Args:
            data (HFDataset): A Hugging Face dataset.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing
                the dataset, where each dictionary corresponds to a datapoint.
        """
        return [dict(item) for item in data]

    def _init_from_pytorch_dataset(
        self, data: Dataset
    ) -> List[Dict[str, Any]]:
        r"""Convert a PyTorch dataset into a list of dictionaries.

        Args:
            data (Dataset): A PyTorch dataset.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing
                the dataset.

        Raises:
            TypeError: If the dataset does not implement :obj:`__len__()`
                or contains non-dictionary elements.
        """
        if not isinstance(data, Sized):
            raise TypeError(
                f"{type(data).__name__} does not implement `__len__()`."
            )
        raw_data = []

        for i in range(len(data)):
            item = data[i]
            if not isinstance(item, dict):
                raise TypeError(
                    f"Item at index {i} is not a dict: "
                    f"got {type(item).__name__}"
                )
            raw_data.append(dict(item))
        return raw_data

    def _init_from_json_path(self, data: Path) -> List[Dict[str, Any]]:
        r"""Load and parse a dataset from a JSON file.

        Args:
            data (Path): Path to the JSON file.

        Returns:
            List[Dict[str, Any]]: A list of datapoint dictionaries.

        Raises:
            FileNotFoundError: If the specified JSON file does not exist.
            ValueError: If the JSON content is not a list of dictionaries.
            json.JSONDecodeError: If the JSON file has invalid formatting.
        """

        if not data.exists():
            raise FileNotFoundError(f"JSON file not found: {data}")
        try:
            logger.debug(f"Loading JSON from {data}")
            with data.open('r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            logger.info(
                f"Successfully loaded {len(loaded_data)} items from {data}"
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {data}: {e}")
        if not isinstance(loaded_data, list):
            raise ValueError("JSON file must contain a list of dictionaries")
        for i, item in enumerate(loaded_data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Expected a dictionary at index {i}, "
                    f"got {type(item).__name__}"
                )
        return loaded_data

    def _init_from_jsonl_path(self, data: Path) -> List[Dict[str, Any]]:
        r"""Load and parse a dataset from a JSONL file.

        Args:
            data (Path): Path to the JSONL file.

        Returns:
            List[Dict[str, Any]]: A list of datapoint dictionaries.

        Raises:
            FileNotFoundError: If the specified JSONL file does not exist.
            ValueError: If a line in the file contains invalid JSON or
                is not a dictionary.
        """
        if not data.exists():
            raise FileNotFoundError(f"JSONL file not found: {data}")

        raw_data = []
        logger.debug(f"Loading JSONL from {data}")
        with data.open('r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue  # Skip blank lines if any exist.
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Invalid JSON on line {line_number} in file "
                        f"{data}: {e}"
                    )
                raw_data.append(record)
        logger.info(f"Successfully loaded {len(raw_data)} items from {data}")

        for i, item in enumerate(raw_data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Expected a dictionary at record {i+1} (line {i+1}), "
                    f"got {type(item).__name__}"
                )
        return raw_data

    def _init_from_list(
        self, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        r"""Validate and convert a list of dictionaries into a dataset.

        Args:
            data (List[Dict[str, Any]]): A list of dictionaries where
                each dictionary must be a valid :obj:`DataPoint`.

        Returns:
            List[Dict[str, Any]]: The validated list of dictionaries.

        Raises:
            ValueError: If any item in the list is not a dictionary.
        """
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Expected a dictionary at index {i}, "
                    f"got {type(item).__name__}"
                )
        return data
