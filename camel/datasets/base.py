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
from datetime import datetime
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
from pydantic import BaseModel, Field, ValidationError
from torch.utils.data import Dataset

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.verifiers import BaseVerifier
from camel.verifiers.models import VerifierInput

logger = get_logger(__name__)


class DataPoint(BaseModel):
    r"""A single data point in the dataset.

    Attributes:
        question (str): The primary question or issue to be addressed.
        rationale (Optional[str]): Logical reasoning or explanation behind the
            answer. (default: :obj:`None`)
        final_answer (str): The final answer.
        metadata Optional[Dict[str, Any]]: Additional metadata about the data
            point. (default: :obj:`None`)
    """

    question: str = Field(
        ..., description="The primary question or issue to be addressed."
    )
    rationale: Optional[str] = Field(
        default=None,
        description="Logical reasoning or explanation behind the answer.",
    )
    final_answer: str = Field(..., description="The final answer.")

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
            data (:obj:`Union[HFDataset, Dataset,
            Path, List[Dict[str, Any]]]`):
                Input data, which can be one of the following:
                - A Hugging Face Dataset (:obj:`HFDataset`).
                - A PyTorch Dataset (:obj:`torch.utils.data.Dataset`).
                - A :obj:`Path` object representing a JSON file.
                - A list of dictionaries with :obj:`DataPoint`-compatible
                  fields.
            seed (:obj:`int`): Random seed for reproducibility.
                Default is :obj:`42`.
            min_samples (:obj:`int`): Minimum required number of samples.
                Default is :obj:`1`.
            strict (:obj:`bool`): Whether to raise an error on invalid
                datapoints (:obj:`True`) or skip/filter them (:obj:`False`).
                Default is :obj:`False`.
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
            data (:obj:`Union[
                HFDataset,
                Dataset,
                Path,
                List[Dict[str, Any]]
            ]`):
                Input dataset in one of the supported formats.

        Returns:
            :obj:`List[DataPoint]`: A list of validated :obj:`DataPoint`
                instances.

        Raises:
            TypeError: If the input data type is unsupported.
        """

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
            idx (:obj:`int`): Index of the datapoint.

        Returns:
            :obj:`DataPoint`: The datapoint corresponding to the given index.

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
            :obj:`DataPoint`: A randomly sampled :obj:`DataPoint`.

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
            :obj:`Dict[str, Any]`: A copy of the dataset metadata dictionary.
        """

        return self._metadata.copy()

    def _init_from_hf_dataset(self, data: HFDataset) -> List[Dict[str, Any]]:
        r"""Convert a Hugging Face dataset into a list of dictionaries.

        Args:
            data (:obj:`HFDataset`): A Hugging Face dataset.

        Returns:
            :obj:`List[Dict[str, Any]]`: A list of dictionaries representing
            the dataset, where each dictionary corresponds to a datapoint.
        """
        return [dict(item) for item in data]

    def _init_from_pytorch_dataset(
        self, data: Dataset
    ) -> List[Dict[str, Any]]:
        r"""Convert a PyTorch dataset into a list of dictionaries.

        Args:
            data (:obj:`Dataset`): A PyTorch dataset.

        Returns:
            :obj:`List[Dict[str, Any]]`: A list of dictionaries representing
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
            data (:obj:`Path`): Path to the JSON file.

        Returns:
            :obj:`List[Dict[str, Any]]`: A list of datapoint dictionaries.

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

    def _init_from_list(
        self, data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        r"""Validate and convert a list of dictionaries into a dataset.

        Args:
            data (:obj:`List[Dict[str, Any]]`): A list of dictionaries where
                each dictionary must be a valid :obj:`DataPoint`.

        Returns:
            :obj:`List[Dict[str, Any]]`: The validated list of dictionaries.

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


