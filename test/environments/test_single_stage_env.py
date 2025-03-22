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
    # Two steps since both ground_truth and llm result gets extracted
    assert mock_extractor.extract.await_count == 2
    assert any(
        "Test response" in args[0]
        for args in mock_extractor.extract.await_args_list
    )
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
    #env_episode_ended._batch_done = True # FIXME
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


@pytest.mark.asyncio
async def test_single_step_env_batch_operations():
    data = [
        {
            "question": "What is 3 + 5?",
            "final_answer": "8",
            "rationale": "Adding 3 and 5 gives 8.",
            "metadata": {"difficulty": "easy"},
        },
        {
            "question": "What is the capital of Brazil?",
            "final_answer": "Brasilia",
            "rationale": "Brasilia is the capital city of Brazil.",
            "metadata": {"difficulty": "medium"},
        },
        {
            "question": "What is the largest planet?",
            "final_answer": "Jupiter",
            "rationale": "Jupiter is the largest planet in our solar system.",
            "metadata": {"difficulty": "easy"},
        },
        {
            "question": "What is 10 * 2?",
            "final_answer": "20",
            "rationale": "Multiplying 10 by 2 gives 20.",
            "metadata": {"difficulty": "easy"},
        },
    ]
    dataset = StaticDataset(data)

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

    mock_extractor = MagicMock()
    mock_extractor.setup = AsyncMock()
    mock_extractor.cleanup = AsyncMock()
    mock_extractor.extract = AsyncMock(return_value="extracted_answer")

    env = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier,
        extractor=mock_extractor,
    )

    # **1. Test Successful Batch Operation**
    await env.setup()
    observations = await env.reset(batch_size=3)
    assert isinstance(observations, list), "Expected a list of observations"
    assert len(observations) == 3, "Expected 3 observations"
    assert all(
        isinstance(obs, Observation) for obs in observations
    ), "All items should be Observation objects"
    questions = [obs.question for obs in observations]
    assert all(
        q in [d["question"] for d in data] for q in questions
    ), "Questions should match dataset"

    actions = [
        Action(llm_response="Response 1"),
        Action(llm_response="Response 2"),
        Action(llm_response="Response 3"),
    ]
    results = await env.step(actions)
    assert isinstance(results, list), "Expected a list of step results"
    assert len(results) == 3, "Expected 3 step results"
    assert all(
        isinstance(res, StepResult) for res in results
    ), "All items should be StepResult objects"
    assert all(
        res.reward == 10.5 for res in results
    ), "Expected reward 10.5 (10 + 0.5) for each"
    assert all(res.done for res in results), "All steps should be done"
    assert all(
        res.observation == SingleStepEnv.PLACEHOLDER_OBS for res in results
    ), "Expected placeholder observation"
    assert (
        mock_extractor.extract.await_count == 6  # twice per item
    ), "Extractor should be called 6 times"
    assert (
        mock_verifier.verify.await_count == 3
    ), "Verifier should be called 3 times"

    await env.close()
    assert env._is_setup is False
    mock_verifier.cleanup.assert_awaited_once()
    mock_extractor.cleanup.assert_awaited_once()

    # **2. Test Batch Size Too Large**
    env_too_large = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier,
        extractor=mock_extractor,
    )
    await env_too_large.setup()
    with pytest.raises(
        ValueError, match="Batch size 5 is too large for dataset of size 4"
    ):
        await env_too_large.reset(batch_size=5)

    # **3. Test Mismatched Actions**
    await env_too_large.reset(batch_size=3)  # Reset with valid batch size
    mismatched_actions = [
        Action(llm_response="Response 1"),
        Action(llm_response="Response 2"),  # Only 2 actions for batch_size=3
    ]
    with pytest.raises(
        ValueError, match="Number of actions must match number of data points"
    ):
        await env_too_large.step(mismatched_actions)

    # **4. Test Faulty Extractor in Batch**
    mock_extractor_fail = MagicMock()
    mock_extractor_fail.setup = AsyncMock()
    mock_extractor_fail.cleanup = AsyncMock()
    mock_extractor_fail.extract = AsyncMock(
        return_value=None
    )  # Fails extraction

    env_fail_extractor = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier,
        extractor=mock_extractor_fail,
    )
    await env_fail_extractor.setup()
    observations = await env_fail_extractor.reset(batch_size=3)
    assert len(observations) == 3, "Reset should still work"
    actions = [Action(llm_response=f"Response {i}") for i in range(1, 4)]
    with pytest.raises(RuntimeError, match="Couldn't extract from"):
        await env_fail_extractor.step(actions)

    # **5. Test Faulty Verifier in Batch**
    mock_verifier_fail = MagicMock()
    mock_verifier_fail.setup = AsyncMock()
    mock_verifier_fail.cleanup = AsyncMock()
    mock_verifier_fail.verify = AsyncMock(
        side_effect=Exception("Verifier batch error")
    )

    env_fail_verifier = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier_fail,
        extractor=mock_extractor,
    )
    await env_fail_verifier.setup()
    observations = await env_fail_verifier.reset(batch_size=3)
    assert len(observations) == 3, "Reset should still work"
    actions = [Action(llm_response=f"Response {i}") for i in range(1, 4)]
    with pytest.raises(Exception, match="Verifier batch error"):
        await env_fail_verifier.step(actions)

    # **6. Test Mixed Verification Outcomes**
    mock_verifier_mixed = MagicMock()
    mock_verifier_mixed.setup = AsyncMock()
    mock_verifier_mixed.cleanup = AsyncMock()
    mock_verifier_mixed.verify = AsyncMock(
        side_effect=[
            VerificationResult(
                status=VerificationOutcome.SUCCESS,
                result="Success",
                feedback="Correct",
                score=1.0,
            ),
            VerificationResult(
                status=VerificationOutcome.FAILURE,
                result="Failure",
                feedback="Incorrect",
                score=0.0,
            ),
            VerificationResult(
                status=VerificationOutcome.SUCCESS,
                result="Success",
                feedback="Correct",
                score=1.0,
            ),
        ]
    )
    env_mixed = MockSingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier_mixed,
        extractor=mock_extractor,
    )
    await env_mixed.setup()
    observations = await env_mixed.reset(batch_size=3)
    actions = [Action(llm_response=f"Response {i}") for i in range(1, 4)]
    results = await env_mixed.step(actions)
    assert len(results) == 3, "Expected 3 results"
    assert results[0].reward == 10.5, "First should succeed (10 + 0.5)"
    assert results[1].reward == 0.5, "Second should fail (0 + 0.5)"
    assert results[2].reward == 10.5, "Third should succeed (10 + 0.5)"
