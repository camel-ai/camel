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

from typing import Any, Dict, Optional, Tuple

from camel.agents import ChatAgent
from camel.datasets.base import BaseDataset, DataPoint
from camel.environments.base import (
    Action,
    BaseEnvironment,
    Observation,
    StepResult,
)
from camel.extractors.base import BaseExtractor
from camel.logger import get_logger
from camel.verifiers.base import BaseVerifier
from camel.verifiers.models import VerificationResult, VerifierInput

logger = get_logger(__name__)


class MedicalEnvironment(BaseEnvironment):
    r"""Environment for medical diagnosis tasks.

    This environment is designed for medical diagnosis tasks where an LLM
    agent is presented with a medical case and must provide a diagnosis.
    The environment includes a reward function that rewards correct diagnoses
    and penalizes incorrect ones.
    """

    def __init__(
        self,
        dataset: BaseDataset,
        verifier: BaseVerifier,
        extractor: BaseExtractor,
        max_steps: Optional[int] = None,
        teacher_agent: Optional[ChatAgent] = None,
        reward_correct: float = 1.0,
        reward_incorrect: float = -0.5,
        reward_no_answer: float = -0.2,
        **kwargs,
    ) -> None:
        r"""Initialize the medical environment.

        Args:
            dataset (BaseDataset): Dataset containing medical cases.
            verifier (BaseVerifier): Verifier for checking diagnoses.
            extractor (BaseExtractor): Extractor for extracting diagnoses.
            max_steps (Optional[int]): Maximum number of steps per episode.
            teacher_agent (Optional[ChatAgent]): Teacher agent for guidance.
            reward_correct (float): Reward for correct diagnosis.
            reward_incorrect (float): Reward for incorrect diagnosis.
            reward_no_answer (float): Reward when no diagnosis is provided.
            **kwargs: Additional environment parameters.
        """
        super().__init__(
            dataset=dataset,
            verifier=verifier,
            extractor=extractor,
            max_steps=max_steps,
            teacher_agent=teacher_agent,
            **kwargs,
        )
        self.reward_correct = reward_correct
        self.reward_incorrect = reward_incorrect
        self.reward_no_answer = reward_no_answer
        self._current_data_point: Optional[DataPoint] = None
        self._current_step: int = 0

    async def setup(self) -> None:
        r"""Set up the environment."""
        await super().setup()
        # Additional setup specific to medical environment
        logger.info("Medical environment setup complete")

    async def teardown(self) -> None:
        r"""Clean up the environment."""
        await super().teardown()
        # Additional teardown specific to medical environment
        logger.info("Medical environment teardown complete")

    async def reset(self) -> Observation:
        r"""Reset the environment and get a new medical case.

        Returns:
            Observation: The initial observation containing a medical case.
        """
        # Reset environment state
        self._current_step = 0

        # Sample a random data point from the dataset
        data_point = self.dataset.sample()
        if not isinstance(data_point, DataPoint):
            raise ValueError("Dataset sample must return a DataPoint")
        self._current_data_point = data_point

        # Create initial observation
        observation = Observation(
            question=self._current_data_point.question,
            context={
                "difficulty": self._current_data_point.difficulty,
                "metadata": self._current_data_point.metadata,
            },
        )

        logger.info("Environment reset with new medical case")
        return observation

    async def step(self, action: Action) -> StepResult:
        r"""Take a step in the environment.

        Args:
            action (Action): The action containing the LLM's diagnosis.

        Returns:
            StepResult: The result of the step, including reward and next
                observation.
        """
        if self._current_data_point is None:
            raise RuntimeError("Environment must be reset before stepping")

        self._current_step += 1

        # Extract the diagnosis from the LLM response
        extracted_diagnosis = await self.extractor.extract(action.llm_response)

        # Verify the diagnosis against the ground truth
        verification_result = await self.verifier.verify(
            VerifierInput(
                llm_response=extracted_diagnosis,
                ground_truth=self._current_data_point.final_answer,
            )
        )

        # Compute reward based on verification result
        total_reward, rewards_dict = await self.compute_reward(
            action, extracted_diagnosis, verification_result
        )

        # Check if episode is done
        done = self._is_done()

        # Get next observation or terminal observation
        if done:
            observation = self._get_terminal_observation()
        else:
            observation = self._get_next_observation()

        return StepResult(
            observation=observation,
            reward=total_reward,
            rewards_dict=rewards_dict,
            done=done,
            info={
                "extracted_diagnosis": extracted_diagnosis,
                "verification_result": verification_result,
                "current_step": self._current_step,
            },
        )

    def _get_initial_state(self) -> Dict[str, Any]:
        r"""Get the initial state of the environment.

        Returns:
            Dict[str, Any]: The initial state.
        """
        return {
            "current_step": 0,
            "current_data_point": None,
        }

    def _get_next_observation(self) -> Observation:
        r"""Get the next observation.

        Returns:
            Observation: The next observation.
        """
        if self._current_data_point is None:
            raise RuntimeError(
                """Environment must be reset
                 before getting next observation"""
            )
        return Observation(
            question=self._current_data_point.question,
            context={
                "difficulty": self._current_data_point.difficulty,
                "metadata": self._current_data_point.metadata,
            },
        )

    def _get_terminal_observation(self) -> Observation:
        r"""Get the terminal observation.

        Returns:
            Observation: The terminal observation.
        """
        if self._current_data_point is None:
            raise RuntimeError(
                "Environment must be reset before getting terminal observation"
            )

        return Observation(
            question=self._current_data_point.question,
            context={
                "difficulty": self._current_data_point.difficulty,
                "metadata": self._current_data_point.metadata,
                "final_answer": self._current_data_point.final_answer,
                "rationale": self._current_data_point.rationale,
            },
        )

    async def compute_reward(
        self,
        action: Action,
        extraction_result: str,
        verification_result: VerificationResult,
    ) -> Tuple[float, Dict[str, float]]:
        r"""Compute the reward for the current step.

        Args:
            action (Action): The action taken.
            extraction_result (str): The extracted diagnosis.
            verification_result (VerificationResult): The verification result.

        Returns:
            Tuple[float, Dict[str, float]]: The total reward and a dictionary
                of individual reward components.
        """
        rewards_dict = await self._compute_reward(
            action, extraction_result, verification_result
        )
        total_reward = sum(rewards_dict.values())
        return total_reward, rewards_dict

    async def _compute_reward(
        self,
        action: Action,
        extraction_result: str,
        verification_result: VerificationResult,
    ) -> Dict[str, float]:
        r"""Compute the individual reward components.

        Args:
            action (Action): The action taken.
            extraction_result (str): The extracted diagnosis.
            verification_result (VerificationResult): The verification result.

        Returns:
            Dict[str, float]: Dictionary of reward components.
        """
        if self._current_data_point is None:
            raise RuntimeError(
                "Environment must be reset before computing reward"
            )

        rewards = {}

        # Reward for providing a diagnosis
        if not extraction_result:
            rewards["diagnosis_provided"] = self.reward_no_answer
            logger.warning("No diagnosis extracted from response")
        else:
            # Reward based on verification outcome
            if verification_result.status.value == "success":
                rewards["diagnosis_accuracy"] = self.reward_correct
                logger.info(f"Correct diagnosis: {extraction_result}")
            else:
                rewards["diagnosis_accuracy"] = self.reward_incorrect
                logger.warning(
                    f"Incorrect diagnosis: {extraction_result}, "
                    f"Expected: {self._current_data_point.final_answer}"
                )

        return rewards

    def _is_done(self) -> bool:
        r"""Check if the episode is done.

        Returns:
            bool: True if the episode is done, False otherwise.
        """
        # Episode is done after one step or if max_steps is reached
        return self._current_step >= 1 or (
            self.max_steps is not None and self._current_step >= self.max_steps
        )

    @property
    def current_step(self) -> int:
        r"""Get the current step.

        Returns:
            int: The current step.
        """
        return self._current_step
