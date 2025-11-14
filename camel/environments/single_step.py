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

import asyncio
import random
from typing import Any, Dict, List, Optional, Tuple, Union

from camel.datasets import BaseGenerator, DataPoint, StaticDataset
from camel.logger import get_logger
from camel.verifiers.base import (
    BaseVerifier,
    VerificationOutcome,
    VerificationResult,
)

from .models import Action, Observation, StepResult

logger = get_logger(__name__)


class SingleStepEnv:
    r"""A lightweight environment for single-step RL with LLMs as policy.

    This environment models a single interaction between an LLM-based agent
    and a problem drawn from a dataset—such as a question-answering or
    math problem—where the agent produces one response and receives feedback.

    Core Flow:
        - A question is sampled from a (possibly infinitely long) dataset.
        - The LLM generates a single-step response (the action).
        - The response is verified against the ground truth.
        - A reward is computed based on correctness and optional custom logic.

    Key Features:
        - Batched evaluation with per-sample state tracking.
        - Async setup and teardown for verifiers and related resources.
        - Supports deterministic sampling via local RNG (optional seed).
        - Extensible reward computation via subclassing.
    """

    PLACEHOLDER_OBS = Observation(
        question="Episode ended. This is just a placeholder."
    )

    ACCURACY_REWARD = 1

    def __init__(
        self,
        dataset: Union[StaticDataset, BaseGenerator],
        verifier: BaseVerifier,
        timeout: Optional[float] = 180.0,
        **kwargs,
    ) -> None:
        r"""Initialize the SingleStepEnv.

        Args:
            dataset (Union[StaticDataset, BaseGenerator]): Dataset to sample
                problems from.
            verifier (BaseVerifier): Verifier used to evaluate LLM responses
                against ground-truth answers.
            timeout (Optional[float], optional): The execution timeout in
                seconds. (default: :obj:`180.0`)
            **kwargs: Optional metadata or configuration values.

        Notes:
            This class assumes all interactions are single-step: one question,
            one LLM response, one reward.
        """
        self._timeout = timeout
        self.dataset = dataset
        self.verifier = verifier
        self._metadata = kwargs

        # State tracking
        self._is_setup: bool = False
        self._states: List[DataPoint] = []
        self._states_done: List[bool] = []
        self.current_batch_size: int = 0

    async def setup(self) -> None:
        r"""Set up the environment by initializing the verifier.

        This method ensures that the environment is ready for interaction.
        It sets up necessary components, including the verifier.

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

        This method shuts down the verifier, resets the internal
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
            self.current_batch_size = 0
            logger.info('Environment closed successfully')
        except Exception as e:
            logger.error(f'Failed to close environment: {e}')
            raise

    async def reset(
        self, batch_size: int = 1, seed: Optional[int] = None
    ) -> Union[Observation, List[Observation]]:
        r"""Resets the environment and starts a new episode.

        This method samples a new batch of data points from the dataset and
        returns the corresponding initial observations.

        If a seed is provided, a local random number generator is initialized
        for deterministic sampling. The global random state is not affected.

        Args:
            batch_size (int): Number of data points to sample.
                (default: :obj:`1`)
            seed (Optional[int]): Seed for deterministic sampling. If None,
                sampling is non-deterministic. (default: :obj:`None`)

        Returns:
            Observation or List[Observation]: Initial observation(s) for the
                episode.

        Raises:
            RuntimeError: If called before all previous states are processed.
            ValueError: If batch size exceeds dataset size.
            TypeError: If the dataset is of an unsupported type.
        """
        if batch_size <= 0:
            raise ValueError("Batch size must be positive")

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
            rng = random.Random(seed)
        else:
            rng = random.Random()

        if isinstance(self.dataset, StaticDataset):
            dataset_len = len(self.dataset)

            if batch_size > dataset_len:
                raise ValueError(
                    f"Batch size {batch_size} is too large for dataset "
                    f"of size {dataset_len}"
                )

            start_idx = rng.randint(0, dataset_len - batch_size)
            idx_slice = slice(start_idx, start_idx + batch_size)
            val = self.dataset[idx_slice]
            self._states = [val] if isinstance(val, DataPoint) else val

            self.current_batch_size = len(self._states)
            self._states_done = [False] * self.current_batch_size

            observations = [
                Observation(
                    question=sample.question,
                    context={},
                    metadata=sample.metadata
                    if sample.metadata is not None
                    else {},
                )
                for sample in self._states
            ]

            return observations[0] if batch_size == 1 else observations

        elif isinstance(self.dataset, BaseGenerator):
            # Generate more data if needed
            if batch_size > len(self.dataset):
                new_datapoints_needed = batch_size - len(self.dataset)
                await self.dataset.generate_new(n=new_datapoints_needed)

                # Verify that enough data was generated
                if len(self.dataset) < batch_size:
                    raise RuntimeError(
                        f"Failed to generate enough datapoints. "
                        f"Requested {batch_size}, but only "
                        f"{len(self.dataset)} available after generation."
                    )

            # Choose sampling strategy based on whether seed is provided
            if seed is not None:
                # Deterministic random sampling when seed is provided
                random_indices = rng.sample(
                    range(len(self.dataset)), batch_size
                )
                self._states = [self.dataset[ind] for ind in random_indices]
            else:
                # Sequential sampling when no seed (backward compatible)
                # Use async_sample to maintain sequential behavior
                self._states = [
                    await self.dataset.async_sample()
                    for _ in range(batch_size)
                ]

            self.current_batch_size = batch_size
            self._states_done = [False] * batch_size

            observations = [
                Observation(
                    question=sample.question,
                    context={},
                    metadata=sample.metadata
                    if sample.metadata is not None
                    else {},
                )
                for sample in self._states
            ]

            return observations[0] if batch_size == 1 else observations

        else:
            raise TypeError(f"Unsupported dataset type: {type(self.dataset)}")

    async def step(
        self, action: Union[Action, List[Action], str, Dict[int, str]]
    ) -> Union[
        Tuple[Observation, float, bool, Dict[str, Any]],
        List[Tuple[Observation, float, bool, Dict[str, Any]]],
    ]:
        r"""Execute one interaction step in the environment using the
        proposed solution.

        This method processes the agent's response(s) to the current
        observation(s), verifies the correctness of the responses using
        the verifier, computes rewards, and returns the resulting
        state transition(s).

        The environment is strictly single-step. Once an action is
        submitted for a state, that state is marked as done, and
        the observation will not change.

        Args:
            action (Union[Action, List[Action], str, Dict[int, str]]):
                The action(s) taken by the agent,
                    which should contain the response(s)
                to the observation(s). Can be:
                - A single `Action` object (for batch size 1),
                - A list of `Action` objects (for batched evaluation),
                - A raw string (only allowed when batch size is 1).
                - A dict that maps indices to their `llm_response`
                    (for batched evaluation)

        Returns:
            Union[Tuple[Observation, float, bool, Dict[str, Any]], List[...]]:
                A tuple or list of tuples containing:
                - `Observation`: Placeholder indicating episode end.
                - `float`: The reward for the response.
                - `bool`: Whether the episode is done
                    (always `True` in this case).
                - `dict`: Additional info including the proposed solution,
                          verification result, and original data point.

        Raises:
            RuntimeError: If the environment has not been set up,
                or if `reset()` has not been called.
            ValueError: If invalid action format, duplicate indices,
                or out-of-bounds indices are detected.
            asyncio.TimeoutError: If the step execution exceeds the timeout.
        """

        if not self._is_setup:
            raise RuntimeError("Environment not set up. Call setup() first.")
        if self._batch_done():
            raise RuntimeError(
                "Episodes have ended for batch. Call reset() first."
            )
        if not self._states:
            raise RuntimeError("No current observation. Call reset() first.")

        actions = self._normalize_actions(action)

        indices = [a.index for a in actions]

        for idx in indices:
            if idx < 0 or idx >= len(self._states):
                raise ValueError(f"Invalid state index {idx}.")
            if self._states_done[idx]:
                raise ValueError(f"State at index {idx} is already finished.")

        num_actions = len(actions)
        if self.current_batch_size % num_actions != 0:
            logger.warning(
                f"Number of actions ({num_actions}) is not a divisor of "
                f"total batch size ({self.current_batch_size})"
            )

        proposed_solutions = [act.llm_response for act in actions]
        ground_truths: List[str] = [
            self._states[idx].final_answer for idx in indices
        ]

        try:
            verification_results = await asyncio.wait_for(
                self.verifier.verify_batch(
                    solutions=proposed_solutions,
                    reference_answers=ground_truths,  # type: ignore [arg-type]
                    raise_on_error=True,
                ),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError as e:
            logger.error(
                f"Step verification timed out after {self._timeout}s: {e}"
            )
            # Return timeout verification results
            verification_results = [
                VerificationResult(
                    result="",
                    status=VerificationOutcome.TIMEOUT,
                    error_message=f"Verification timed out "
                    f"after {self._timeout}s",
                )
                for _ in range(len(proposed_solutions))
            ]
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            # Return failed verification results with status=FAILURE
            verification_results = [
                VerificationResult(
                    result="",
                    status=VerificationOutcome.FAILURE,
                    error_message=f"Verification error: {e}",
                )
                for _ in range(len(proposed_solutions))
            ]

        # Track which solutions have been processed and which have timed out
        total_rewards = [0.0] * len(proposed_solutions)
        rewards_dicts = [{"correctness": 0.0}] * len(proposed_solutions)

        try:
            # First try to compute all rewards with a timeout
            computed_rewards, computed_rewards_dicts = await asyncio.wait_for(
                self._compute_reward_batch(
                    proposed_solutions, verification_results
                ),
                timeout=self._timeout,
            )
            # If successful, use all the computed values
            total_rewards = computed_rewards
            rewards_dicts = computed_rewards_dicts
        except asyncio.TimeoutError as e:
            logger.error(
                f"Reward computation timed out after {self._timeout}s: {e}"
            )
            # Try to compute rewards one by one to identify which ones time out
            for i, (solution, result) in enumerate(
                zip(proposed_solutions, verification_results)
            ):
                try:
                    individual_rewards = await asyncio.wait_for(
                        self._compute_custom_reward(solution, result),
                        timeout=self._timeout,
                    )
                    # If successful, calculate the reward for this solution
                    correctness_reward = (
                        self.ACCURACY_REWARD if result.status else 0.0
                    )
                    rewards_dict = {
                        "correctness": correctness_reward,
                        **individual_rewards,
                    }
                    total_rewards[i] = sum(rewards_dict.values())
                    rewards_dicts[i] = rewards_dict
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Reward computation for solution {i} timed out"
                    )
                except Exception as e:
                    logger.warning(
                        f"Error computing reward for solution {i}: {e}"
                    )
        except Exception as e:
            logger.error(f"Reward computation failed: {e}")

        # Create and return step results in batch
        step_results = [
            StepResult(
                observation=self.PLACEHOLDER_OBS,
                reward=total_rewards[i],
                rewards_dict=rewards_dicts[i],
                done=True,
                info={
                    "proposed_solution": proposed_solutions[i],
                    "verification_result": verification_results[i],
                    "state": self._states[indices[i]],
                },
            ).as_tuple()
            for i in range(len(actions))
        ]

        for _, idx in enumerate(indices):
            self._states_done[idx] = True

        return step_results[0] if len(step_results) == 1 else step_results

    def _normalize_actions(
        self, action: Union[Action, List[Action], str, Dict[int, str]]
    ) -> List[Action]:
        r"""Normalize the user-provided action(s) into a validated list
        of `Action` objects.

        This method handles flexibility in input format by converting
        raw strings (only allowed when batch size is 1) and dictionaries,
        ensuring all necessary structure and integrity checks on
        actions (e.g., index bounds, duplicates).

        Args:
            action (Union[Action, List[Action], str]):
                The raw input action(s) provided by the agent. Can be:
                - A single `Action` object.
                - A list of `Action` objects.
                - A raw string (if `batch_size == 1`), auto-wrapped
                    in an `Action`.
                - A dict mapping int indices to str responses

        Returns:
            List[Action]: A list of validated `Action` instances
                ready for evaluation.

        Raises:
            ValueError: If:
                - Action indices are invalid or duplicated,
                - Action list is empty,
                - Index mismatches expected values
                    (e.g., 0 for batch size 1),
                - Wrong structure is used (e.g.,
                    string used with batch size > 1,
                    dict used with batch size == 1).
            TypeError: If the action is of an unsupported type.
        """

        if isinstance(action, str):
            if self.current_batch_size != 1:
                raise ValueError(
                    "String input for action is only allowed"
                    " when batch_size == 1"
                )
            logger.warning("Auto-converting from str to Action", stacklevel=2)
            actions = [Action(index=0, llm_response=action)]

        elif isinstance(action, dict):
            if not all(isinstance(k, int) for k in action.keys()):
                raise ValueError("All dictionary keys must be integers")

            if self.current_batch_size == 1 and list(action.keys()) != [0]:
                raise ValueError(
                    "For batch_size=1, dict input must have exactly one key: 0"
                )
            actions = [
                Action(index=k, llm_response=v) for k, v in action.items()
            ]
        elif isinstance(action, Action):
            actions = [action]
        elif isinstance(action, list):
            if not action:
                raise ValueError("Action list cannot be empty")
            if not all(isinstance(a, Action) for a in action):
                raise ValueError(
                    "All elements in the list must be Action objects"
                )
            actions = action
        else:
            raise TypeError("Action must be a str, Action, or list of Actions")

        if self.current_batch_size == 1 and len(actions) != 1:
            raise ValueError(
                "For batch_size=1, expect a single Action, a dictionary or a "
                "list containing exactly one Action"
            )

        # Validate indices
        for a in actions:
            if not isinstance(a.index, int):
                raise ValueError(
                    f"Action index must be an integer, got {a.index}"
                )
            if self.current_batch_size == 1:
                if a.index != 0:
                    raise ValueError(
                        "For batch_size=1, Action index must be 0"
                    )

        indices = [a.index for a in actions]
        if len(set(indices)) != len(indices):
            raise ValueError("Duplicate state indices in actions.")

        return actions

    async def _compute_reward_batch(
        self,
        proposed_solutions: List[str],
        verification_results: List[VerificationResult],
    ) -> Tuple[List[float], List[Dict[str, float]]]:
        r"""Compute rewards for a batch of proposed solutions based on
        verification results.

        Args:
            proposed_solutions (List[str]): List of LLM-generated responses to
                evaluate.
            verification_results (List[VerificationResult]): List of
                verification outcomes for each solution.

        Returns:
            Tuple containing:
                - List of total rewards for each solution.
                - List of reward component dictionaries for each solution.
        """
        if len(proposed_solutions) != len(verification_results):
            raise ValueError(
                f"Length mismatch: {len(proposed_solutions)} solutions vs "
                f"{len(verification_results)} verification results"
            )

        total_rewards = []
        rewards_dicts = []

        for solution, verification_result in zip(
            proposed_solutions, verification_results
        ):
            rewards: Dict[str, float] = {}

            rewards["correctness"] = (
                self.ACCURACY_REWARD if verification_result.status else 0.0
            )

            further_rewards = await self._compute_custom_reward(
                solution, verification_result
            )
            rewards = {**rewards, **further_rewards}

            total_reward = sum(rewards.values())
            total_rewards.append(total_reward)
            rewards_dicts.append(rewards)

        return total_rewards, rewards_dicts

    async def _compute_custom_reward(
        self, proposed_solution: str, verification_result: VerificationResult
    ) -> Dict[str, float]:
        r"""Compute additional custom reward components for a single solution.

        To be overridden by subclasses for domain-specific rewards.

        Args:
            proposed_solution (str): The LLM-generated response.
            verification_result (VerificationResult): The verification outcome.

        Returns:
            Dict[str, float]: Dictionary of custom reward components.
        """
        return {}

    def _batch_done(self) -> bool:
        r"""Check if all states in the current batch are done.

        Returns:
            bool: True if all states are marked as done, False otherwise.
        """
        return all(self._states_done)

    def _batch_started(self) -> bool:
        r"""Check if the batch processing has started.

        Returns:
            bool: True if at least one state is marked as done, False
                otherwise.
        """
        return any(self._states_done)

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Retrieve the metadata of the environment.

        This provides additional parameters and configuration details.

        Returns:
            Dict[str, Any]: A copy of the environment's metadata.
        """

        return self._metadata.copy()
