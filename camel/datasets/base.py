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
import os
import random
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sized,
    TypeVar,
    Union,
)

import torch
from datasets import Dataset as HFDataset
from pydantic import BaseModel, Field, ValidationError
from torch.utils.data import DataLoader, Dataset

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.verifiers import BaseVerifier

logger = get_logger(__name__)


class DataPoint(BaseModel):
    r"""A single data point in the dataset.

    Attributes:
        question (str): The primary question or issue to be addressed.
        rationale (str): Logical reasoning or explanation behind the
            answer.
        final_answer (str): The final answer.
        raw_markdown (Optional[str]): Raw markdown content for generating
            rewards/hints. (default: :obj:`None`)
        difficulty (Optional[str]): Difficulty level of the question.
            (default: :obj:`None`)
        metadata Optional[Dict[str, Any]]: Additional metadata about the data
            point. (default: :obj:`None`)
    """

    question: str = Field(
        ..., description="The primary question or issue to be addressed."
    )
    rationale: str = Field(
        ..., description="Logical reasoning or explanation behind the answer."
    )
    final_answer: str = Field(..., description="The final answer.")
    difficulty: Optional[str] = Field(
        None, description="Difficulty level of the question."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata about the data point."
    )

    def to_dict(self) -> Dict[str, Any]:
        r"""Convert DataPoint to a dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation of the DataPoint.
        """
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataPoint':
        r"""Create a DataPoint from a dictionary.

        Args:
            data (Dict[str, Any]): Dictionary containing DataPoint fields.

        Returns:
            DataPoint: New DataPoint instance.
        """
        return cls(**data)


