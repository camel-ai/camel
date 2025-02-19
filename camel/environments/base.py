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
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.datasets.base import BaseDataset
from camel.extractors.base import BaseExtractor
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
        teacher_agent: Optional[ChatAgent] = None,
        generator_agent: Optional[ChatAgent] = None,
        **kwargs,
    ) -> None:
        r"""Initialize the environment.

        Args:
            dataset: Dataset to sample questions from.
            verifier: Verifier to check responses.
            extractor: Extractor to process LLM responses.
            max_steps: Maximum steps per episode.
            task_type: Type of task being performed.
            teacher_agent: Optional agent for reward shaping
            generator_agent: Optional agent for data generation
            **kwargs: Additional environment parameters.
        """
        self.dataset = dataset
        self.verifier = verifier
        self.extractor = extractor
        self.max_steps = max_steps
        self.task_type = task_type
        self.teacher_agent = teacher_agent
        self.generator_agent = generator_agent
        self._metadata = kwargs

        # State tracking
        self._is_setup: bool = False
        self._current_step: int = 0
        self._episode_ended: bool = False
        self._state: Dict[str, Any] = self._get_initial_state()
        self._last_observation: Optional[Observation] = None
        self._episode_history: List[Tuple[Observation, Response]] = []

    @abstractmethod
    async def setup(self) -> None:
        r"""Set up the environment, including verifier initialization."""
        if self._is_setup:
            return

        # TODO: implement something to initialize in respective classes
        # await self.verifier.setup()
        # await self.dataset.setup()
        # await self.extractor.setup()

        # initialize agents if present
        if self.teacher_agent:
            await self.teacher_agent.reset()
        if self.generator_agent:
            await self.generator_agent.reset()

        self._is_setup = True

    @abstractmethod
    async def teardown(self) -> None:
        r"""Clean up resources, including verifier teardown."""
        if not self._is_setup:
            return

        # Cleanup components
        await self.verifier.cleanup()
        await self.dataset.cleanup()
        await self.extractor.cleanup()

        self._is_setup = False

    @abstractmethod
    async def reset(self) -> Observation:
        r"""Reset the environment to initial state.

        Returns:
            Initial observation for the episode
        """

        if not self._is_setup:
            await self.setup()

        # Reset state
        self._current_step = 0
        self._episode_ended = False
        self._episode_history = []
        self._state = self._get_initial_state()

        # Get initial observation
        observation = self._get_next_observation()
        if observation is None:
            raise RuntimeError("Failed to get initial observation")

        self._last_observation = observation

        return observation

    async def process_response(
        self, response: Response, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], VerificationResult]:
        r"""Process an response through extraction and verification.

        Args:
            response: Response containing the output.
            context: Optional context for extraction.

        Returns:
            Tuple of (extraction_result, verification_result).
        """
        # TODO: Define response.content/message in Response class
        extraction_result = await self.extractor.extract(
            str(
                response
            ),  # Temporary solution until Response class is defined
            context or {},
        )

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

        if not self._is_setup:
            raise RuntimeError("Environment not set up. Call setup() first.")
        if self._episode_ended:
            raise RuntimeError("Episode has ended. Call reset() first.")
        if self._last_observation is None:
            raise RuntimeError("No current observation. Call reset() first.")

        self._current_step += 1

        current_obs: Observation = self._last_observation
        self._episode_history.append((current_obs, response))

        # process response
        extraction_result, verification_result = await self.process_response(
            response
        )

        # compute rewards
        rewards = await self.compute_reward(
            response, extraction_result, verification_result
        )

        # check termination
        done = self._is_done()

        next_obs = (
            self._get_terminal_observation()
            if done
            else self._get_next_observation()
        )

        self._last_observation = next_obs
        self._episode_ended = done

        return StepResult(
            observation=next_obs,
            reward=rewards,
            done=done,
            info={
                "extraction_result": extraction_result,
                "verification_result": verification_result,
                "step": self._current_step,
                "state": self._state,
            },
        )

    @abstractmethod
    def _get_initial_state(self) -> Dict[str, Any]:
        r"""Get initial environment state."""

        return {
            "current_datapoint": None,
            "attempts": 0,
            "success_rate": 0.0,
            "rewards": [],
            "termination_reason": None,
        }

    @abstractmethod
    def _get_next_observation(self) -> Observation:
        r"""Get the next observation for the environment.

        Returns:
            Observation for the next step
        """

        # TODO: Implement sample() method in BaseDataset
        # datapoint = self.dataset.sample()

        # TODO: Update once DataPoint structure is defined
        return Observation(
            question="No data available",
            context={"status": "placeholder", "step": self._current_step},
            metadata={
                "step": self._current_step,
                "datapoint_id": f"placeholder_{self._current_step}",
                "is_placeholder": True,
            },
        )

    @abstractmethod
    def _get_terminal_observation(self) -> Observation:
        r"""Get the terminal observation when episode ends.

        Returns:
            Terminal observation
        """
        return Observation(
            question="Episode completed",
            context={},
            metadata={"terminal": True, "final_step": self._current_step},
        )

    @abstractmethod
    async def compute_reward(
        self,
        response: Response,
        extraction_result: Dict[str, Any],
        verification_result: VerificationResult,
    ) -> Dict[str, float]:
        r"""Compute reward scores for different aspects of the response.

        Args:
            response: The response.
            extraction_result: Extracted information from response
            verification_result: Result from the verifier.

        Returns:
            Dictionary of reward scores for different aspects.
        """
        rewards = {}

        # TODO: Define success attribute in VerificationResult
        verification_success = 0.0  # Temporary
        rewards["correctness"] = 1.0 if verification_success > 0.5 else 0.0

        # Update state
        self._state["rewards"].append(rewards)
        total_attempts = self._state["attempts"] + 1
        self._state["success_rate"] = (
            self._state["success_rate"] * (total_attempts - 1)
            + verification_success
        ) / total_attempts

        # Additional reward aspects can be added here
        # For example:
        # - Solution efficiency/structure
        # - Reasoning quality
        # ...

        return rewards

    def _is_done(self) -> bool:
        """Check if episode should terminate."""
        if self.max_steps and self._current_step >= self.max_steps:
            return True
        return False

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Get environment metadata."""
        return self._metadata.copy()

    @property
    def current_step(self) -> int:
        r"""Get current step number."""
        return self._current_step
