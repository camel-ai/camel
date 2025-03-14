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
from datetime import datetime
from pathlib import Path
from typing import (
    List,
    Union,
)

from pydantic import ValidationError

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.verifiers import BaseVerifier
from camel.verifiers.models import VerifierInput

from .models import DataPoint
from .static_dataset import StaticDataset

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
        self.seed = seed
        random.seed(self.seed)

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

class FewShotGenerator(BaseGenerator):
    r"""A generator for creating synthetic datapoints using few-shot learning.

    This class leverages a seed dataset, an agent, and a verifier to generate
    new synthetic datapoints on demand through few-shot prompting.
    """

    def __init__(
        self,
        seed_dataset: StaticDataset,
        verifier: BaseVerifier,
        agent: ChatAgent,
        seed: int = 42,
        **kwargs,
    ):
        r"""Initialize the few-shot generator.

        Args:
            seed_dataset (StaticDataset): Validated static dataset to
                use for examples.
            verifier (BaseVerifier): Verifier to validate generated content.
            agent (ChatAgent): Agent to generate new datapoints.
            seed (int): Random seed for reproducibility. (default: :obj:`42`)
            **kwargs: Additional generator parameters.
        """
        super().__init__(seed=seed, **kwargs)
        self.seed_dataset = seed_dataset
        try:
            self._validate_seed_dataset()
        except:
            raise RuntimeError("Seed Data does not follow Datapoint format")
        self.verifier = verifier
        self.agent = agent

    # TODO: Validate that seed dataset contains rationale
    def _validate_seed_dataset(self) -> None:
        pass
            

    def _construct_prompt(self, examples: List[DataPoint]) -> str:
        r"""Construct a prompt for generating new datapoints
        using a fixed sample of examples from the seed dataset.

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
            if example.rationale is not None:
                prompt += f"Rationale: {example.rationale}\n"
            else:
                prompt += "Rationale: None\n"
            prompt += f"Final Answer: {example.final_answer}\n\n"
        prompt += "New datapoint:"
        return prompt

    async def generate_new(
        self,
        n: int,
        max_retries: int = 10,
        num_examples: int = 3,
        **kwargs,
    ) -> List[DataPoint]:
        r"""Generates and validates `n` new datapoints through
        few-shot prompting, with a retry limit.

        Steps:
            1. Samples examples from the seed dataset.
            2. Constructs a prompt using the selected examples.
            3. Uses an agent to generate a new datapoint.
            4. Verifies the datapoint using a verifier.
            5. Stores valid datapoints in memory.

        Args:
            n (int): Number of valid datapoints to generate.
            max_retries (int): Maximum number of retries before stopping.
                (default: :obj:`10`)
            num_examples (int): Number of examples to sample from the
            seed dataset for few shot prompting.
                (default: :obj:`3`)
            **kwargs: Additional generation parameters.

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
        """
        valid_data_points: List[DataPoint] = []
        retries = 0

        while len(valid_data_points) < n and retries < max_retries:
            try:
                examples = [
                    self.seed_dataset.sample() for _ in range(num_examples)
                ]
                prompt = self._construct_prompt(examples)

                try:
                    agent_output = (
                        self.agent.step(prompt, response_format=DataPoint)
                        .msgs[0]
                        .parsed
                    )
                    if not isinstance(agent_output, dict):
                        raise TypeError("Agent output must be a dictionary")
                    if "question" not in agent_output:
                        raise KeyError(f"Missing 'question' in agent output {agent_output}")
                    if "rationale" not in agent_output:
                        raise KeyError(f"Missing 'rationale' in agent output {agent_output}")
                except (TypeError, KeyError) as e:
                    logger.warning(
                        f"Agent output issue: {e}, retrying... "
                        f"({retries + 1}/{max_retries})"
                    )
                    retries += 1
                    continue

                rationale = agent_output.get("rationale")

                try:
                    verifier_response = await self.verifier.verify(
                        VerifierInput(
                            llm_response=rationale,
                            ground_truth=None,
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
                            "verify_mode": verify_mode,
                            "generator": "few_shot",
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
