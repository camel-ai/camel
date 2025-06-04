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

from camel.environments.models import Action, Observation, StepResult
from camel.extractors.base import BaseExtractor
from camel.logger import get_logger
import asyncio

logger = get_logger(__name__)


class MultiStepEnv(ABC):
    r"""A multi-step environment for reinforcement learning with LLMs."""

    def __init__(
        self,
        extractor: BaseExtractor,
        max_steps: Optional[int] = None,
        timeout: Optional[float] = 180.0,
        **kwargs,
    ) -> None:
        r"""Initialize the environment.

        Args:
            extractor: Extractor to process LLM responses.
            max_steps: Maximum steps per episode.
            timeout: The execution timeout in seconds.
            **kwargs: Additional environment parameters.
        """
        self.extractor = extractor
        self.max_steps = max_steps
        self._timeout = timeout
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

    async def reset(self) -> Observation:
        r"""Reset the environment to an initial state.

        Returns:
            Observation: The initial observation for the episode.

        Raises:
            RuntimeError: If we fail to get the initial observation.
            asyncio.TimeoutError: If the environment setup times out.
        """

        if not self._is_setup:
            logger.warning(
                "reset() called on un-setup environment. Setting up..."
            )
            try:
                # add timeout control
                await asyncio.wait_for(
                    self.setup(),
                    timeout=self._timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Environment setup timed out after {self._timeout}s")
                raise
            
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
            asyncio.TimeoutError: If the step operation times out.
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

        # Initialize info dictionary
        info = {}

        # Update the environment state based on the action
        update_timed_out = False
        try:
            await asyncio.wait_for(
                self._update_state(action),
                timeout=self._timeout
            )
        except asyncio.TimeoutError:
            update_timed_out = True
            logger.error(f"State update timed out after {self._timeout}s")
            # Don't raise, continue with error handling

        # If update timed out, return error information
        if update_timed_out:
            return StepResult(
                observation=self._last_observation,  # Use last observation
                reward=0.0,  # Default reward
                rewards_dict={},  # No rewards on timeout
                done=False,  # Episode not done
                info={"error": f"State update timed out after {self._timeout}s"}
            ).as_tuple()
        
        # Compute rewards
        try:
            total_reward, rewards_dict = await asyncio.wait_for(
                self.compute_reward(),
                timeout=self._timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Reward computation timed out after {self._timeout}s")
            # raise exception to terminate the step operation
            total_reward = 0.0
            rewards_dict = {}
            info["error"] = f"Reward computation timed out after {self._timeout}s"

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


        extraction_result = None
        try:
            extraction_result = await asyncio.wait_for(
                self.extractor.extract(action.llm_response),
                timeout=self._timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Extraction timed out after {self._timeout}s")
            # Don't raise, use default values instead
            extraction_result = None
            if info is None:
                info = {}
            info["error"] = f"Extraction timed out after {self._timeout}s"
        
        # If we have no info dict yet (no errors occurred), create one
        if info is None:
            info = {}
        
        # Add extraction result to info if available and no error occurred
        if "error" not in info and extraction_result is not None:
            info["extraction_result"] = extraction_result
            
        # Add step and state info
        info["step"] = self._current_step
        info["state"] = self._state  # Updated state

        return StepResult(
            observation=next_obs,
            reward=total_reward,
            rewards_dict=rewards_dict,
            done=done,
            info=info,
        ).as_tuple()

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
