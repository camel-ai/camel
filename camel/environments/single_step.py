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


from abc import abstractmethod
from typing import Any, Dict, Optional, Tuple

from camel.agents import ChatAgent
from camel.datasets.base import DataPoint, GenerativeDataset, StaticDataset
from camel.extractors.base import BaseExtractor
from camel.logger import get_logger
from camel.verifiers.base import (
    BaseVerifier,
    VerificationResult,
)
from camel.verifiers.models import (
    VerificationOutcome,
    VerifierInput,
)

from .models import Action, Observation, StepResult

logger = get_logger(__name__)

# TODO: Add MachineInfo into this file
# TODO: Implement Curriculum Learning
# Note: TeacherAgent should be renamed into neural_reward_model.
#       This is where PRMs or such could be useful.
#       Should probably be its own class and not just raw ChatAgent


class SingleStepEnv:
    r"""Base class for all single step
    RL training environments.

    An environment ties everything together. It:
    1. Holds state and manages curriculum progression
    2. Defines reward functions and hint generation
    3. Manages dataset and task selection
    4. Provides reset and step functions
    5. Handles verifier setup and teardown

    Key Features:
    - Reward shaping based on solution quality
    - Hint generation from verified solutions
    - Task selection based on agent progress
    - Practice environment generation
    - Chain-of-thought validation
    """

    PLACEHOLDER_OBS = Observation(
        question="Episode ended. This is just a placeholder."
    )

    def __init__(
        self,
        dataset: StaticDataset | GenerativeDataset,
        verifier: BaseVerifier,
        extractor: BaseExtractor,
        **kwargs,
    ) -> None:
        r"""Initialize the environment.

        Args:
            dataset: Dataset to sample questions from.
            verifier: Verifier to check responses.
            extractor: Extractor to process LLM responses.
            **kwargs: Additional environment parameters.
        """
        self.dataset = dataset
        self.verifier = verifier
        self.extractor = extractor
        self._metadata = kwargs

        # State tracking
        self._is_setup: bool = False
        self._state: Optional[DataPoint] = None
        self._episode_ended: bool = False

    async def setup(self) -> None:
        r"""Set up the environment, including verifier initialization."""
        if self._is_setup:
            return

        try:
            await self.verifier.setup()
            await self.extractor.setup()

            self._is_setup = True
            logger.info('Environment setup completed successfully')
        except Exception as e:
            logger.error(f'Failed to setup environment: {e}')
            raise

    async def teardown(self) -> None:
        r"""Clean up resources, including verifier teardown."""
        if not self._is_setup:
            return

        try:
            # Cleanup components
            await self.verifier.cleanup()
            await self.extractor.cleanup()

            self._is_setup = False
            logger.info('Environment teardown completed successfully')
        except Exception as e:
            logger.error(f'Failed to teardown environment: {e}')
            raise

    async def close(self) -> None:
        r"""Perform a full cleanup of all environment resources."""
        if not self._is_setup:
            return

        try:
            await self.teardown()

            # TODO: Once teacher and dataset have clean up
            # methods, call them here
            self._state = None
            self._episode_ended = False
            logger.info('Environment closed successfully')
        except Exception as e:
            logger.error(f'Failed to close environment: {e}')
            raise

    async def reset(self) -> Observation:
        r"""Reset the environment to initial state.

        Returns:
            Initial observation for the episode
        """

        if not self._is_setup:
            await self.setup()

        self._episode_ended = False

        # Sample a datapoint

        self._state = self.dataset.sample()

        observation = Observation(
            question=self._state.question, context={}, metadata={}
        )

        return observation

    async def step(self, action: Action) -> StepResult:
        r"""Take a step in the environment.

        Args:
            action: Action containing everything that is needed
            to progress in the environment

        Returns:
            StepResult containing next observation, reward, done flag, and info
        """

        if not self._is_setup:
            raise RuntimeError("Environment not set up. Call setup() first.")
        if self._episode_ended:
            raise RuntimeError("Episode has ended. Call reset() first.")
        if self._state is None:
            raise RuntimeError("No current observation. Call reset() first.")

        # extract verifiable part from llm response
        extraction_result = await self.extractor.extract(action.llm_response)

        if not extraction_result:
            raise RuntimeError(f"Couldn't extract from {action.llm_response}")

        # verify the extracted
        verification_result = await self.verifier.verify(
            VerifierInput(
                llm_response=extraction_result,
                ground_truth=self._state.final_answer,
            )
        )

        # compute rewards
        total_reward, rewards_dict = await self._compute_reward(
            action, extraction_result, verification_result
        )

        self._episode_ended = True

        return StepResult(
            observation=self.PLACEHOLDER_OBS,
            reward=total_reward,
            rewards_dict=rewards_dict,
            done=True,
            info={
                "extraction_result": extraction_result,
                "verification_result": verification_result,
                "state": self._state,
            },
        )

    async def _compute_reward(
        self,
        action: Action,
        extraction_result: str,
        verification_result: VerificationResult,
    ) -> Tuple[float, Dict[str, float]]:
        r"""Compute reward scores for different aspects of the response.

        Args:
            action: The action.
            extraction_result: Extracted information from response
            verification_result: Result from the verifier.

        Returns:
            - Total reward
            - Dictionary of reward scores for different aspects.
        """
        rewards: Dict[str, float] = {}

        # Get success from verification result status
        verification_success = float(
            verification_result.status == VerificationOutcome.SUCCESS
        )
        # FIXME: Magic numbers
        rewards["correctness"] = 1.0 if verification_success > 0.5 else 0.0

        further_rewards = await self._compute_custom_reward(
            action, extraction_result, verification_result
        )

        rewards = rewards | further_rewards

        return sum(rewards.values()), rewards

    @abstractmethod
    async def _compute_custom_reward(
        self,
        action: Action,
        extraction_result: str,
        verification_result: VerificationResult,
    ) -> Dict[str, float]:
        pass

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Get environment metadata."""
        return self._metadata.copy()
