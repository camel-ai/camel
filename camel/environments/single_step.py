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

from camel.datasets.base import DataPoint, GenerativeDataset, StaticDataset
from camel.extractors.base import BaseExtractor
from camel.logger import get_logger
from camel.verifiers.base import (
    BaseVerifier,
    VerificationResult,
)
from camel.verifiers.models import (
    VerifierInput,
)

from .models import Action, Observation, StepResult

logger = get_logger(__name__)


class SingleStepEnv:
    r"""A single-step environment for reinforcement learning with LLMs.

    Key Features:
    - Samples questions from a dataset and asks the LLM
    - Extracts verifiable information from model responses.
    - Verifies extracted responses against ground truth.
    - Computes and assigns rewards based on correctness.
    - Supports async setup, teardown, and cleanup of resources.

    This class is intended as a foundation for RL experiments involving
    LLM-based policies, ensuring structured interactions between model
    actions and verification mechanisms.
    """

    PLACEHOLDER_OBS = Observation(
        question="Episode ended. This is just a placeholder."
    )

    ACCURACY_REWARD = 10

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
        r"""Set up the environment by initializing the verifier and extractor.

        This method ensures that the environment is ready for interaction.
        It sets up necessary components, including the verifier and extractor.

        Raises:
            Exception: If setup fails due to an internal error.
        """

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

    async def close(self) -> None:
        r"""Clean up and close all resources used by the environment.

        This method shuts down the verifier and extractor, resets the internal
        state, and ensures that the environment is properly closed.

        Raises:
            Exception: If an error occurs while closing the environment.
        """

        if not self._is_setup:
            return

        try:
            self._is_setup = False
            await self.verifier.cleanup()
            await self.extractor.cleanup()
            self._state = None
            self._episode_ended = False
            logger.info('Environment closed successfully')
        except Exception as e:
            logger.error(f'Failed to close environment: {e}')
            raise

    async def reset(self) -> Observation:
        r"""Reset the environment and start a new episode.

        This method samples a new data point from the dataset and returns the
        initial observation.

        Returns:
            Observation: The first observation of the new episode, including
                the question.

        Raises:
            Exception: If the environment is not set up properly.
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
        r"""Take a step in the environment using the given action.

        This method processes the LLM response, extracts verifiable content,
        verifies correctness, computes rewards, and ends the episode.

        Args:
            action (Action): The action containing the LLM response to
                evaluate.

        Returns:
            StepResult: Contains the next observation (placeholder), total
                reward, reward breakdown, completion flag, and additional
                information.

        Raises:
            RuntimeError: If the environment is not set up, the episode has
                ended, or there is no valid current observation.
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
        r"""Compute reward scores based on verification results.

        This method calculates the reward based on correctness and any
        additional custom reward components.

        Args:
            action (Action): The action taken in the environment.
            extraction_result (str): The extracted verifiable content from the
                LLM response.
            verification_result (VerificationResult): The result of verifying
                the extracted response.

        Returns:
            Tuple[float, Dict[str, float]]: A tuple containing:
                - Total reward (float)
                - Dictionary of individual reward components.

        Raises:
            Exception: If an error occurs while computing rewards.
        """

        rewards: Dict[str, float] = {}

        rewards["correctness"] = (
            self.ACCURACY_REWARD if verification_result.status else 0.0
        )

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
        r"""Compute additional custom reward components.

        This method should be implemented by subclasses to define
        domain-specific reward calculations.

        Args:
            action (Action): The action taken in the environment.
            extraction_result (str): The extracted verifiable content from the
                LLM response.
            verification_result (VerificationResult): The result of verifying
                the extracted response.

        Returns:
            Dict[str, float]: A dictionary mapping custom reward categories
                to their values.
        """
        pass

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Retrieve the metadata of the environment.

        This provides additional parameters and configuration details.

        Returns:
            Dict[str, Any]: A copy of the environment's metadata.
        """

        return self._metadata.copy()