class BaseDataset(Dataset):
    r"""A dataset contains questions and ground truth data for training.
    It can be either static (e.g., MATH dataset) or generative
    (using an LLM to generate questions).
    """

    def __init__(
        self,
        data: List[Dict[str, str]],
        cache_dir: Optional[str] = None,
        **kwargs,
    ):
        r"""Initialize the dataset.

        Args:
            data (List[Dict[str, str]]): List of dictionary items to
                create the dataset from.
            cache_dir (Optional[str]): Directory to cache dataset files.
                (default: :obj:`None`)
            **kwargs: Additional dataset parameters.

        Note:
            The dataset must be initialized by calling setup() before use.
        """
        self._is_setup = False
        self._raw_data: List[Dict[str, str]] = data if data is not None else []
        self._cache_dir = str(cache_dir) if cache_dir is not None else None

        # Store all parameters in metadata dict for compatibility
        self._metadata = {
            'cache_dir': self._cache_dir,
            **kwargs,
        }

        self.data: List[DataPoint] = []  # Will be populated in setup()

    async def setup(self) -> None:
        r"""Set up the dataset with necessary resources.

        This method:
        1. Creates cache directory if needed
        2. Processes raw data into DataPoint objects using vectorized
        operations
        3. Validates dataset integrity

        Raises:
            OSError: If cache directory creation fails.
            Exception: If dataset initialization fails.
        """
        if self._is_setup:
            logger.debug(f"{self.__class__.__name__} already initialized")
            return

        try:
            # Create cache directory if specified
            if self._cache_dir:
                try:
                    os.makedirs(self._cache_dir, exist_ok=True)
                    logger.debug(f"Created cache directory: {self._cache_dir}")
                except OSError as e:
                    logger.error(
                        f"Failed to create cache directory "
                        f"{self._cache_dir}: {e}"
                    )
                    raise

            # Process raw data into DataPoint objects using vectorized
            # operations
            if not self._raw_data:
                self.data = []
                logger.debug("No raw data to process")
            else:
                try:
                    # Helper function for validation that can be used with map
                    def create_datapoint(item, idx=None):
                        try:
                            return DataPoint(
                                question=item.get('question', ''),
                                rationale=item.get('rationale', ''),
                                final_answer=item.get('final_answer', ''),
                                metadata=item.get('metadata', {})
                                if isinstance(item.get('metadata'), dict)
                                else {},
                                raw_markdown='',
                                difficulty='',
                            )
                        except ValidationError as e:
                            idx_str = (
                                f" at index {idx}" if idx is not None else ""
                            )
                            error_msg = (
                                f"Sample{idx_str} validation error: {e}"
                            )
                            logger.error(error_msg)
                            raise ValueError(error_msg)

                    # If raw_data is already a HF dataset, use its map function
                    if hasattr(self._raw_data, 'map') and callable(
                        self._raw_data.map
                    ):
                        # Using HF dataset's map for vectorized processing
                        processed_data = self._raw_data.map(
                            lambda example, idx: {
                                'datapoint': create_datapoint(example, idx)
                            },
                            with_indices=True,
                        )
                        self.data = [
                            item['datapoint'] for item in processed_data
                        ]
                    else:
                        # Bulk create datapoints
                        self.data = [
                            create_datapoint(item, i)
                            for i, item in enumerate(self._raw_data)
                        ]

                    logger.debug(f"Processed {len(self.data)} data points")
                except Exception as e:
                    logger.error(f"Error processing data: {e}")
                    raise

            self._is_setup = True
            logger.info(f"{self.__class__.__name__} initialized successfully")

        except Exception as e:
            logger.error(f"Error during {self.__class__.__name__} setup: {e}")
            await self.cleanup()
            raise

    async def cleanup(self) -> None:
        r"""Clean up dataset resources.

        This method handles cleanup of resources and resets the dataset state.
        """
        if not self._is_setup:
            return

        try:
            # Clear metadata while preserving init config
            init_config = {
                'cache_dir': self._cache_dir,
            }
            self._metadata = init_config

            logger.info(f"{self.__class__.__name__} cleaned up successfully")

        except Exception as e:
            logger.error(
                f"Error during {self.__class__.__name__} cleanup: {e}"
            )
            raise

        finally:
            # Always mark as uninitialized, even if cleanup fails
            self._is_setup = False

    def sample(self) -> DataPoint:
        r"""Sample a random datapoint from the dataset.

        Returns:
            DataPoint: A randomly sampled DataPoint.

        Raises:
            RuntimeError: If dataset is not initialized.
        """
        if not self._is_setup:
            raise RuntimeError(
                f"{self.__class__.__name__} must be initialized "
                "before sampling"
            )

        idx = random.randint(0, len(self) - 1)
        return self[idx]

    def __len__(self) -> int:
        r"""Return the size of the dataset."""
        return len(self.data)

    def __getitem__(self, idx: int) -> DataPoint:
        r"""Get an item from the dataset.

        Args:
            idx (int): Index of the item to get.

        Returns:
            DataPoint: DataPoint from the dataset with the given index.

        Raises:
            IndexError: If idx is out of bounds.
        """
        if idx < 0 or idx >= len(self):
            raise IndexError(
                f"Index {idx} out of bounds for dataset of size {len(self)}"
            )

        return self.data[idx]

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Get dataset metadata."""
        return self._metadata.copy()

    def to_pytorch_dataset(
        self,
        transform: Optional[Callable] = None,
        target_transform: Optional[Callable] = None,
        batch_size: Optional[int] = None,
    ) -> Union["PyTorchDataset", "DataLoader"]:
        r"""Convert to a PyTorch dataset or DataLoader.

        Args:
            transform (Optional[Callable]): Transform to apply to samples.
            target_transform (Optional[Callable]): Transform to apply to
                targets.
            batch_size (Optional[int]): If provided, returns a DataLoader with
                the specified batch size instead of a PyTorchDataset.
                (default: :obj:`None`)

        Returns:
            Union[PyTorchDataset, torch.utils.data.DataLoader]: Dataset in
                PyTorch format or DataLoader if batch_size is provided.
        """
        dataset = PyTorchDataset.from_datapoints(
            self.data,
            transform=transform,
            target_transform=target_transform,
        )

        if batch_size is not None:
            return dataset.get_dataloader(batch_size=batch_size)

        return dataset


class SeedDataset(BaseDataset):
    r"""A dataset containing validated seed examples for data generation.
    Ensures that all items adhere to the DataPoint schema.

    This class can initialize from Hugging Face Datasets,
    PyTorch Datasets, JSON file paths, or lists of dictionaries,
    converting them into a consistent internal format.
    """

    def __init__(
        self,
        data: Union[HFDataset, Dataset, Path, List[Dict[str, Any]]],
        cache_dir: Optional[str] = None,
        seed: Optional[int] = None,
        min_samples: int = 1,
        strict: bool = False,
        **kwargs,
    ):
        r"""Initialize the seed dataset and validate integrity.

        Args:
            data (Union[HFDataset, Dataset, Path, List[Dict[str, Any]]]):
            Input data, which can be:
                - A Hugging Face Dataset (HFDataset)
                - A PyTorch Dataset (torch.utils.data.Dataset)
                - A Path object representing the path to a JSON file
                - A list of dictionaries with DataPoint-compatible fields
            seed (Optional[int]): Seed for reproducibility.
                (default: :obj:`1`)
            min_samples (int): Minimum number of samples required.
                (default: :obj:`1`)
            strict (bool): Whether to raise an error on invalid datapoints
                (True) or skip/filter them (False). (default: False)
            **kwargs: Additional dataset parameters.

        Raises:
            TypeError: If the data type is not supported.
            ValueError: If dataset size is less than min_samples or
            if sample validation fails.
            FileNotFoundError: If the JSON file path doesn't exist.
            json.JSONDecodeError: If the JSON file is invalid.
        """
        # Initialize BaseDataset with empty data, we'll populate it ourselves
        super().__init__(data=[], cache_dir=cache_dir, **kwargs)

        self._rng = random.Random(seed)
        self._strict = strict

        # Type checking and conversion into list of dicts to have a
        # consistent internal format. Since Seed Dataset should be
        # small, we can load it entirely into memory

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
        if isinstance(data, HFDataset):
            raw_data = self._init_from_hf_dataset(data)
        elif isinstance(data, Dataset):
            raw_data = self._init_from_pytorch_dataset(data)
        elif isinstance(data, Path):
            raw_data = self._init_from_json_path(data)
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
                    difficulty=item.get('difficulty'),
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
        r"""Get an item from the dataset.

        Args:
            idx (int): Index of the item to get.

        Returns:
            DataPoint: DataPoint from the dataset with the given index.

        Raises:
            IndexError: If idx is out of bounds.
        """
        if idx < 0 or idx >= self._length:
            raise IndexError(
                f"Index {idx} out of bounds for dataset of size {self._length}"
            )
        return self.data[idx]

    def sample(self) -> DataPoint:
        r"""Sample a random datapoint from the dataset.

        Returns:
            DataPoint: A randomly sampled DataPoint.

        Raises:
            RuntimeError: If the dataset is empty.
        """
        if self._length == 0:
            raise RuntimeError("Dataset is empty, cannot sample.")
        idx = self._rng.randint(0, self._length - 1)
        return self[idx]

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Get dataset metadata."""
        return self._metadata.copy()

    def _init_from_hf_dataset(self, data: HFDataset) -> List[Dict[str, Any]]:
        return [dict(item) for item in data]

    def _init_from_pytorch_dataset(
        self, data: Dataset
    ) -> List[Dict[str, Any]]:
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

    def _init_from_list(
        self, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Expected a dictionary at index {i}, "
                    f"got {type(item).__name__}"
                )
        return data


