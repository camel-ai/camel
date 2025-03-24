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
        proposed_solution: str,
        verification_result: VerificationResult,
    ) -> Dict[str, float]:
        return {"custom_reward": 5}


@pytest.mark.asyncio
async def test_single_step_env_lifecycle():
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
        {
            "question": "Who wrote 'Romeo and Juliet'?",
            "final_answer": "Shakespeare",
            "rationale": "William Shakespeare is the author of 'Romeo and "
            "Juliet'.",
            "metadata": {"difficulty": "medium"},
        },
        {
            "question": "What is the boiling point of water in Celsius?",
            "final_answer": "100",
            "rationale": "Water boils at 100 degrees Celsius at standard "
            "pressure.",
            "metadata": {"difficulty": "easy"},
        },
        {
            "question": "What is the chemical symbol for gold?",
            "final_answer": "Au",
            "rationale": "The chemical symbol for gold is Au, from the Latin "
            "'aurum'.",
            "metadata": {"difficulty": "medium"},
        },
        {
            "question": "How many continents are there?",
            "final_answer": "7",
            "rationale": "There are seven continents: Asia, Africa, North "
            "America, South America, Antarctica, Europe, and Australia.",
            "metadata": {"difficulty": "easy"},
        },
        {
            "question": "What is the largest planet in our solar system?",
            "final_answer": "Jupiter",
            "rationale": "Jupiter is the largest planet, with a diameter of "
            "about 142,984 km.",
            "metadata": {"difficulty": "medium"},
        },
        {
            "question": "Who painted the Mona Lisa?",
            "final_answer": "Leonardo da Vinci",
            "rationale": "Leonardo da Vinci painted the Mona Lisa "
            "between 1503 and 1506.",
            "metadata": {"difficulty": "medium"},
        },
    ]
    dataset = StaticDataset(data)
    mock_verifier = MagicMock()
    mock_verifier.setup = AsyncMock()
    mock_verifier.cleanup = AsyncMock()
    mock_verifier.verify_batch = AsyncMock(
        side_effect=lambda solutions, ground_truths, **kwargs: [
            VerificationResult(
                status=VerificationOutcome.SUCCESS,
                result="Verification successful",
                feedback="Correct",
                score=1.0,
            )
            for _ in solutions
        ]
    )

    env = MockSingleStepEnv(dataset=dataset, verifier=mock_verifier)

    await env.setup()
    assert env._is_setup is True
    mock_verifier.setup.assert_awaited_once()

    # Test reset
    observations = await env.reset(batch_size=4)
    assert isinstance(observations, list)
    assert len(observations) == 4
    for obs in observations:
        assert isinstance(obs, Observation)
        assert obs.question in [dp["question"] for dp in data]

    # Test step with 2 actions
    actions = [
        Action(index=0, llm_response="4"),  # "What is 2 + 2?"
        Action(
            index=2, llm_response="Shakespeare"
        ),  # "Who wrote 'Romeo and Juliet'?"
    ]
    results = await env.step(actions)
    assert isinstance(results, list)
    assert len(results) == 2
    for result in results:
        assert isinstance(result, StepResult)
        assert result.reward == 15
        assert result.done is True
        assert result.observation == MockSingleStepEnv.PLACEHOLDER_OBS

    # Test step with remaining two actions
    actions = [
        Action(
            index=1, llm_response="Paris"
        ),  # "What is the capital of France?"
        Action(
            index=3, llm_response="100"
        ),  # "What is the boiling point of water?"
    ]
    results = await env.step(actions)
    assert isinstance(results, list)
    assert len(results) == 2
    for result in results:
        assert isinstance(result, StepResult)
        assert result.reward == 15
        assert result.done is True
        assert result.observation == MockSingleStepEnv.PLACEHOLDER_OBS

    assert env._batch_done()
    await env.close()
    assert env._is_setup is False
    mock_verifier.cleanup.assert_awaited_once()


def create_mock_verifier():
    verifier = MagicMock()
    verifier.setup = AsyncMock()
    verifier.cleanup = AsyncMock()
    verifier.verify_batch = AsyncMock(
        side_effect=lambda solutions, ground_truths, **kwargs: [
            VerificationResult(
                status=VerificationOutcome.SUCCESS,
                result="Mock verification",
                feedback="Mock feedback",
                score=1.0,
            )
            for _ in solutions
        ]
    )
    return verifier


