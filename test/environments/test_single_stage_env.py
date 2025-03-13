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
from datetime import datetime, timezone
from typing import Dict, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest

from camel.environments.base import (
    Action,
    BaseEnvironment,
    Observation,
    StepResult,
)
from camel.environments.single_step import SingleStepEnv
from camel.verifiers.models import VerificationOutcome, VerificationResult
from camel.datasets import StaticDataset
from unittest.mock import MagicMock, AsyncMock
from camel.verifiers.models import VerificationResult, VerificationOutcome


class MockSingleStepEnv(SingleStepEnv):
    async def _compute_custom_reward(
        self,
        action: Action,
        extraction_result: str,
        verification_result: VerificationResult,
    ) -> Dict[str, float]:
        return {"custom_reward": 0.5}

@pytest.mark.asyncio
async def test_single_step_env_lifecycle():
    # Define dataset
    data = [
        {
            "question": "What is 2 + 2?",
            "final_answer": "4",
            "rationale": "Adding 2 and 2 gives 4.",
            "metadata": {"difficulty": "easy"}
        },
        {
            "question": "What is the capital of France?",
            "final_answer": "Paris",
            "rationale": "Paris is known as the capital city of France.",
            "metadata": {"difficulty": "easy"}
        }
    ]
    dataset = StaticDataset(data)

    # Define mock verifier
    mock_verifier = MagicMock()
    mock_verifier.setup = AsyncMock()
    mock_verifier.cleanup = AsyncMock()
    mock_verifier.verify = AsyncMock(
        return_value=VerificationResult(
            status=VerificationOutcome.SUCCESS,
            result="Verification successful",
            feedback="Correct",
            score=1.0,
        )
    )

    # Define mock extractor
    mock_extractor = MagicMock()
    mock_extractor.setup = AsyncMock()
    mock_extractor.cleanup = AsyncMock()
    mock_extractor.extract = AsyncMock(return_value="extracted_answer")

    # Initialize the environment with mocked dependencies
    env = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier,
        extractor=mock_extractor,
    )

    # Test setup
    await env.setup()
    assert env._is_setup is True
    mock_verifier.setup.assert_awaited_once()
    mock_extractor.setup.assert_awaited_once()

    # Test reset
    observation = await env.reset()
    assert isinstance(observation, Observation)
    assert observation.question in ["What is 2 + 2?", "What is the capital of France?"]

    # Test step
    action = Action(llm_response="Test response")
    result = await env.step(action)
    assert isinstance(result, StepResult)
    assert result.reward == 1.5  # correctness: 1.0 + custom_reward: 0.5
    assert result.done is True
    assert result.observation == SingleStepEnv.PLACEHOLDER_OBS
    mock_extractor.extract.assert_awaited_once_with("Test response")
    mock_verifier.verify.assert_awaited_once()

    # Test close
    await env.close()
    assert env._is_setup is False
    mock_verifier.cleanup.assert_awaited_once()
    mock_extractor.cleanup.assert_awaited_once()