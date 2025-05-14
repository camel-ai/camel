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
from typing import Any, Dict, List, Optional, Tuple, Union

from camel.environments.models import Action, Observation, StepResult
from camel.extractors.base import BaseExtractor
from camel.logger import get_logger

logger = get_logger(__name__)


class MultiStepEnv(ABC):
    r"""A multi-step environment for reinforcement learning with LLMs."""

    def __init__(
        self,
        extractor: BaseExtractor,
        max_steps: Optional[int] = None,
        **kwargs,
    ) -> None:
        r"""Initialize the environment.

        Args:
            extractor: Extractor to process LLM responses.
            max_steps: Maximum steps per episode.
            **kwargs: Additional environment parameters.
        """
        self.extractor = extractor
        self.max_steps = max_steps
        self._metadata = kwargs

        # State tracking
        self._is_setup: bool = False
        self._current_step: int = 0
        self._episode_ended: bool = False
        self._state: Dict[str, Any] = self._get_initial_state()
        self._last_observation: Optional[Observation] = None
        self._episode_history: List[Tuple[Observation, Action]] = []

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
            await self.extractor.setup()
            await self._setup()
            self._is_setup = True
            logger.info('Environment setup completed successfully')
        except Exception as e:
            logger.error(f'Failed to setup environment: {e}')
            raise

    async def _setup(self) -> None:
        return

    async def close(self) -> None:
        r"""Clean up and close all resources used by the environment.
        This method shuts down the verifier, calls the internal
        close function that is implemented in any MultiStepEnv,
        and ensures that the environment is properly closed.

        Raises:
            Exception: If an error occurs while closing the environment.
        """
        if not self._is_setup:
            return

        try:
            await self.extractor.cleanup()

            await self._close()

            self._is_setup = False
            logger.info('Environment teardown completed successfully')
        except Exception as e:
            logger.error(f'Failed to teardown environment: {e}')
            raise

    async def _close(self) -> None:
        return

    async def reset(
        self, batch_size: int = 1, seed: Optional[int] = None
    ) -> Union[Observation, List[Observation]]:
        r"""Reset the environment and start new episodes.

        Args:
            batch_size (int): Number of parallel episodes to run.
                (default: :obj:`1`)
            seed (Optional[int]): Seed for deterministic behavior.
                (default: :obj:`None`)

        Returns:
            Union[Observation, List[Observation]]: Initial observation(s)
                for the episode(s).

        Raises:
            RuntimeError: If called before setup or before previous batch
                is done.
        """
        if batch_size <= 0:
            raise ValueError("Batch size must be positive")

        if not self._is_setup:
            logger.warning(
                "reset() called on un-setup environment. Setting up..."
            )
            await self.setup()

        # Initialize batch tracking
        self.current_batch_size = batch_size
        self._states = [self._get_initial_state() for _ in range(batch_size)]
        self._states_done = [False] * batch_size
        self._current_steps = [0] * batch_size
        self._episode_histories: List[List[Tuple[Observation, Action]]] = [
            [] for _ in range(batch_size)
        ]

        # Get initial observations
        observations = [
            self._get_next_observation() for _ in range(batch_size)
        ]
        self._last_observations = observations

        return observations[0] if batch_size == 1 else observations

    async def step(
        self, action: Action
    ) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        r"""Take a step in the environment using the given action.

        This method updates the environment state based on the LLM's response,
        computes rewards, checks if the episode is done, and based on that
        gets the next or final observation.

        Args:
            action (Action): The action containing the LLM response.

        Returns:
            StepResult containing next observation, total reward, a dictionary
                of rewards, done flag, and info.

        Raises:
            RuntimeError: If the environment is not set up, the episode has
                ended, or there is no valid current observation.
        """
        if self.max_steps and self._current_step >= self.max_steps:
            return StepResult(
                observation=self._get_terminal_observation(),
                reward=0,
                rewards_dict={},
                done=True,
                info={"reason": "max_steps_reached"},
            ).as_tuple()

        if not self._is_setup:
            raise RuntimeError("Environment not set up. Call setup() first.")
        if self._episode_ended:
            raise RuntimeError("Episode has ended. Call reset() first.")
        if self._last_observation is None:
            raise RuntimeError("No current observation. Call reset() first.")

        self._current_step += 1

        current_obs: Observation = self._last_observation
        self._episode_history.append((current_obs, action))

        # Update the environment state based on the action
        await self._update_state(action)

        # Compute rewards
        total_reward, rewards_dict = await self.compute_reward()

        # Check termination
        done = self.is_done()

        # Get next observation based on the updated state
        next_obs = (
            self._get_terminal_observation()
            if done
            else self._get_next_observation()
        )

        self._last_observation = next_obs
        self._episode_ended = done

        return StepResult(
            observation=next_obs,
            reward=total_reward,
            rewards_dict=rewards_dict,
            done=done,
            info={
                "extraction_result": await self.extractor.extract(
                    action.llm_response
                ),
                "step": self._current_step,
                "state": self._state,  # Updated state
            },
        ).as_tuple()

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

    @abstractmethod
    def _get_initial_state(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def _update_state(self, action: Action) -> None:
        pass

    @abstractmethod
    def _get_next_observation(self) -> Observation:
        pass

    @abstractmethod
    def _get_terminal_observation(self) -> Observation:
        pass

    @abstractmethod
    async def compute_reward(
        self,
    ) -> Tuple[float, Dict[str, float]]:
        pass

    def is_done(self) -> bool:
        r"""Check if the episode should terminate.

        This function terminates the episode if the maximum number of
        steps is reached or if any other terminating criterion is met.

        Returns:
            bool: A boolean flag.
        """

        # After too many steps
        if self.max_steps and self._current_step >= self.max_steps:
            return True

        # Further termination logic can be implemented in subclass
        if self._is_done():
            return True

        return False

    @abstractmethod
    def _is_done(self) -> bool:
        pass

    @property
    def metadata(self) -> Dict[str, Any]:
        r"""Retrieve the metadata of the environment.

        This provides additional parameters and configuration details.

        Returns:
            Dict[str, Any]: A copy of the environment's metadata.
        """
        return self._metadata.copy()

    @property
    def current_step(self) -> int:
        r"""Get the current step number.

        Returns:
            int: The number of the step we are currently in.
        """
        return self._current_step
