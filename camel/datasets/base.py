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

import os
import random
from typing import Any, Dict, Iterator, List, Optional

from pydantic import BaseModel, Field, ValidationError
from torch.utils.data import Dataset

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
        verified (bool): Whether this chain-of-thought is verified.
            (default: :obj:`False`)
        ground_truth (Optional[str]): The ground truth solution.
            (default: :obj:`None`)
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
        None, description="Logical reasoning or explanation behind the answer."
    )
    final_answer: str = Field(..., description="The final answer.")
    verified: bool = Field(
        False, description="Whether this chain-of-thought is verified."
    )
    ground_truth: Optional[str] = Field(
        None, description="The ground truth solution."
    )
    raw_markdown: Optional[str] = Field(
        None, description="Raw markdown content for generating rewards/hints."
    )
    difficulty: Optional[str] = Field(
        None, description="Difficulty level of the question."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata about the data point."
    )


class BaseDataset(Dataset):
    r"""A dataset contains questions and ground truth data for training.
    It can be either static (e.g., MATH dataset) or generative
    (using an LLM to generate questions).
    """

    def __init__(
        self,
        data: List[Dict[str, str]],
        cache_dir: Optional[str] = None,
        max_cache_size: int = int(1e9),  # 1GB default
        preload: bool = False,
        shuffle: bool = True,
        **kwargs,
    ):
        r"""Initialize the dataset.

        Args:
            data (List[Dict[str, str]]): List of dictionary items to
                create the dataset from.
            cache_dir (Optional[str]): Directory to cache dataset files.
                (default: :obj:`None`)
            max_cache_size (int): Maximum cache size in bytes.
                (default: :obj:`1e9` (1GB))
            preload (bool): Whether to preload dataset into memory.
                (default: :obj:`False`)
            shuffle (bool): Whether to shuffle dataset on load.
                (default: :obj:`True`)
            **kwargs: Additional dataset parameters.

        Raises:
            ValueError: If max_cache_size is negative.

        Note:
            The dataset must be initialized by calling setup() before use.
        """
        self._current_index = 0
        self._is_setup = False
        self._cache: Dict[int, DataPoint] = {}
        self._raw_data: List[Dict[str, str]] = data if data is not None else []

        # Store configuration parameters
        self._cache_dir = str(cache_dir) if cache_dir is not None else None
        self._max_cache_size = int(max_cache_size)
        self._preload = bool(preload)
        self._shuffle = bool(shuffle)

        # Store all parameters in metadata dict for compatibility
        self._metadata = {
            'cache_dir': self._cache_dir,
            'max_cache_size': self._max_cache_size,
            'preload': self._preload,
            'shuffle': self._shuffle,
            **kwargs,
        }

        if self._max_cache_size < 0:
            raise ValueError("max_cache_size must be positive")

        self.data: List[DataPoint] = []  # Will be populated in setup()

    async def setup(self) -> None:
        r"""Set up the dataset with necessary resources.

        This method:
        1. Creates cache directory if needed
        2. Processes raw data into DataPoint objects
        3. Preloads data if configured
        4. Initializes shuffling if enabled
        5. Validates dataset integrity

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

            # Process raw data into DataPoint objects
            self.data = []  # Clear any existing data
            data_points: List[
                DataPoint
            ] = []  # Explicitly annotated temporary list
            for i, item in enumerate(self._raw_data):
                try:
                    # Convert dictionary to DataPoint with all required fields
                    dp = DataPoint(
                        question=item.get('question', ''),
                        rationale=item.get('rationale', ''),
                        final_answer=item.get('final_answer', ''),
                        verified=bool(item.get('verified', False)),
                        metadata=item.get('metadata', {})  # type: ignore[arg-type]
                        if isinstance(item.get('metadata'), dict)
                        else {},
                        ground_truth='',
                        raw_markdown='',
                        difficulty='',
                    )
                    data_points.append(dp)
                except ValidationError as e:
                    logger.error(f"Sample {i} validation error: {e}")
                    raise ValueError(f"Sample {i} validation error: {e}")

            # Update self.data after all points are successfully processed
            self.data = data_points
            logger.debug(f"Processed {len(self.data)} data points")

            # Preload dataset if configured
            if self._preload:
                logger.info(f"Preloading {len(self)} items into cache")
                try:
                    for i in range(len(self)):
                        self._cache[i] = await self._get_item_async(i)
                except Exception as e:
                    logger.error(f"Failed to preload dataset: {e}")
                    raise

            # Initialize shuffle indices if needed
            if self._shuffle:
                self._shuffle_indices = list(range(len(self)))
                random.shuffle(self._shuffle_indices)
                logger.debug("Initialized shuffle indices")

            self._is_setup = True
            logger.info(f"{self.__class__.__name__} initialized successfully")

        except Exception as e:
            logger.error(f"Error during {self.__class__.__name__} setup: {e}")
            await self.cleanup()
            raise

    async def cleanup(self) -> None:
        r"""Clean up dataset resources.

        This method handles cleanup of resources and resets the dataset state.
        It ensures:
        1. All resources are properly released
        2. State is reset to initial
        3. Cache is cleared
        4. Cleanup happens even if errors occur
        """
        if not self._is_setup:
            return

        try:
            # Reset dataset state
            self._current_index = 0

            # Clear cache
            self._cache.clear()
            if hasattr(self, '_shuffle_indices'):
                del self._shuffle_indices

            # Clear metadata while preserving init config
            init_config = {
                'cache_dir': self._cache_dir,
                'max_cache_size': self._max_cache_size,
                'preload': self._preload,
                'shuffle': self._shuffle,
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

    async def _get_item_async(self, idx: int) -> DataPoint:
        r"""Async wrapper around __getitem__ for preloading.

        Args:
            idx (int): Index of the item to get.

        Returns:
            DataPoint: DataPoint from the dataset.
        """
        return self[idx]

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

        if self._shuffle:
            idx = self._shuffle_indices[self._current_index]
        else:
            idx = self._current_index

        self._current_index = (self._current_index + 1) % len(self)
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

        if idx in self._cache:
            return self._cache[idx]

        return self.data[idx]

    def __iter__(self) -> Iterator[DataPoint]:
        r"""Create an iterator over the dataset."""
        return self

    def __next__(self) -> DataPoint:
        r"""Get the next item from the dataset."""
        if self._current_index >= len(self):
            self._current_index = 0
            raise StopIteration
        self._current_index += 1
        item = self[self._current_index]
        return item

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Get dataset metadata."""
        return self._metadata.copy()

    def reset(self) -> None:
        r"""Reset the dataset iterator and re-shuffle if enabled."""
        self._current_index = 0
        if self._shuffle and self._is_setup:
            random.shuffle(self._shuffle_indices)