class SyntheticDataset(BaseDataset):
    r"""A dataset for storing synthetically generated data points.

    This class is used to store datapoints that are generated through
    a generative process, such as using an agent.
    """

    def __init__(
        self,
        data: Optional[List[Dict[str, str]]] = None,
        cache_dir: Optional[str] = None,
        **kwargs,
    ):
        r"""Initialize the synthetic dataset.

        Args:
            data (Optional[List[Dict[str, str]]]): List of dictionary items to
                create the dataset from. (default: :obj:`None`)
            cache_dir (Optional[str]): Directory to cache dataset files.
                (default: :obj:`None`)
            **kwargs: Additional dataset parameters.
        """
        super().__init__(
            data=data if data is not None else [],
            cache_dir=cache_dir,
            **kwargs,
        )
        self.data: List[DataPoint] = []

    def add(self, item: DataPoint) -> None:
        r"""Add a new data point to the dataset.

        Args:
            item (DataPoint): The datapoint to add to the dataset.
        """
        self.data.append(item)

    def add_batch(self, items: List[DataPoint]) -> None:
        r"""Add multiple data points to the dataset.

        Args:
            items (List[DataPoint]): The datapoints to add to the dataset.
        """
        self.data.extend(items)

    def to_pytorch_dataset(
        self,
        transform: Optional[Callable] = None,
        target_transform: Optional[Callable] = None,
        batch_size: Optional[int] = None,
    ) -> Union["PyTorchDataset", "DataLoader"]:
        r"""Convert to a PyTorch dataset or DataLoader.

        Args:
            transform (Optional[Callable]): Transform to apply to samples.
            target_transform (Optional[Callable]): Transform to apply to
                targets.
            batch_size (Optional[int]): If provided, returns a DataLoader with
                the specified batch size instead of a PyTorchDataset.
                (default: :obj:`None`)

        Returns:
            Union[PyTorchDataset, torch.utils.data.DataLoader]: Dataset in
                PyTorch format or DataLoader if batch_size is provided.
        """
        return convert_synthetic_to_pytorch(
            self,
            transform=transform,
            target_transform=target_transform,
            batch_size=batch_size,
        )

    def save_pytorch_format(self, path: str, compression: bool = True) -> None:
        r"""Save the dataset to disk in PyTorch format.

        Args:
            path (str): Path to save the dataset to.
            compression (bool): Whether to use compression to reduce file size.
                (default: :obj:`True`)
        """
        save_synthetic_dataset(self, path, compression=compression)

    def filter(
        self, predicate: Callable[[DataPoint], bool]
    ) -> 'SyntheticDataset':
        r"""Filter the dataset using a predicate function.

        Args:
            predicate (Callable[[DataPoint], bool]): Function that takes a
                DataPoint and returns True if it should be kept, False
                otherwise.

        Returns:
            SyntheticDataset: A new dataset containing only the filtered items.
        """
        filtered_data = [dp for dp in self.data if predicate(dp)]

        # Create a new dataset with the filtered data
        new_dataset = SyntheticDataset()
        new_dataset.add_batch(filtered_data)

        return new_dataset


