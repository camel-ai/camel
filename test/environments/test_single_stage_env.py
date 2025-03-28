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
import re
from typing import Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from camel.datasets import StaticDataset
from camel.environments import (
    Action,
    Observation,
    StepResult,
)
from camel.environments.single_step import SingleStepEnv
from camel.verifiers.models import VerificationOutcome, VerificationResult


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
            "metadata": {"difficulty": "easy"},
        },
        {
            "question": "What is the capital of France?",
            "final_answer": "Paris",
            "rationale": "Paris is known as the capital city of France.",
            "metadata": {"difficulty": "easy"},
        },
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
    assert observation.question in [
        "What is 2 + 2?",
        "What is the capital of France?",
    ]

    # Test step
    action = Action(llm_response="Test response")
    result = await env.step(action)
    assert isinstance(result, StepResult)
    assert result.reward == 10.5  # correctness: 10.0 + custom_reward: 0.5
    assert result.done is True
    assert result.observation == SingleStepEnv.PLACEHOLDER_OBS
    mock_extractor.extract.assert_awaited_once_with("Test response")
    mock_verifier.verify.assert_awaited_once()

    # Test close
    await env.close()
    assert env._is_setup is False
    mock_verifier.cleanup.assert_awaited_once()
    mock_extractor.cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_single_step_env_error_handling():
    # **1. Test Faulty Dataset**
    faulty_data = [
        {
            "question": "What is 2 + 2?",
            # Missing "final_answer"
            "rationale": "Adding 2 and 2 gives 4.",
            "metadata": {"difficulty": "easy"},
        },
        {
            "question": "What is the capital of France?",
            "final_answer": "Paris",
            "rationale": "Paris is known as the capital city of France.",
            "metadata": {"difficulty": "easy"},
        },
    ]
    try:
        StaticDataset(faulty_data)
    except Exception as e:
        assert isinstance(
            e, ValueError
        ), "Expected ValueError for faulty dataset"

    # **Valid Dataset for Subsequent Tests**
    valid_data = [
        {
            "question": "What is 2 + 2?",
            "final_answer": "4",
            "rationale": "Adding 2 and 2 gives 4.",
            "metadata": {"difficulty": "easy"},
        },
        {
            "question": "What is the capital of France?",
            "final_answer": "Paris",
            "rationale": "Paris is known as the capital city of France.",
            "metadata": {"difficulty": "easy"},
        },
    ]
    dataset = StaticDataset(valid_data)

    # **2. Test Faulty Extractor**
    # Mock verifier that fails verification
    mock_verifier_fail = MagicMock()
    mock_verifier_fail.setup = AsyncMock()
    mock_verifier_fail.cleanup = AsyncMock()
    mock_verifier_fail.verify = AsyncMock(
        return_value=VerificationResult(
            status=VerificationOutcome.FAILURE,
            result="Verification failed",
            feedback="Incorrect",
            score=0.0,
        )
    )
    # Mock extractor that returns None (extraction failure)
    mock_extractor_fail = MagicMock()
    mock_extractor_fail.setup = AsyncMock()
    mock_extractor_fail.cleanup = AsyncMock()
    mock_extractor_fail.extract = AsyncMock(return_value=None)

    env_fail_extractor = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier_fail,
        extractor=mock_extractor_fail,
    )
    await env_fail_extractor.setup()
    observation = await env_fail_extractor.reset()
    assert isinstance(
        observation, Observation
    ), "Reset should still return an Observation"

    action = Action(llm_response="Test response")
    with pytest.raises(RuntimeError, match="Couldn't extract from"):
        await env_fail_extractor.step(action)

    # **3. Test Faulty Verifier**
    # Mock verifier that raises an exception
    mock_verifier_exception = MagicMock()
    mock_verifier_exception.setup = AsyncMock()
    mock_verifier_exception.cleanup = AsyncMock()
    mock_verifier_exception.verify = AsyncMock(
        side_effect=Exception("Verifier error")
    )
    # Valid extractor
    mock_extractor = MagicMock()
    mock_extractor.setup = AsyncMock()
    mock_extractor.cleanup = AsyncMock()
    mock_extractor.extract = AsyncMock(return_value="extracted_answer")

    env_fail_verifier = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier_exception,
        extractor=mock_extractor,
    )
    await env_fail_verifier.setup()
    observation = await env_fail_verifier.reset()
    assert isinstance(
        observation, Observation
    ), "Reset should still return an Observation"

    with pytest.raises(Exception, match="Verifier error"):
        await env_fail_verifier.step(action)

    # **4. Test State Mismanagement Scenarios**
    # a) Environment not set up
    env_not_setup = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier_fail,
        extractor=mock_extractor,
    )
    with pytest.raises(
        RuntimeError,
        match=re.escape("Environment not set up. Call setup() first."),
    ):
        await env_not_setup.step(action)

    # b) Episode ended
    env_episode_ended = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier_fail,
        extractor=mock_extractor,
    )
    await env_episode_ended.setup()
    await env_episode_ended.reset()
    env_episode_ended._episode_ended = True
    with pytest.raises(
        RuntimeError,
        match=re.escape("Episode has ended. " "Call reset() first."),
    ):
        await env_episode_ended.step(action)

    # c) No current observation
    env_no_state = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier_fail,
        extractor=mock_extractor,
    )
    await env_no_state.setup()
    env_no_state._state = None
    with pytest.raises(
        RuntimeError,
        match=re.escape("No current observation. Call reset() first."),
    ):
        await env_no_state.step(action)
