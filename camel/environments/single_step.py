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

import random
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from camel.datasets import BaseGenerator, DataPoint, StaticDataset
from camel.logger import get_logger
from camel.verifiers.base import (
    BaseVerifier,
    VerificationResult,
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
        dataset: Union[StaticDataset, BaseGenerator],
        verifier: BaseVerifier,
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
        self._metadata = kwargs

        # State tracking
        self._is_setup: bool = False
        self._states: List[DataPoint] = []
        self._states_done: List[bool] = []
        self.current_batch_size: int = 0

    async def setup(self) -> None:
        r"""Set up the environment by initializing the verifier and extractor.

        This method ensures that the environment is ready for interaction.
        It sets up necessary components, including the verifier and extractor.

        Raises:
            Exception: If setup fails due to an internal error.
        """

        if self._is_setup:
            logger.warning("Environment has already been set up")
            return

        try:
            await self.verifier.setup()

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
            logger.warning(
                "Not closing environment - has not been set up yet."
            )
            return

        try:
            self._is_setup = False
            await self.verifier.cleanup()
            self._states = []
            self._states_done = []
            logger.info('Environment closed successfully')
        except Exception as e:
            logger.error(f'Failed to close environment: {e}')
            raise

    async def reset(
        self, batch_size: int = 1, seed: Optional[int] = None
    ) -> Union[Observation, List[Observation]]:
        r"""Reset the environment and start a new episode.

        This method samples a new batch of data points from the dataset
            and returns the initial observations.
        If the batch size is 1, a single observation is returned.

        Returns:
            Union[Observation, List[Observation]]:
                One or more initial observations.

        Raises:
            Exception: If the environment is not set up properly.
        """

        if not self._is_setup:
            logger.warning(
                "reset() called on un-setup environment. Setting up..."
            )
            await self.setup()

        if self._batch_started() and not self._batch_done():
            logger.error(
                "Reset called before all states were processed. "
                "Call step on remaining states first."
            )
            raise RuntimeError(
                "reset() called before all states in batch were processed."
            )

        if seed is not None:
            random.seed(seed)

        if isinstance(self.dataset, StaticDataset):
            dataset_len = len(self.dataset)

            if batch_size > dataset_len:
                raise ValueError(
                    f"Batch size {batch_size} is too large for dataset "
                    f"of size {dataset_len}"
                )

            start_idx = random.randint(0, dataset_len - batch_size)
            idx_slice = slice(start_idx, start_idx + batch_size)
            self._states = self.dataset[idx_slice]
            self.current_batch_size = len(self._states)
            self._states_done = [False] * self.current_batch_size

            observations = [
                Observation(question=sample.question, context={}, metadata={})
                for sample in self._states
            ]

            return observations[0] if batch_size == 1 else observations

        elif isinstance(self.dataset, BaseGenerator):
            raise NotImplementedError(
                "Reset not yet implemented for BaseGenerator datasets."
            )

        else:
            raise TypeError(f"Unsupported dataset type: {type(self.dataset)}")

    async def step(
        self, action: Union[Action, List[Action]]
    ) -> Union[StepResult, List[StepResult]]:
        """
        Process actions for a subset of states and update their
            finished status.

        Args:
            action: Single action or list of actions, where each action
                contains an index indicating which state it corresponds to.


        Returns:
            StepResult or list of StepResults for the processed states

        Raises:
            RuntimeError: If environment isn't set up or episode has ended.
            ValueError: If indices are invalid, duplicate, or correspond to
                finished states.
        """
        if not self._is_setup:
            raise RuntimeError("Environment not set up. Call setup() first.")
        if self._batch_done():
            raise RuntimeError(
                "Episodes have ended for batch. Call reset() first."
            )
        if not self._states:
            raise RuntimeError("No current observation. Call reset() first.")

        # Normalize everything to list
        actions = [action] if isinstance(action, Action) else action
        indices = [act.index for act in actions]

        if len(set(indices)) != len(indices):
            raise ValueError("Duplicate state indices in actions.")
        for idx in indices:
            if idx < 0 or idx >= len(self._states):
                raise ValueError(f"Invalid state index {idx}.")
            if self._states_done[idx]:
                raise ValueError(f"State at index {idx} is already finished.")

        num_actions = len(actions)

        if (self.current_batch_size % num_actions != 0):
            logger.warning(
                f"Number of actions ({num_actions}) is not a divisor of"
                f"total batch size ({self.current_batch_size})"
            )

        proposed_solutions = [act.llm_response for act in actions]
        ground_truths: List[str] = [
            self._states[idx].final_answer for idx in indices
        ]
        verification_results = await self.verifier.verify_batch(
            solutions=proposed_solutions,
            ground_truths=cast(
                list[str | None], ground_truths
            ),  # to satisfy mypy
            raise_on_error=True,
        )

        total_rewards, rewards_dicts = await self._compute_reward_batch(
            proposed_solutions, verification_results
        )

        step_results = []
        # TODO: batch this
        for i, action in enumerate(actions):
            idx = action.index
            step_result = StepResult(
                observation=self.PLACEHOLDER_OBS,
                reward=total_rewards[i],
                rewards_dict=rewards_dicts[i],
                done=True,
                info={
                    "proposed_solution": proposed_solutions[i],
                    "verification_result": verification_results[i],
                    "state": self._states[idx],
                },
            )
            step_results.append(step_result)
            self._states_done[idx] = True

        return step_results[0] if len(step_results) == 1 else step_results

    # TODO: implement
    async def _compute_reward_batch(
        self, proposed_solutions, verification_results
    ) -> Tuple[List[float], List[Dict[str, float]]]:
        raise NotImplementedError

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
        return {}

    def _batch_done(self) -> bool:
        return all(self._states_done)

    def _batch_started(self) -> bool:
        return any(self._states_done)

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Retrieve the metadata of the environment.

        This provides additional parameters and configuration details.

        Returns:
            Dict[str, Any]: A copy of the environment's metadata.
        """

        return self._metadata.copy()