class GenerativeDataset(BaseDataset):
    r"""A dataset for generating synthetic datapoints using external agents and
    verifiers.

    This class leverages a seed dataset and external components to generate
    new synthetic datapoints on demand.
    """

    def __init__(
        self,
        seed_dataset: SeedDataset,
        verifier: BaseVerifier,
        agent: ChatAgent,
        cache_dir: Optional[str] = None,
        seed: int = 42,
        **kwargs,
    ):
        r"""Initialize the generative dataset.

        Args:
            seed_dataset (SeedDataset): Validated dataset to use for examples.
            verifier (BaseVerifier): Verifier to validate generated content.
            agent (ChatAgent): Agent to generate new datapoints.
            cache_dir (Optional[str]): Directory to cache dataset files.
                (default: :obj:`None`)
            seed (int): Random seed for reproducibility. (default: :obj:`42`)
            **kwargs: Additional dataset parameters.
        """
        # Initialize with empty data since we'll generate content dynamically
        super().__init__(
            data=[],
            cache_dir=cache_dir,
            **kwargs,
        )

        self.seed_dataset = seed_dataset
        self.verifier = verifier
        self.agent = agent

        self.seed = seed
        random.seed(self.seed)

    def _construct_prompt(self, examples: List[DataPoint]) -> str:
        r"""Construct a prompt for generating new datapoints.

        Args:
            examples (List[DataPoint]): Examples to include in the prompt.

        Returns:
            str: Formatted prompt with examples.
        """
        prompt = (
            "Generate a new datapoint similar to the following examples:\n\n"
        )
        for i, example in enumerate(examples, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Question: {example.question}\n"
            prompt += f"Rationale: {example.rationale}\n"
            prompt += f"Final Answer: {example.final_answer}\n\n"
        prompt += "New datapoint:"
        return prompt

    async def generate_new(self, n: int) -> None:
        r"""Generate n new datapoints and add them to the dataset.

        Args:
            n (int): Number of valid datapoints to generate.

        This method generates new datapoints by:
        1. Sampling examples from the seed dataset
        2. Constructing a prompt for the agent
        3. Generating a new datapoint using the agent
        4. Verifying the generated datapoint with the verifier
        5. Adding valid datapoints to the dataset
        """
        valid_data_points: List[DataPoint] = []

        while len(valid_data_points) < n:
            try:
                indices = random.sample(range(len(self.seed_dataset)), 3)
                examples = [self.seed_dataset[i] for i in indices]
                prompt = self._construct_prompt(examples)

                # Get agent response
                agent_output = (
                    self.agent.step(prompt, response_format=DataPoint)
                    .msgs[0]
                    .parsed
                )

                if not isinstance(agent_output, dict):
                    raise TypeError("Agent output must be a dictionary")
                if (
                    'question' not in agent_output
                    or 'rationale' not in agent_output
                ):
                    raise KeyError(
                        "Agent output missing required keys: "
                        "'question' or 'rationale'"
                    )

                rationale = agent_output['rationale']

                # Verify the generated content
                verifier_response = await self.verifier.verify(rationale)
                if not hasattr(verifier_response, 'content'):
                    raise AttributeError(
                        "Verifier response missing 'content' attribute"
                    )

                if not verifier_response.result:
                    continue

                final_answer = verifier_response.result

                # Create and validate the new datapoint
                new_datapoint = {
                    'question': agent_output['question'],
                    'rationale': rationale,
                    'final_answer': final_answer,
                }

                datapoint = DataPoint(**new_datapoint)
                valid_data_points.append(datapoint)

            except (TypeError, KeyError, AttributeError, ValidationError) as e:
                logger.warning(
                    f"Error encountered during generation: {e}, retrying..."
                )

        # Add all valid datapoints to the dataset
        for datapoint in valid_data_points:
            self.data.append(datapoint)
            logger.debug("Added new datapoint to dataset")


# Define a type variable for return type flexibility
T_co = TypeVar('T_co', covariant=True)


class PyTorchDataset(Dataset[T_co]):
    r"""A PyTorch-compatible dataset implementation that leverages PyTorch's
    efficient data handling capabilities.
    """

    def __init__(
        self,
        data: List[Dict[str, Any]],
        transform: Optional[Callable] = None,
        target_transform: Optional[Callable] = None,
        validate: bool = True,
    ):
        r"""Initialize the PyTorch dataset.

        Args:
            data (List[Dict[str, Any]]): List of dictionary items to create
                the dataset from.
            transform (Optional[Callable]): A function/transform that takes a
                sample and returns a transformed version for features.
                (default: :obj:`None`)
            target_transform (Optional[Callable]): A function/transform that
                takes a target and returns a transformed version. (default:
                :obj:`None`)
            validate (bool): Whether to validate data points using DataPoint
                schema. (default: :obj:`True`)

        Raises:
            ValidationError: If validation is enabled and data doesn't match
                DataPoint schema.
        """
        self.transform = transform
        self.target_transform = target_transform

        # Validate and store data
        self._raw_data = data
        self.data = []

        if validate:
            for i, item in enumerate(self._raw_data):
                try:
                    # Use DataPoint for validation only
                    dp = DataPoint(**item)
                    self.data.append(dp.to_dict())
                except ValidationError as e:
                    logger.error(f"Sample {i} validation error: {e}")
                    raise ValueError(f"Sample {i} validation error: {e}")
        else:
            # Skip validation and just store the data dictionaries
            self.data = [dict(item) for item in self._raw_data]

    def __getitem__(self, index: int) -> T_co:
        r"""Get an item from the dataset.

        Args:
            index (int): Index of the item to get.

        Returns:
            T_co: Item from the dataset, possibly transformed.
        """
        sample = self.data[index]

        # Apply transformations if provided
        if self.transform is not None:
            sample = self.transform(sample)

        return sample  # type: ignore[return-value]

    def __len__(self) -> int:
        r"""Return the size of the dataset.

        Returns:
            int: Number of samples in the dataset.
        """
        return len(self.data)

    @classmethod
    def from_datapoints(
        cls, datapoints: List[DataPoint], **kwargs
    ) -> 'PyTorchDataset':
        r"""Create a PyTorchDataset from a list of DataPoints.

        Args:
            datapoints (List[DataPoint]): List of DataPoint objects.
            **kwargs: Additional arguments to pass to the constructor.

        Returns:
            PyTorchDataset: A new PyTorchDataset instance.
        """
        data = [dp.to_dict() for dp in datapoints]
        # We can skip validation since datapoints are already validated
        return cls(data, validate=False, **kwargs)

    def to_hf_dataset(self) -> HFDataset:
        r"""Convert to a HuggingFace dataset.

        Returns:
            HFDataset: Dataset in HuggingFace format.
        """
        return HFDataset.from_list(self.data)

    def save_to_disk(self, path: str) -> None:
        r"""Save the dataset to disk using PyTorch.

        Args:
            path (str): Path to save the dataset to.
        """
        torch.save(self.data, path)

    @classmethod
    def load_from_disk(
        cls,
        path: str,
        transform: Optional[Callable] = None,
        target_transform: Optional[Callable] = None,
    ) -> 'PyTorchDataset':
        r"""Load a dataset from disk.

        Args:
            path (str): Path to load the dataset from.
            transform (Optional[Callable]): Transform to apply to samples.
                (default: :obj:`None`)
            target_transform (Optional[Callable]): Transform to apply to
                targets. (default: :obj:`None`)

        Returns:
            PyTorchDataset: Loaded dataset.
        """
        data = torch.load(path)
        return cls(
            data,
            transform=transform,
            target_transform=target_transform,
            validate=False,
        )

    @staticmethod
    def collate_fn(
        batch: List[Dict[str, Any]],
    ) -> Dict[str, Union[List[Any], torch.Tensor]]:
        r"""Collate function for PyTorch DataLoader.

        Args:
            batch (List[Dict[str, Any]]): Batch of samples from the dataset.

        Returns:
            Dict[str, Union[List[Any], torch.Tensor]]: Collated batch with
                tensors for numerical data.
        """
        if not batch:
            return {}

        # Initialize result dictionary with keys from first item - start with
        # lists only
        result: Dict[str, List[Any]] = {k: [] for k in batch[0].keys()}

        # Collect values by key
        for item in batch:
            for k, v in item.items():
                result[k].append(v)

        # Convert numeric/boolean lists to tensors where possible
        result_with_tensors: Dict[str, Union[List[Any], torch.Tensor]] = {}
        for k, v in result.items():
            if all(isinstance(x, (int, float, bool)) for x in v):
                try:
                    result_with_tensors[k] = torch.tensor(v)
                except (ValueError, TypeError):
                    # Keep as list if tensor conversion fails
                    result_with_tensors[k] = v
            else:
                result_with_tensors[k] = v

        return result_with_tensors

    def get_dataloader(
        self,
        batch_size: int = 32,
        shuffle: bool = True,
        num_workers: int = 0,
        pin_memory: bool = False,
        **kwargs,
    ) -> "DataLoader":
        r"""Create a PyTorch DataLoader for this dataset.

        Args:
            batch_size (int): Batch size. (default: :obj:`32`)
            shuffle (bool): Whether to shuffle the dataset. (default:
                :obj:`True`)
            num_workers (int): Number of workers for data loading. (default:
            :obj:`0`)
            pin_memory (bool): Whether to pin memory for faster GPU transfer.
                (default: :obj:`False`)
            **kwargs: Additional arguments to pass to DataLoader.

        Returns:
            torch.utils.data.DataLoader: DataLoader for this dataset.
        """
        from torch.utils.data import DataLoader

        return DataLoader(
            self,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            collate_fn=self.collate_fn,
            pin_memory=pin_memory,
            **kwargs,
        )


def convert_hf_to_pytorch(
    hf_dataset: HFDataset,
    transform: Optional[Callable] = None,
    target_transform: Optional[Callable] = None,
    column_mapping: Optional[Dict[str, str]] = None,
    validate: bool = True,
    batch_size: Optional[int] = None,
) -> Union["PyTorchDataset", "DataLoader"]:
    r"""Convert a HuggingFace dataset to a PyTorchDataset or DataLoader.

    This function maps HuggingFace dataset columns to the expected DataPoint
    format, validates the data, and creates a PyTorchDataset or DataLoader.

    Args:
        hf_dataset (HFDataset): HuggingFace dataset to convert.
        transform (Optional[Callable]): Transform to apply to samples.
        target_transform (Optional[Callable]): Transform to apply to targets.
        column_mapping (Optional[Dict[str, str]]): Mapping from HuggingFace
            column names to DataPoint field names. If None, assumes columns
            already match DataPoint fields.
        validate (bool): Whether to validate data points using DataPoint
            schema. (default: :obj:`True`)
        batch_size (Optional[int]): If provided, returns a DataLoader with the
            specified batch size instead of a PyTorchDataset. (default:
            :obj:`None`)

    Returns:
        Union[PyTorchDataset, torch.utils.data.DataLoader]: Converted dataset
            or DataLoader if batch_size is provided.
    """
    # Convert HuggingFace dataset to list of dicts more efficiently
    mapped_dataset = []

    for i in range(len(hf_dataset)):
        item = hf_dataset[i]
        if column_mapping is not None:
            # Apply column mapping if provided
            mapped_item = {}
            for hf_col, dp_field in column_mapping.items():
                if hf_col in item:
                    mapped_item[dp_field] = item[hf_col]
            mapped_dataset.append(mapped_item)
        else:
            # Otherwise use item directly
            mapped_dataset.append(dict(item))

    # Create PyTorchDataset
    dataset: PyTorchDataset = PyTorchDataset(
        mapped_dataset,
        transform=transform,
        target_transform=target_transform,
        validate=validate,
    )

    # Return DataLoader if batch_size is provided
    if batch_size is not None:
        return dataset.get_dataloader(batch_size=batch_size)

    return dataset


def convert_synthetic_to_pytorch(
    synthetic_dataset: 'SyntheticDataset',
    transform: Optional[Callable] = None,
    target_transform: Optional[Callable] = None,
    batch_size: Optional[int] = None,
) -> Union["PyTorchDataset", "DataLoader"]:
    r"""Convert a SyntheticDataset to a PyTorchDataset or DataLoader.

    Args:
        synthetic_dataset (SyntheticDataset): Synthetic dataset to convert.
        transform (Optional[Callable]): Transform to apply to samples.
        target_transform (Optional[Callable]): Transform to apply to targets.
        batch_size (Optional[int]): If provided, returns a DataLoader with the
            specified batch size instead of a PyTorchDataset. (default:
            :obj:`None`)

    Returns:
        Union[PyTorchDataset, torch.utils.data.DataLoader]: Converted dataset
            or DataLoader if batch_size is provided.
    """
    dataset = PyTorchDataset.from_datapoints(
        synthetic_dataset.data,
        transform=transform,
        target_transform=target_transform,
    )

    # Return DataLoader if batch_size is provided
    if batch_size is not None:
        return dataset.get_dataloader(batch_size=batch_size)

    return dataset


def save_synthetic_dataset(
    synthetic_dataset: 'SyntheticDataset',
    path: str,
    compression: bool = True,
) -> None:
    r"""Save a synthetic dataset to disk using PyTorch format.

    Args:
        synthetic_dataset (SyntheticDataset): Dataset to save.
        path (str): Path to save the dataset to.
        compression (bool): Whether to use compression to reduce file size.
            (default: :obj:`True`)
    """
    pytorch_dataset = convert_synthetic_to_pytorch(synthetic_dataset)

    # Save with compression if enabled (uses less disk space)
    if compression:
        torch.save(
            pytorch_dataset.data,  # type: ignore[union-attr]
            path,
            _use_new_zipfile_serialization=True,
        )
    else:
        pytorch_dataset.save_to_disk(path)  # type: ignore[union-attr]


def load_pytorch_dataset(
    path: str,
    transform: Optional[Callable] = None,
    target_transform: Optional[Callable] = None,
    batch_size: Optional[int] = None,
) -> Union["PyTorchDataset", "DataLoader"]:
    r"""Load a PyTorchDataset from disk.

    Args:
        path (str): Path to load the dataset from.
        transform (Optional[Callable]): Transform to apply to samples.
        target_transform (Optional[Callable]): Transform to apply to targets.
        batch_size (Optional[int]): If provided, returns a DataLoader with the
            specified batch size instead of a PyTorchDataset. (default:
            :obj:`None`)

    Returns:
        Union[PyTorchDataset, torch.utils.data.DataLoader]: Loaded dataset or
            DataLoader if batch_size is provided.
    """
    dataset = PyTorchDataset.load_from_disk(
        path, transform=transform, target_transform=target_transform
    )

    # Return DataLoader if batch_size is provided
    if batch_size is not None:
        return dataset.get_dataloader(batch_size=batch_size)

    return dataset
