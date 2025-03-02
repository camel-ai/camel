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

from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime

from .base import BaseEnvironment, Observation, StepResult
from camel.verifiers.models import Response, TaskType, VerificationStatus
from camel.verifiers.medicine import MedicalVerifier
from camel.extractors.medicine import MedicineExtractor


class MedicalEnvironment(BaseEnvironment):
    """Medical domain specific environment for training and evaluation.

    This environment specializes in medical tasks with features like:
    1. Medical case complexity tracking
    2. Evidence-based practice validation
    3. Clinical guideline compliance checking
    4. Medical terminology accuracy assessment
    5. Treatment safety verification
    6. Diagnostic reasoning evaluation
    """

    def __init__(
        self,
        dataset: 'MedicalDataset',  # Forward reference
        verifier: Optional[MedicalVerifier] = None,
        extractor: Optional[MedicineExtractor] = None,
        max_steps: Optional[int] = None,
        required_fields: Optional[Set[str]] = None,
        min_confidence_score: float = 0.7,
        curriculum_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Initialize the medical environment.

        Args:
            dataset: Dataset containing medical cases
            verifier: Medical domain verifier (created if None)
            extractor: Medical content extractor (created if None)
            max_steps: Maximum steps per episode
            required_fields: Required fields in medical responses
            min_confidence_score: Minimum confidence threshold
            curriculum_config: Curriculum learning configuration
            **kwargs: Additional environment parameters
        """
        # Create default components if not provided
        verifier = verifier or MedicalVerifier(
            required_fields=required_fields,
            min_confidence_score=min_confidence_score,
        )
        extractor = extractor or MedicineExtractor()

        super().__init__(
            dataset=dataset,
            verifier=verifier,
            extractor=extractor,
            max_steps=max_steps,
            task_type=TaskType.MEDICINE,
            curriculum_config=curriculum_config,
            **kwargs,
        )

        self._required_fields = required_fields or {
            'symptoms',
            'diagnosis',
            'treatment',
            'icd_codes',
        }
        self._min_confidence = min_confidence_score

    def _get_initial_state(self) -> Dict[str, Any]:
        """Initialize environment state.

        Returns:
            Dict containing initial state variables
        """
        return {
            'current_case_id': None,
            'case_difficulty': 'moderate',
            'attempts': 0,
            'correct_diagnoses': 0,
            'treatment_compliance': 0.0,
            'safety_score': 1.0,
            'evidence_score': 0.0,
        }

    def _get_terminal_observation(self) -> Observation:
        """Get observation for terminal state.

        Returns:
            Terminal observation with performance summary
        """
        return Observation(
            question="Episode complete",
            context={
                'performance_summary': {
                    'correct_diagnoses': self._state['correct_diagnoses'],
                    'treatment_compliance': self._state['treatment_compliance'],
                    'safety_score': self._state['safety_score'],
                    'evidence_score': self._state['evidence_score'],
                }
            },
            metadata={
                'is_terminal': True,
                'timestamp': datetime.now(),
            }
        )

    def _get_next_observation(self) -> Optional[Observation]:
        """Get next medical case observation.

        Returns:
            Next observation or None if no more cases
        """
        try:
            case = self.dataset.get_next_case(
                difficulty=self._state['case_difficulty']
            )
            if case is None:
                return None

            self._state['current_case_id'] = case.id
            return Observation(
                question=case.description,
                context={
                    'patient_history': case.history,
                    'vital_signs': case.vitals,
                    'lab_results': case.labs,
                    'imaging': case.imaging,
                },
                metadata={
                    'difficulty': case.difficulty,
                    'specialty': case.specialty,
                    'urgency': case.urgency,
                }
            )
        except Exception as e:
            logger.error(f"Failed to get next observation: {e}")
            return None

    def _calculate_rewards(
        self,
        extraction_result: Dict[str, Any],
        verification_result: 'VerificationResult',
    ) -> Dict[str, float]:
        """Calculate rewards for the current step.

        Args:
            extraction_result: Extracted medical content
            verification_result: Verification results

        Returns:
            Dictionary of reward components
        """
        rewards = {
            'base': 0.0,
            'diagnostic': 0.0,
            'treatment': 0.0,
            'safety': 0.0,
            'evidence': 0.0,
        }

        # Base reward for valid response
        if verification_result.status == VerificationStatus.SUCCESS:
            rewards['base'] = 1.0

        # Diagnostic accuracy reward
        if extraction_result.get('final_answer'):
            diagnostic_score = verification_result.metadata.get(
                'confidence_score', 0
            )
            rewards['diagnostic'] = diagnostic_score

        # Treatment compliance reward
        for validation in verification_result.metadata.get('validations', []):
            if validation['type'] == 'treatment_protocol':
                protocol = validation.get('validation', {})
                if protocol.get('compliant', False):
                    rewards['treatment'] = protocol.get('confidence', 0)

        # Safety penalty for drug interactions
        interactions = [
            v for v in verification_result.metadata.get('validations', [])
            if v['type'] == 'drug_interactions'
        ]
        if interactions:
            rewards['safety'] = -0.5 * len(interactions)

        # Evidence-based practice reward
        if extraction_result.get('chain_of_thought'):
            rewards['evidence'] = 0.5

        return rewards

    async def setup(self) -> None:
        """Set up the medical environment."""
        await super().setup()
        # Additional medical-specific setup could be added here

    async def teardown(self) -> None:
        """Clean up the medical environment."""
        await super().teardown()
        # Additional medical-specific cleanup could be added here

    async def reset(self) -> Observation:
        """Reset the medical environment.

        Returns:
            Initial medical case observation
        """
        return await super().reset()

    async def step(self, response: Response) -> StepResult:
        """Take a step in the medical environment.

        Args:
            response: Response containing medical assessment

        Returns:
            StepResult with next case, rewards, completion status, and info
        """
        if self._episode_ended:
            return StepResult(
                observation=self._get_terminal_observation(),
                reward={},
                done=True,
                info={'error': 'Episode already ended'},
            )

        self._current_step += 1
        self._state['attempts'] += 1

        # Process response
        extraction_result, verification_result = await self.process_response(
            response
        )

        # Update state based on results
        if verification_result.status == VerificationStatus.SUCCESS:
            self._state['correct_diagnoses'] += 1
            self._state['treatment_compliance'] = (
                self._state['treatment_compliance'] * 0.9 +
                verification_result.metadata.get('confidence_score', 0) * 0.1
            )

        # Calculate rewards
        rewards = self._calculate_rewards(extraction_result, verification_result)

        # Check episode termination
        done = (
            self.max_steps and self._current_step >= self.max_steps
        )
        self._episode_ended = done

        # Get next observation
        next_observation = (
            self._get_terminal_observation() if done
            else self._get_next_observation()
        )

        if next_observation is None:
            done = True
            self._episode_ended = True
            next_observation = self._get_terminal_observation()

        return StepResult(
            observation=next_observation,
            reward=rewards,
            done=done,
            info={
                'extraction_result': extraction_result,
                'verification_result': verification_result.dict(),
                'current_state': self._state.copy(),
            }
        )

    def compute_reward(
        self,
        response: Response,
        extraction_result: Dict[str, Any],
        verification_result: 'VerificationResult',
    ) -> Dict[str, float]:
        """Compute reward for the current step.

        Args:
            response: The agent's response
            extraction_result: Extracted medical content
            verification_result: Verification results

        Returns:
            Dictionary of reward components
        """
        rewards = {
            'base': 0.0,
            'diagnostic': 0.0,
            'treatment': 0.0,
            'safety': 0.0,
            'evidence': 0.0,
        }

        # Base reward for valid response
        if verification_result.status == VerificationStatus.SUCCESS:
            rewards['base'] = 1.0

        # Diagnostic accuracy reward
        if extraction_result.get('final_answer'):
            diagnostic_score = verification_result.metadata.get(
                'confidence_score', 0
            )
            rewards['diagnostic'] = diagnostic_score

        # Treatment compliance reward
        for validation in verification_result.metadata.get('validations', []):
            if validation['type'] == 'treatment_protocol':
                protocol = validation.get('validation', {})
                if protocol.get('compliant', False):
                    rewards['treatment'] = protocol.get('confidence', 0)

        # Safety penalty for drug interactions
        interactions = [
            v for v in verification_result.metadata.get('validations', [])
            if v['type'] == 'drug_interactions'
        ]
        if interactions:
            rewards['safety'] = -0.5 * len(interactions)

        # Evidence-based practice reward
        if extraction_result.get('chain_of_thought'):
            rewards['evidence'] = 0.5

        return rewards 