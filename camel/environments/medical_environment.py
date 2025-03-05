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
    and penalizes incorrect ones. It also implements a retry mechanism for
    quality control.

    Attributes:
        reward_correct (float): Reward value for correct diagnosis.
        reward_incorrect (float): Penalty value for incorrect diagnosis.
        reward_no_answer (float): Penalty value when no diagnosis is provided.
        max_retries (int): Maximum number of retry attempts allowed.
        quality_threshold (float): Minimum reward threshold for
        sacceptable quality.
        retry_delay (float): Delay between retry attempts in seconds.
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
        max_retries: int = 3,
        quality_threshold: float = 0.7,
        retry_delay: float = 1.0,
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
            max_retries (int): Maximum number of retry attempts.
            quality_threshold (float): Minimum reward threshold for quality.
            retry_delay (float): Delay between retries in seconds.
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
        self.max_retries = max_retries
        self.quality_threshold = quality_threshold
        self.retry_delay = retry_delay
        self._current_data_point: Optional[DataPoint] = None
        self._retry_count: int = 0
        self._best_result: Optional[Tuple[float, str, VerificationResult]] = (
            None
        )

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
        self._current_step = 0
        self._retry_count = 0
        self._best_result = None

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
        r"""Take a step in the environment with retry mechanism.

        This implementation extends the base step method
        to include quality-based retries and tracking of best results.

        Args:
            action (Action): The action containing the LLM's diagnosis.

        Returns:
            StepResult: The result of the step, including reward and next
                observation, with additional retry-related information.
        """
        if self._current_data_point is None:
            raise RuntimeError("Environment must be reset before stepping")

        self._current_step += 1

        # Extract and verify the diagnosis
        extracted_diagnosis = await self.extractor.extract(action.llm_response)
        verification_result = await self.verifier.verify(
            VerifierInput(
                llm_response=extracted_diagnosis,
                ground_truth=self._current_data_point.final_answer,
            )
        )

        # Compute reward
        total_reward, rewards_dict = await self.compute_reward(
            action, extracted_diagnosis, verification_result
        )

        # Update best result
        if self._best_result is None or total_reward > self._best_result[0]:
            self._best_result = (
                total_reward,
                extracted_diagnosis,
                verification_result,
            )

        # Update state
        self._state["retry_history"].append(
            {
                "reward": total_reward,
                "diagnosis": extracted_diagnosis,
                "retry_count": self._retry_count,
            }
        )

        if self._state["initial_reward"] is None:
            self._state["initial_reward"] = total_reward
        self._state["best_reward"] = self._best_result[0]

        # Check retry conditions
        should_retry = await self._should_retry(
            total_reward, verification_result
        )
        if should_retry and self._retry_count < self.max_retries:
            self._retry_count += 1
            self._state["retry_count"] = self._retry_count
            return StepResult(
                observation=self._get_retry_observation(
                    total_reward, verification_result
                ),
                reward=total_reward,
                rewards_dict=rewards_dict,
                done=False,
                info={
                    "extracted_diagnosis": extracted_diagnosis,
                    "verification_result": verification_result,
                    "current_step": self._current_step,
                    "retry_count": self._retry_count,
                    "is_retry": True,
                    "best_result": self._best_result,
                },
            )

        # Return final result using best outcome
        done = self._is_done()
        observation = (
            self._get_terminal_observation()
            if done
            else self._get_next_observation()
        )

        return StepResult(
            observation=observation,
            reward=self._best_result[0],
            rewards_dict=rewards_dict,
            done=done,
            info={
                "extracted_diagnosis": self._best_result[1],
                "verification_result": self._best_result[2],
                "current_step": self._current_step,
                "retry_count": self._retry_count,
                "is_retry": False,
                "retry_history": self._state["retry_history"],
            },
        )

    def _get_initial_state(self) -> Dict[str, Any]:
        r"""Get initial environment state.

        Returns:
            Dict[str, Any]: Initial state dictionary containing retry-related
                information and basic state from parent class.
        """
        initial_state = super()._get_initial_state()
        initial_state.update(
            {
                "retry_count": 0,
                "best_reward": None,
                "initial_reward": None,
                "retry_history": [],
            }
        )
        return initial_state

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
            Dict[str, float]: Dictionary of reward components
                including diagnosis accuracy and completeness.
        """
        rewards = {}

        # Basic diagnosis presence check
        if not extraction_result:
            rewards["diagnosis_provided"] = self.reward_no_answer
            logger.warning("No diagnosis extracted from response")
            return rewards

        # Accuracy reward based on verification
        rewards["diagnosis_accuracy"] = (
            self.reward_correct
            if verification_result.status.value == "success"
            else self.reward_incorrect
        )

        # Additional reward components can be added here
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

    async def _should_retry(
        self,
        reward: float,
        verification_result: VerificationResult,
    ) -> bool:
        r"""Determine if a retry attempt should be made.

        Args:
            reward (float): Current reward value.
            verification_result (VerificationResult): Result of verification.

        Returns:
            bool: True if a retry should be attempted, False otherwise.
        """
        if reward >= self.quality_threshold:
            return False

        if self._retry_count >= self.max_retries:
            return False

        # Consider verification result confidence
        if hasattr(verification_result, "confidence"):
            if verification_result.confidence > 0.8:
                return False

        return True

    def _get_retry_observation(
        self,
        reward: float,
        verification_result: VerificationResult,
    ) -> Observation:
        r"""Generate observation for retry attempt.

        Args:
            reward (float): Current reward value.
            verification_result (VerificationResult): Result of verification.

        Returns:
            Observation: Observation object with retry-specific feedback.
        """
        if self._current_data_point is None:
            raise RuntimeError(
                "Environment must be reset before getting retry observation"
            )

        # Construct verification feedback based on available information
        verification_feedback = {
            "status": verification_result.status.value,
            "message": f"""Previous diagnosis 
            was {'correct' if verification_result.status.value 
                 == 'success' else 'incorrect'}""",
            "expected": self._current_data_point.final_answer,
        }

        retry_feedback = {
            "retry_count": self._retry_count,
            "previous_reward": reward,
            "quality_threshold": self.quality_threshold,
            "verification_feedback": verification_feedback,
            "best_reward_so_far": self._best_result[0]
            if self._best_result
            else None,
        }

        return Observation(
            question=self._current_data_point.question,
            context={
                "difficulty": self._current_data_point.difficulty,
                "metadata": self._current_data_point.metadata,
                "retry_feedback": retry_feedback,
            },
        )
