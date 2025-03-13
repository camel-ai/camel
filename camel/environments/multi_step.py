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
from typing import Any, Dict, List, Optional, Tuple

from camel.environments.base import BaseEnvironment
from camel.extractors.base import BaseExtractor
from camel.logger import get_logger
from .models import Action, Observation, StepResult

logger = get_logger(__name__)

class MultiStepEnv(BaseEnvironment):
    r"""Base class for developing Multi-Step environments for RL with LLMs.
    """
    
    def __init__(
        self,
        extractor: BaseExtractor,
        max_steps: Optional[int] = None,
        **kwargs,
    ) -> None:
        r"""Initialize the environment.

        Args:
            dataset: Dataset to sample questions from.
            verifier: Verifier to check responses.
            extractor: Extractor to process LLM responses.
            max_steps: Maximum steps per episode.
            teacher_agent: Optional agent for reward shaping and hints
            curriculum_config: Configuration for curriculum learning including:
                - difficulty_levels: List of available difficulty levels
                - promotion_threshold: Score needed to advance
                - demotion_threshold: Score triggering level decrease
                - min_questions_per_level: Questions before promotion
            practice_env_config: Configuration for practice environments:
                - max_practice_envs: Maximum concurrent environments
                - difficulty_range: Allowed difficulty variation
                - focus_areas: Specific skills to practice
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
        r"""Set up the environment"""
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
    
    @abstractmethod
    async def _setup(self) -> None:
        pass

    async def close(self) -> None:
        r"""Clean up resources, including verifier teardown."""
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
    
    @abstractmethod
    async def _close(self) -> None:
        pass

    async def reset(self) -> Observation:
        r"""Reset the environment to an initial state.

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

    async def step(self, action: Action) -> StepResult:
        r"""Take a step in the environment.

        Args:
            action: Action containing everything that is needed
            to progress in the environment

        Returns:
            StepResult containing next observation, reward, done flag, and info
        """
        if self.max_steps and self._current_step >= self.max_steps:
            return StepResult(
                observation=self._get_terminal_observation(),
                reward=0,
                rewards_dict={},
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
        self._episode_history.append((current_obs, action))

        # extract relevant part from llm response
        extraction_result = await self.extractor.extract(action.llm_response)

        if not extraction_result:
            extraction_result = ""

        # compute rewards
        total_reward, rewards_dict = await self.compute_reward(
            action, extraction_result
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
            reward=total_reward,
            rewards_dict=rewards_dict,
            done=done,
            info={
                "extraction_result": extraction_result,
                "step": self._current_step,
                "state": self._state,
            },
        )

    @abstractmethod
    def _get_initial_state(self) -> Dict[str, Any]:
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
        action: Action,
        extraction_result: str,
    ) -> Tuple[float, Dict[str, float]]:
        pass

    def _is_done(self) -> bool:
        r"""Check if episode should terminate."""
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