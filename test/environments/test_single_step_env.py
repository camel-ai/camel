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
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from camel.datasets import BaseGenerator, DataPoint, StaticDataset
from camel.environments import (
    Action,
    Observation,
)
from camel.environments.single_step import SingleStepEnv
from camel.verifiers.models import VerificationOutcome, VerificationResult

pytestmark = pytest.mark.heavy_dependency


class MockSingleStepEnv(SingleStepEnv):
    async def _compute_custom_reward(
        self,
        proposed_solution: str,
        verification_result: VerificationResult,
    ) -> Dict[str, float]:
        return {"custom_reward": 5}


class MockGenerator(BaseGenerator):
    def __init__(self, predefined_data: List[Dict], *args, **kwargs):
        if 'buffer' not in kwargs:
            kwargs['buffer'] = 1
        super().__init__(*args, **kwargs)
        self.predefined_data = predefined_data
        self.index = 0

    async def generate_new(self, n: int, **kwargs) -> None:
        if self.index + n > len(self.predefined_data):
            raise ValueError("Not enough predefined datapoints")
        new_points = [
            DataPoint(**data)
            for data in self.predefined_data[self.index : self.index + n]
        ]
        self._data.extend(new_points)
        self.index += n


@pytest.mark.asyncio
async def test_single_step_env_lifecycle_single_generator():
    predefined_data = [
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
    dataset = MockGenerator(predefined_data, seed=42)

    mock_verifier = MagicMock()
    mock_verifier.setup = AsyncMock()
    mock_verifier.cleanup = AsyncMock()
    mock_verifier.verify_batch = AsyncMock(
        side_effect=lambda solutions, reference_answers, **kwargs: [
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

    # Test reset with batch_size=1
    observation = await env.reset(batch_size=1)
    assert isinstance(observation, Observation)
    assert observation.question == "What is 2 + 2?"  # First datapoint

    # Test step with a single action
    action = Action(index=0, llm_response="4")
    result = await env.step(action)
    assert isinstance(result, tuple)
    next_obs, reward, done, info = result
    assert next_obs == env.PLACEHOLDER_OBS
    assert reward == env.ACCURACY_REWARD + 5
    assert done is True
    assert info["rewards_dict"].get("custom_reward", None) == 5

    # Test that stepping again without reset fails
    with pytest.raises(
        RuntimeError,
        match=r"Episodes have ended for batch\. Call reset\(\) first\.",
    ):
        await env.step(action)

    # Test reset and step again
    observation2 = await env.reset(batch_size=1)
    assert isinstance(observation2, Observation)
    assert (
        observation2.question == "What is the capital of France?"
    )  # Second datapoint
    action2 = Action(llm_response="Paris")
    result2 = await env.step(action2)
    next_obs2, reward2, done2, info2 = result2
    assert next_obs2 == env.PLACEHOLDER_OBS
    assert reward2 == env.ACCURACY_REWARD + 5
    assert done2 is True
    assert info2["rewards_dict"].get("custom_reward", None) == 5

    # Note: Skipping deterministic sampling test as BaseGenerator
    # doesn't use seed in the same way
    # Test close
    await env.close()
    assert env._is_setup is False
    mock_verifier.cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_single_step_env_lifecycle_single():
    # Define a sample dataset
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

    # Create a mock verifier
    mock_verifier = MagicMock()
    mock_verifier.setup = AsyncMock()
    mock_verifier.cleanup = AsyncMock()
    mock_verifier.verify_batch = AsyncMock(
        side_effect=lambda solutions, reference_answers, **kwargs: [
            VerificationResult(
                status=VerificationOutcome.SUCCESS,
                result="Verification successful",
                feedback="Correct",
                score=1.0,
            )
            for _ in solutions
        ]
    )

    # Initialize the environment
    env = MockSingleStepEnv(dataset=dataset, verifier=mock_verifier)

    # Test setup
    await env.setup()
    assert env._is_setup is True
    mock_verifier.setup.assert_awaited_once()

    # Test reset with batch_size=1
    observation = await env.reset(batch_size=1)
    assert isinstance(
        observation, Observation
    )  # Single Observation, not a list
    assert observation.question in [dp["question"] for dp in data]

    # Test step with a single action (index=0)
    action = Action(index=0, llm_response="4")  # Assuming first question
    result = await env.step(action)
    assert isinstance(result, tuple)  # Single result tuple, not a list
    next_obs, reward, done, info = result
    assert next_obs == env.PLACEHOLDER_OBS
    assert reward == env.ACCURACY_REWARD + 5  # Accuracy + custom reward
    assert done is True  # Single step should end the episode
    assert isinstance(info, dict)
    assert info["rewards_dict"].get("custom_reward", None) == 5

    # Test that stepping again without reset fails
    with pytest.raises(
        RuntimeError,
        match=re.escape("Episodes have ended for batch. Call reset() first."),
    ):
        await env.step(action)

    # Test reset and step again with no index (should default to 0)
    observation2 = await env.reset(batch_size=1)
    assert isinstance(observation2, Observation)
    action2 = Action(llm_response="Paris")  # Assuming second question
    result2 = await env.step(action2)
    next_obs2, reward2, done2, info2 = result2
    assert next_obs2 == env.PLACEHOLDER_OBS
    assert reward2 == env.ACCURACY_REWARD + 5
    assert done2 is True
    assert info2["rewards_dict"].get("custom_reward", None) == 5

    # Test deterministic sampling with seed
    obs1 = await env.reset(batch_size=1, seed=42)
    obs2 = await env.reset(batch_size=1, seed=42)
    assert obs1.question == obs2.question  # Same seed, same question

    # Test close
    await env.close()
    assert env._is_setup is False
    mock_verifier.cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_batched_single_step_env_lifecycle():
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
        side_effect=lambda solutions, reference_answers, **kwargs: [
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
    for next_obs, reward, done, info in results:
        assert next_obs == env.PLACEHOLDER_OBS
        assert reward == env.ACCURACY_REWARD + 5  # 5 is custom reward
        assert done
        assert isinstance(info, dict)
        assert info["rewards_dict"].get("custom_reward", None) == 5

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
    for next_obs, reward, done, info in results:
        assert next_obs == env.PLACEHOLDER_OBS
        assert reward == env.ACCURACY_REWARD + 5  # 5 is custom reward
        assert done
        assert isinstance(info, dict)
        assert info["rewards_dict"].get("custom_reward", None) == 5

    assert env._batch_done()
    await env.close()
    assert env._is_setup is False
    mock_verifier.cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_batched_single_step_env_lifecycle_generator():
    predefined_data = [
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
    ]
    dataset = MockGenerator(predefined_data, seed=42)

    # Create a mock verifier
    mock_verifier = MagicMock()
    mock_verifier.setup = AsyncMock()
    mock_verifier.cleanup = AsyncMock()
    mock_verifier.verify_batch = AsyncMock(
        side_effect=lambda solutions, reference_answers, **kwargs: [
            VerificationResult(
                status=VerificationOutcome.SUCCESS,
                result="Verification successful",
                feedback="Correct",
                score=1.0,
            )
            for _ in solutions
        ]
    )

    # Initialize the environment
    env = MockSingleStepEnv(dataset=dataset, verifier=mock_verifier)

    # Test setup
    await env.setup()
    assert env._is_setup is True
    mock_verifier.setup.assert_awaited_once()

    # Test reset with batch_size=4
    observations = await env.reset(batch_size=4)
    assert isinstance(observations, list)
    assert len(observations) == 4
    expected_questions = [dp["question"] for dp in predefined_data]
    for i, obs in enumerate(observations):
        assert isinstance(obs, Observation)
        assert obs.question == expected_questions[i]

    # Test step with 2 actions
    actions = [
        Action(index=0, llm_response="4"),  # First question
        Action(index=2, llm_response="Shakespeare"),  # Third question
    ]
    results = await env.step(actions)
    assert isinstance(results, list)
    assert len(results) == 2
    for next_obs, reward, done, info in results:
        assert next_obs == env.PLACEHOLDER_OBS
        assert reward == env.ACCURACY_REWARD + 5
        assert done is True
        assert info["rewards_dict"].get("custom_reward", None) == 5

    # Test step with remaining 2 actions
    actions = [
        Action(index=1, llm_response="Paris"),  # Second question
        Action(index=3, llm_response="100"),  # Fourth question
    ]
    results = await env.step(actions)
    assert isinstance(results, list)
    assert len(results) == 2
    for next_obs, reward, done, info in results:
        assert next_obs == env.PLACEHOLDER_OBS
        assert reward == env.ACCURACY_REWARD + 5
        assert done is True
        assert info["rewards_dict"].get("custom_reward", None) == 5

    # Test batch completion
    assert env._batch_done()
    await env.close()
    assert env._is_setup is False
    mock_verifier.cleanup.assert_awaited_once()


def create_mock_verifier():
    verifier = MagicMock()
    verifier.setup = AsyncMock()
    verifier.cleanup = AsyncMock()
    verifier.verify_batch = AsyncMock(
        side_effect=lambda solutions, reference_answers, **kwargs: [
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
async def test_single_step_env_error_handling_single():
    # Define a valid dataset
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

    # **1. Test Faulty Dataset**
    faulty_data = [
        {
            "question": "What is 2 + 2?",
            # Missing "final_answer"
            "rationale": "Adding 2 and 2 gives 4.",
            "metadata": {"difficulty": "easy"},
        },
    ]
    with pytest.raises(ValueError):
        StaticDataset(faulty_data, strict=True)

    # **2. Test Faulty Verifier**
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

    step_result = await env_fail_verifier.step(action)

    _, reward, _, info = step_result

    # Verify that the verification result indicates a failure
    assert info["verification_result"].status == VerificationOutcome.FAILURE
    assert "Verifier error" in info["verification_result"].error_message
    # Verify that the reward reflects the failure
    assert reward == 0.0

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

    # b) Step after episode is done
    env_episode_ended = SingleStepEnv(
        dataset=dataset,
        verifier=create_mock_verifier(),
    )
    await env_episode_ended.setup()
    await env_episode_ended.reset(batch_size=1)
    await env_episode_ended.step(Action(index=0, llm_response="4"))
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

    # **4. Test Invalid Actions**
    env_invalid_actions = SingleStepEnv(
        dataset=dataset,
        verifier=create_mock_verifier(),
    )
    await env_invalid_actions.setup()
    await env_invalid_actions.reset(batch_size=1)

    # a) Action with invalid index
    with pytest.raises(
        ValueError, match="For batch_size=1, Action index must be 0"
    ):
        await env_invalid_actions.step(Action(index=1, llm_response="4"))

    # b) Providing a list of 2 actions for batch size == 1
    with pytest.raises(
        ValueError,
        match="For batch_size=1, expect a single Action, a dictionary or "
        "a list containing exactly one Action",
    ):
        await env_invalid_actions.step(
            [
                Action(index=0, llm_response="4"),
                Action(index=1, llm_response="3"),
            ]
        )

    # **5. Test Batch Size Issues**
    env_batch_size = SingleStepEnv(
        dataset=dataset,
        verifier=create_mock_verifier(),
    )
    await env_batch_size.setup()
    with pytest.raises(ValueError, match="Batch size must be positive"):
        await env_batch_size.reset(batch_size=0)

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


@pytest.mark.asyncio
async def test_batched_single_step_env_error_handling():
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
    # Ensure errors in verifier are properly handled
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

    step_result = await env_fail_verifier.step(action)

    # Unpack step result
    _, reward, _, info = step_result

    # Verify that the verification result indicates a failure
    assert info["verification_result"].status == VerificationOutcome.FAILURE
    assert "Verifier error" in info["verification_result"].error_message
    # Verify that the reward reflects the failure
    assert reward == 0.0

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


def get_dummy_predefined_data(n):
    predefined_data = []
    for i in range(n):
        predefined_data.append(
            {
                "question": f"What is {i} + {i}?",
                "final_answer": str(i + i),
                "rationale": f"Adding {i} and {i} gives {i + i}.",
                "metadata": {"difficulty": "easy"},
            }
        )
    return predefined_data


@pytest.mark.asyncio
async def test_basegenerator_reset_reproducibility_with_identical_seed():
    """Verify that resetting the environment with the same random seed
    produces identical sampling order across consecutive resets."""

    PREDEFINED_DATA_SIZE = 128
    RESET_BATCH_SIZE = 64

    predefined_data = get_dummy_predefined_data(PREDEFINED_DATA_SIZE)
    mock_verifier = create_mock_verifier()
    dataset = MockGenerator(predefined_data, seed=42)
    env = MockSingleStepEnv(dataset=dataset, verifier=mock_verifier)
    await env.setup()

    # Pre-populate dataset with all data to ensure sampling from full pool
    await dataset.generate_new(PREDEFINED_DATA_SIZE)

    # First reset with seed=42
    observations1 = await env.reset(batch_size=RESET_BATCH_SIZE, seed=42)
    questions1 = [obs.question for obs in observations1]

    # Second reset with same seed=42 should produce same order
    observations2 = await env.reset(batch_size=RESET_BATCH_SIZE, seed=42)
    questions2 = [obs.question for obs in observations2]

    # Same seed should produce same sampling order
    assert (
        questions1 == questions2
    ), "Same seed should produce same sampling order"
    await env.close()


@pytest.mark.asyncio
async def test_basegenerator_reset_variability_with_different_seeds():
    """Verify that resetting the environment with different random seeds
    produces distinct sampling orders, confirming stochastic behavior."""

    PREDEFINED_DATA_SIZE = 128
    RESET_BATCH_SIZE = 64

    predefined_data = get_dummy_predefined_data(PREDEFINED_DATA_SIZE)
    mock_verifier = create_mock_verifier()
    dataset = MockGenerator(predefined_data, seed=42)
    env = MockSingleStepEnv(dataset=dataset, verifier=mock_verifier)
    await env.setup()

    # Pre-populate dataset with all data to ensure sampling from full pool
    await dataset.generate_new(PREDEFINED_DATA_SIZE)

    observations1 = await env.reset(batch_size=RESET_BATCH_SIZE, seed=42)
    questions1 = [obs.question for obs in observations1]

    observations2 = await env.reset(batch_size=RESET_BATCH_SIZE, seed=43)
    questions2 = [obs.question for obs in observations2]

    # Different seeds should produce different orders
    assert (
        questions1 != questions2
    ), "Different seeds should produce different sampling orders"
    await env.close()


@pytest.mark.asyncio
async def test_single_step_env_all_input_types():
    # Define a simple dataset
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

    # Create a mock verifier
    mock_verifier = MagicMock()
    mock_verifier.setup = AsyncMock()
    mock_verifier.cleanup = AsyncMock()
    mock_verifier.verify_batch = AsyncMock(
        side_effect=lambda solutions, reference_answers, **kwargs: [
            VerificationResult(
                status=VerificationOutcome.SUCCESS,
                result="Verification successful",
                feedback="Correct",
                score=1.0,
            )
            for _ in solutions
        ]
    )

    # Initialize the environment
    env = SingleStepEnv(dataset=dataset, verifier=mock_verifier)
    await env.setup()

    # --- Test with batch_size=1 ---
    await env.reset(batch_size=1)

    # 1. Test str input (valid for batch_size=1)
    result = await env.step("4")
    assert isinstance(result, tuple)
    _, reward, done, _ = result
    assert reward == env.ACCURACY_REWARD
    assert done is True

    # Reset for next test
    await env.reset(batch_size=1)

    # 2. Test Action input (valid)
    result = await env.step(Action(index=0, llm_response="4"))
    assert isinstance(result, tuple)
    _, reward, done, _ = result
    assert reward == env.ACCURACY_REWARD
    assert done is True

    # Reset for next test
    await env.reset(batch_size=1)

    # 3. Test List[Action] input (valid with one element)
    result = await env.step([Action(index=0, llm_response="4")])
    assert isinstance(result, tuple)
    _, reward, done, _ = result
    assert reward == env.ACCURACY_REWARD
    assert done is True

    # Reset for error tests
    await env.reset(batch_size=1)

    # 4. Test List[Action] with too many elements
    with pytest.raises(
        ValueError,
        match="For batch_size=1, expect a single Action, a dictionary or "
        "a list containing exactly one Action",
    ):
        await env.step(
            [
                Action(index=0, llm_response="4"),
                Action(index=1, llm_response="Paris"),
            ]
        )

    # 5. Test Action with wrong index
    with pytest.raises(
        ValueError, match="For batch_size=1, Action index must be 0"
    ):
        await env.step(Action(index=1, llm_response="4"))

    # --- Test with batch_size=2 ---
    await env.reset(batch_size=2)

    # 6. Test Dict[int, str] input (valid for batch_size > 1)
    result = await env.step({0: "4", 1: "Paris"})
    assert isinstance(result, list)
    assert len(result) == 2
    for _, reward, done, _ in result:
        assert reward == env.ACCURACY_REWARD
        assert done is True

    # Reset for next test
    await env.reset(batch_size=2)

    # 7. Test List[Action] input (valid)
    result = await env.step(
        [
            Action(index=0, llm_response="4"),
            Action(index=1, llm_response="Paris"),
        ]
    )
    assert isinstance(result, list)
    assert len(result) == 2
    for _, reward, done, _ in result:
        assert reward == env.ACCURACY_REWARD
        assert done is True

    # Reset for next test
    await env.reset(batch_size=2)

    # 8. Test str with batch_size > 1 (should fail)
    with pytest.raises(
        ValueError,
        match="String input for action is only allowed when batch_size == 1",
    ):
        await env.step("4")

    # 9. Test Dict[int, str] with non-integer keys
    with pytest.raises(
        ValueError, match="All dictionary keys must be integers"
    ):
        await env.step({"0": "4", 1: "Paris"})

    # 10. Test List[Action] with non-Action elements
    with pytest.raises(
        ValueError, match="All elements in the list must be Action objects"
    ):
        await env.step([Action(index=0, llm_response="4"), "Paris"])

    # 11. Test invalid index in List[Action]
    with pytest.raises(ValueError, match="Invalid state index 2"):
        await env.step([Action(index=2, llm_response="4")])

    await env.close()
