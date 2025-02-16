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
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field

from camel.datasets.base import BaseDataset, DataPoint
from camel.extractors.base import BaseExtractor, ExtractionResult
from camel.verifiers.base import BaseVerifier, VerificationResult
from camel.verifiers.models import Response, TaskType


class Observation(BaseModel):
    r"""Environment observation.

    Attributes:
        question: The question posed to the LLM.
        context: Additional context for the question.
        metadata: Optional metadata about the observation.
    """

    question: str = Field(..., description="The question posed to the LLM")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context for the question"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata about the observation"
    )


class StepResult(BaseModel):
    r"""Result of an environment step.

    Attributes:
        observation: The next observation.
        reward: Dictionary of reward scores for different aspects.
        done: Whether the episode is complete.
        info: Additional information about the step.
    """

    observation: Observation = Field(..., description="The next observation")
    reward: Dict[str, float] = Field(
        default_factory=dict,
        description="Dictionary of reward scores for different aspects",
    )
    done: bool = Field(..., description="Whether the episode is complete")
    info: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional information about the step",
    )


class BaseEnvironment(ABC):
    r"""Base class for all RLVR training environments.

    An environment ties everything together. It:
    1. Holds state
    2. Defines a reward function
    3. Manages a dataset
    4. Provides reset and step functions
    5. Handles verifier setup and teardown
    """

    def __init__(
        self,
        dataset: BaseDataset,
        verifier: BaseVerifier,
        extractor: BaseExtractor,
        max_steps: Optional[int] = None,
        task_type: TaskType = TaskType.SOFTWARE_ENGINEERING,
        **kwargs,
    ):
        r"""Initialize the environment.

        Args:
            dataset: Dataset to sample questions from.
            verifier: Verifier to check responses.
            extractor: Extractor to process LLM responses.
            max_steps: Maximum steps per episode.
            task_type: Type of task being performed.
            **kwargs: Additional environment parameters.
        """
        self.dataset = dataset
        self.verifier = verifier
        self.extractor = extractor
        self.max_steps = max_steps
        self.task_type = task_type
        self._current_step = 0
        self._current_datapoint: Optional[DataPoint] = None
        self._metadata = kwargs

    @abstractmethod
    async def setup(self) -> None:
        r"""Set up the environment, including verifier initialization."""
        pass

    @abstractmethod
    async def teardown(self) -> None:
        r"""Clean up resources, including verifier teardown."""
        pass

    @abstractmethod
    async def reset(self) -> None:
        r"""Reset the environment to initial state."""
        self._current_step = 0
        self._current_datapoint = None

    async def process_response(
        self, response: Response, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ExtractionResult, VerificationResult]:
        r"""Process an response through extraction and verification.

        Args:
            response: Response containing the output.
            context: Optional context for extraction.

        Returns:
            Tuple of (extraction_result, verification_result).
        """
        # Extract relevant content from response
        extraction_result = await self.extractor.extract(
            response.llm_response, context=context
        )

        # Verify using Response object
        verification_result = await self.verifier.verify(response)

        return extraction_result, verification_result

    @abstractmethod
    async def step(self, response: Response) -> StepResult:
        r"""Take a step in the environment.

        Args:
            response: Response containing output

        Returns:
            StepResult containing next observation, reward, done flag, and info
        """
        if self.max_steps and self._current_step >= self.max_steps:
            return StepResult(
                observation=self._get_terminal_observation(),
                reward={},
                done=True,
                info={"reason": "max_steps_reached"},
            )

        # Process the response
        extraction_result, verification_result = await self.process_response(
            response
        )

        # Compute reward
        reward = await self.compute_reward(response, verification_result)

        self._current_step += 1
        return StepResult(
            observation=self._get_next_observation(),
            reward=reward,
            done=False,
            info={
                "extraction": extraction_result,
                "verification": verification_result,
            },
        )

    @abstractmethod
    def _get_next_observation(self) -> Observation:
        r"""Get the next observation for the environment.

        Returns:
            Observation for the next step
        """
        pass

    @abstractmethod
    def _get_terminal_observation(self) -> Observation:
        r"""Get the terminal observation when episode ends.

        Returns:
            Terminal observation
        """
        pass

    @abstractmethod
    async def compute_reward(
        self, response: Response, verification_result: VerificationResult
    ) -> Dict[str, float]:
        r"""Compute reward scores for different aspects of the response.

        Args:
            response: The response.
            verification_result: Result from the verifier.

        Returns:
            Dictionary of reward scores for different aspects.
        """
        pass

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Get environment metadata."""
        return self._metadata.copy()

    @property
    def current_step(self) -> int:
        r"""Get current step number."""
        return self._current_step