@pytest.mark.asyncio
async def test_single_step_env_error_handling():
    # **1. Test Faulty Dataset**
    # Ensure we don't silently handle the error
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
    with pytest.raises(ValueError):
        StaticDataset(faulty_data, strict=True)

    # Define valid dataset for subsequent tests
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
        {
            "question": "Who wrote 'Romeo and Juliet'?",
            "final_answer": "Shakespeare",
            "rationale": "William Shakespeare is the author of 'Romeo and "
            "Juliet'.",
            "metadata": {"difficulty": "medium"},
        },
        {
            "question": "What is the boiling point of water in Celsius?",
            "final_answer": "100",
            "rationale": "Water boils at 100 degrees Celsius at standard "
            "pressure.",
            "metadata": {"difficulty": "easy"},
        },
        {
            "question": "What is the chemical symbol for gold?",
            "final_answer": "Au",
            "rationale": "The chemical symbol for gold is Au, from the Latin "
            "'aurum'.",
            "metadata": {"difficulty": "medium"},
        },
        {
            "question": "How many continents are there?",
            "final_answer": "7",
            "rationale": "There are seven continents: Asia, Africa, North "
            "America, South America, Antarctica, Europe, and Australia.",
            "metadata": {"difficulty": "easy"},
        },
        {
            "question": "What is the largest planet in our solar system?",
            "final_answer": "Jupiter",
            "rationale": "Jupiter is the largest planet, with a diameter of "
            "about 142,984 km.",
            "metadata": {"difficulty": "medium"},
        },
        {
            "question": "Who painted the Mona Lisa?",
            "final_answer": "Leonardo da Vinci",
            "rationale": "Leonardo da Vinci painted the Mona Lisa "
            "between 1503 and 1506.",
            "metadata": {"difficulty": "medium"},
        },
    ]
    dataset = StaticDataset(data)

    # **2. Test Faulty Verifier**
    # Ensure errors in verifier are propagated
    mock_verifier_exception = MagicMock()
    mock_verifier_exception.setup = AsyncMock()
    mock_verifier_exception.cleanup = AsyncMock()
    mock_verifier_exception.verify_batch = AsyncMock(
        side_effect=Exception("Verifier error")
    )
    env_fail_verifier = SingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier_exception,
    )
    await env_fail_verifier.setup()
    await env_fail_verifier.reset(batch_size=1)
    action = Action(index=0, llm_response="4")
    with pytest.raises(Exception, match="Verifier error"):
        await env_fail_verifier.step(action)

    # **3. Test State Mismanagement Scenarios**
    # a) Step without setup
    env_not_setup = SingleStepEnv(
        dataset=dataset,
        verifier=create_mock_verifier(),
    )
    with pytest.raises(
        RuntimeError,
        match=re.escape("Environment not set up. Call setup() first."),
    ):
        await env_not_setup.step(Action(index=0, llm_response="4"))

    # b) Step after batch is done
    env_episode_ended = SingleStepEnv(
        dataset=dataset,
        verifier=create_mock_verifier(),
    )
    await env_episode_ended.setup()
    await env_episode_ended.reset(batch_size=1)
    env_episode_ended._states_done = [True]  # Simulate batch completion
    with pytest.raises(
        RuntimeError,
        match=re.escape("Episodes have ended for batch. Call reset() first."),
    ):
        await env_episode_ended.step(Action(index=0, llm_response="4"))

    # c) Step without reset
    env_no_reset = SingleStepEnv(
        dataset=dataset,
        verifier=create_mock_verifier(),
    )
    await env_no_reset.setup()
    with pytest.raises(
        RuntimeError,
        match=re.escape("Episodes have ended for batch. Call reset() first."),
    ):
        await env_no_reset.step(Action(index=0, llm_response="4"))

    # d) Reset before all states processed
    env_partial_batch = SingleStepEnv(
        dataset=dataset,
        verifier=create_mock_verifier(),
    )
    await env_partial_batch.setup()
    await env_partial_batch.reset(batch_size=2)
    await env_partial_batch.step(
        Action(index=0, llm_response="4")
    )  # Process only one state
    with pytest.raises(
        RuntimeError,
        match=re.escape(
            "reset() called before all states in batch were processed."
        ),
    ):
        await env_partial_batch.reset(batch_size=1)

    # **4. Test Invalid Actions**
    env_invalid_actions = SingleStepEnv(
        dataset=dataset,
        verifier=create_mock_verifier(),
    )
    await env_invalid_actions.setup()
    await env_invalid_actions.reset(batch_size=2)

    # a) Action with invalid index (out of range)
    with pytest.raises(ValueError, match="Invalid state index 2."):
        await env_invalid_actions.step(Action(index=2, llm_response="4"))

    # b) Actions with duplicate indices
    with pytest.raises(
        ValueError, match="Duplicate state indices in actions."
    ):
        await env_invalid_actions.step(
            [
                Action(index=0, llm_response="4"),
                Action(index=0, llm_response="Paris"),
            ]
        )

    # c) Action on already finished state
    await env_invalid_actions.step(Action(index=0, llm_response="4"))
    with pytest.raises(
        ValueError, match="State at index 0 is already finished."
    ):
        await env_invalid_actions.step(Action(index=0, llm_response="Paris"))

    # **5. Test Batch Size Issues**
    env_large_batch = SingleStepEnv(
        dataset=dataset,
        verifier=create_mock_verifier(),
    )
    await env_large_batch.setup()
    with pytest.raises(
        ValueError, match="Batch size 9 is too large for dataset of size 8"
    ):
        await env_large_batch.reset(batch_size=9)

    # **6. Test Setup and Close Failures**
    # a) Setup failure
    mock_verifier_setup_fail = MagicMock()
    mock_verifier_setup_fail.setup = AsyncMock(
        side_effect=Exception("Setup failed")
    )
    env_setup_fail = SingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier_setup_fail,
    )
    with pytest.raises(Exception, match="Setup failed"):
        await env_setup_fail.setup()

    # b) Close failure
    mock_verifier_close_fail = MagicMock()
    mock_verifier_close_fail.setup = AsyncMock()
    mock_verifier_close_fail.cleanup = AsyncMock(
        side_effect=Exception("Cleanup failed")
    )
    env_close_fail = SingleStepEnv(
        dataset=dataset,
        verifier=mock_verifier_close_fail,
    )
    await env_close_fail.setup()
    with pytest.raises(Exception, match="Cleanup failed"):
        await env_close_fail.close()