class SeedDataset(BaseDataset):
    r"""A dataset containing validated seed examples for data generation.
    Ensures that all items adhere to the DataPoint schema.

    This class is used to initialize a dataset from a list of dictionary items,
    validating each against the DataPoint schema.
    """

    def __init__(
        self,
        data: List[Dict[str, str]],
        cache_dir: Optional[str] = None,
        max_cache_size: int = int(1e9),
        preload: bool = False,
        shuffle: bool = True,
        min_samples: int = 1,
        **kwargs,
    ):
        r"""Initialize the seed dataset.

        Args:
            data (List[Dict[str, str]]): List of dictionary items to create the
                dataset from.
            cache_dir (Optional[str]): Directory to cache dataset files.
                (default: :obj:`None`)
            max_cache_size (int): Maximum cache size in bytes.
                (default: :obj:`1e9` (1GB))
            preload (bool): Whether to preload dataset into memory.
                (default: :obj:`False`)
            shuffle (bool): Whether to shuffle dataset on load.
                (default: :obj:`True`)
            min_samples (int): Minimum number of samples required.
                (default: :obj:`1`)
            **kwargs: Additional dataset parameters.

        Raises:
            ValueError: If dataset size is less than min_samples or if sample
                validation fails.
        """
        if len(data) < min_samples:
            raise ValueError(
                f"Seed dataset must contain at least {min_samples} samples."
            )

        super().__init__(
            data=data,
            cache_dir=cache_dir,
            max_cache_size=max_cache_size,
            preload=preload,
            shuffle=shuffle,
            **kwargs,
        )


class SyntheticDataset(BaseDataset):
    r"""A dataset for storing synthetically generated data points.

    This class is used to store datapoints that are generated through
    a generative process, such as using an agent.
    """

    def __init__(
        self,
        data: Optional[List[Dict[str, str]]] = None,
        cache_dir: Optional[str] = None,
        max_cache_size: int = int(1e9),
        preload: bool = False,
        shuffle: bool = True,
        **kwargs,
    ):
        r"""Initialize the synthetic dataset.

        Args:
            data (Optional[List[Dict[str, str]]]): List of dictionary items to
                create the dataset from. (default: :obj:`None`)
            cache_dir (Optional[str]): Directory to cache dataset files.
                (default: :obj:`None`)
            max_cache_size (int): Maximum cache size in bytes.
                (default: :obj:`1e9` (1GB))
            preload (bool): Whether to preload dataset into memory.
                (default: :obj:`False`)
            shuffle (bool): Whether to shuffle dataset on load.
                (default: :obj:`True`)
            **kwargs: Additional dataset parameters.
        """
        super().__init__(
            data=data if data is not None else [],
            cache_dir=cache_dir,
            max_cache_size=max_cache_size,
            preload=preload,
            shuffle=shuffle,
            **kwargs,
        )
        self.data: List[DataPoint] = []

    def add(self, item: DataPoint) -> None:
        r"""Add a new data point to the dataset.

        Args:
            item (DataPoint): The datapoint to add to the dataset.
        """
        self.data.append(item)


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
        max_cache_size: int = int(1e9),
        preload: bool = False,
        shuffle: bool = True,
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
            max_cache_size (int): Maximum cache size in bytes.
                (default: :obj:`1e9` (1GB))
            preload (bool): Whether to preload dataset into memory.
                (default: :obj:`False`)
            shuffle (bool): Whether to shuffle dataset on load.
                (default: :obj:`True`)
            seed (int): Random seed for reproducibility. (default: :obj:`42`)
            **kwargs: Additional dataset parameters.
        """
        # Initialize with empty data since we'll generate content dynamically
        super().__init__(
            data=[],
            cache_dir=cache_dir,
            max_cache_size=max_cache_size,
            preload=preload,
            shuffle=shuffle,
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

                final_answer = verifier_response.sub_results[0]

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