class GenerativeDataset(Dataset):
    r"""A dataset for generating synthetic datapoints using external agents and
    verifiers.

    This class leverages a seed dataset and external components to generate
    new synthetic datapoints on demand.
    """

    def __init__(
        self,
        seed_dataset: StaticDataset,
        verifier: BaseVerifier,
        agent: ChatAgent,
        seed: int = 42,
        **kwargs,
    ):
        r"""Initialize the generative dataset.

        Args:
            seed_dataset (StaticDataset): Validated static dataset to
            use for examples.
            verifier (BaseVerifier): Verifier to validate generated content.
            agent (ChatAgent): Agent to generate new datapoints.
            seed (int): Random seed for reproducibility. (default: :obj:`42`)
            **kwargs: Additional dataset parameters.
        """

        self.seed_dataset = seed_dataset
        self.verifier = verifier
        self.agent = agent

        self.seed = seed
        random.seed(self.seed)

        self._data: List[DataPoint] = []

    def _construct_prompt(self, examples: List[DataPoint]) -> str:
        r"""Construct a prompt for generating new datapoints
        using a fixed sample of 3 examples from the seed dataset.

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

    async def generate_new(
        self, n: int, max_retries: int = 10
    ) -> List[DataPoint]:
        r"""Generates and validates `n` new datapoints through
        few-shot prompting, with a retry limit.

        Steps:
            1. Samples 3 examples from the seed dataset.
            2. Constructs a prompt using the selected examples.
            3. Uses an agent to generate a new datapoint.
            4. Verifies the datapoint using a verifier.
            5. Stores valid datapoints in memory.

        Args:
            n (int): Number of valid datapoints to generate.
            max_retries (int): Maximum number of retries before stopping.

        Returns:
            List[DataPoint]: A list of newly generated valid datapoints.

        Raises:
            TypeError: If the agent's output is not a dictionary (or does not
            match the expected format).
            KeyError: If required keys are missing from the response.
            AttributeError: If the verifier response lacks attributes.
            ValidationError: If a datapoint fails schema validation.
            RuntimeError: If retries are exhausted before `n` valid datapoints
            are generated.

        Notes:
            - Retries on validation failures until `n` valid datapoints exist
            or `max_retries` is reached, whichever comes first.
            - If retries are exhausted before reaching `n`, a `RuntimeError`
            is raised.
            - Metadata includes a timestamp for tracking datapoint creation.
            - This method can be overridden to implement custom generation.
        """
        valid_data_points: List[DataPoint] = []
        retries = 0

        while len(valid_data_points) < n and retries < max_retries:
            try:
                examples = [self.seed_dataset.sample() for _ in range(3)]
                prompt = self._construct_prompt(examples)

                try:
                    agent_output = (
                        self.agent.step(prompt, response_format=DataPoint)
                        .msgs[0]
                        .parsed
                    )
                    if not isinstance(agent_output, dict):
                        raise TypeError("Agent output must be a dictionary")
                    if (
                        "question" not in agent_output
                        or "rationale" not in agent_output
                    ):
                        raise KeyError(
                            "Missing 'question' or 'rationale' in agent output"
                        )
                except (TypeError, KeyError) as e:
                    logger.warning(
                        f"Agent output issue: {e}, retrying... "
                        f"({retries + 1}/{max_retries})"
                    )
                    retries += 1
                    continue

                rationale = agent_output["rationale"]

                try:
                    verifier_response = await self.verifier.verify(
                        VerifierInput(
                            llm_response=rationale, ground_truth=None
                        )
                    )
                    if not verifier_response or not verifier_response.result:
                        raise ValueError(
                            "Verifier unsuccessful, response: "
                            f"{verifier_response}"
                        )
                except (ValueError, AttributeError) as e:
                    logger.warning(
                        f"Verifier issue: {e}, "
                        f"retrying... ({retries + 1}/{max_retries})"
                    )
                    retries += 1
                    continue

                try:
                    new_datapoint = DataPoint(
                        question=agent_output["question"],
                        rationale=rationale,
                        final_answer=verifier_response.result,
                        metadata={
                            "synthetic": str(True),
                            "created": datetime.now().isoformat(),
                        },
                    )
                except ValidationError as e:
                    logger.warning(
                        f"Datapoint validation failed: {e}, "
                        f"retrying... ({retries + 1}/{max_retries})"
                    )
                    retries += 1
                    continue

                valid_data_points.append(new_datapoint)

            except Exception as e:
                logger.warning(
                    f"Unexpected error: {e}, retrying..."
                    f" ({retries + 1}/{max_retries})"
                )
                retries += 1

        if len(valid_data_points) < n:
            raise RuntimeError(
                f"Failed to generate {n} valid datapoints "
                f"after {max_retries} retries."
            )

        self._data.extend(valid_data_points)
        return valid_data_points

    def __len__(self) -> int:
        r"""Return the size of the dataset."""
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

    def save_to_jsonl(self, file_path: Union[str, Path]) -> None:
        r"""Saves the dataset to a JSONL (JSON Lines) file.

        Each datapoint is stored as a separate JSON object on a new line.

        Args:
            file_path (Union[str, Path]): Path to save the JSONL file.

        Raises:
            ValueError: If the dataset is empty.
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
