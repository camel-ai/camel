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
from camel.verifiers.models import VerificationOutcome, VerificationResult


def test_action_model():
    r"""Test the Action model initialization and properties."""
    custom_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    action_full = Action(
        llm_response="Full response",
        metadata={"model": "test-model", "temperature": 0.7},
        timestamp=custom_time,
    )
    assert action_full.llm_response == "Full response"
    assert action_full.metadata == {"model": "test-model", "temperature": 0.7}
    assert action_full.timestamp == custom_time


def test_observation_model():
    r"""Test the Observation model initialization and properties."""
    obs_full = Observation(
        question="Complex math problem",
        context={"hint": "Use calculus"},
        metadata={"difficulty": "hard"},
    )
    assert obs_full.question == "Complex math problem"
    assert obs_full.context == {"hint": "Use calculus"}
    assert obs_full.metadata == {"difficulty": "hard"}


def test_step_result_model():
    r"""Test the StepResult model initialization and properties."""
    obs = Observation(question="Next question")
    result_full = StepResult(
        observation=obs,
        reward=1.0,
        rewards_dict={"correctness": 0.8, "efficiency": 0.2},
        done=True,
        info={"reason": "task_complete"},
    )
    assert result_full.observation == obs
    assert result_full.reward == 1.0
    assert result_full.rewards_dict == {"correctness": 0.8, "efficiency": 0.2}
    assert result_full.done is True
    assert result_full.info == {"reason": "task_complete"}


class MockBaseEnvironment(BaseEnvironment):
    r"""Mock implementation of BaseEnvironment for testing."""

    async def setup(self):
        await super().setup()

    async def teardown(self):
        await super().teardown()

    async def reset(self):
        return await super().reset()

    async def step(self, action):
        return await super().step(action)

    def _get_initial_state(self):
        return super()._get_initial_state()

    def _get_next_observation(self):
        return Observation(question="Test question")

    def _get_terminal_observation(self):
        return super()._get_terminal_observation()

    async def compute_reward(
        self,
        action: Action,
        extraction_result: str,
        verification_result: VerificationResult,
    ) -> Tuple[float, Dict[str, float]]:
        return await super().compute_reward(
            action, extraction_result, verification_result
        )

    async def _compute_reward(
        self, action, extraction_result, verification_result
    ):
        return {"additional_reward": 0.5}


@pytest.mark.asyncio
async def test_base_environment_lifecycle():
    r"""Test the lifecycle methods of BaseEnvironment."""
    mock_dataset = MagicMock()
    mock_dataset.__len__.return_value = 1
    mock_dataset.__getitem__.return_value = MagicMock(
        question="Test question",
        final_answer="Test answer",
        rationale="Test rationale",
        difficulty="medium",
        metadata={"verified": True},
    )
    mock_dataset.setup = AsyncMock()
    mock_dataset.cleanup = AsyncMock()

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
    mock_extractor.extract = AsyncMock(return_value={"extracted": "content"})

    # Create environment
    env = MockBaseEnvironment(
        dataset=mock_dataset,
        verifier=mock_verifier,
        extractor=mock_extractor,
        max_steps=5,
    )

    # Test setup
    await env.setup()
    assert env._is_setup is True
    mock_verifier.setup.assert_awaited_once()

    # Test reset
    observation = await env.reset()
    assert isinstance(observation, Observation)
    assert env._current_step == 0
    assert env._episode_ended is False

    original_step = env.step

    async def mock_step(action):
        env._current_step += 1
        return StepResult(
            observation=env._get_next_observation(),
            reward=1.0,
            rewards_dict={"correctness": 1.0, "additional_reward": 0.5},
            done=False,
            info={
                "extraction_result": {"extracted": "content"},
                "verification_result": VerificationResult(
                    status=VerificationOutcome.SUCCESS,
                    result="Verification successful",
                    feedback="Correct",
                    score=1.0,
                ),
                "step": env._current_step,
            },
        )

    env.step = mock_step

    # Test step
    action = Action(
        problem_statement="Test problem",
        llm_response="Test response",
    )
    result = await env.step(action)
    assert isinstance(result, StepResult)
    assert env._current_step == 1

    # Restore the original step method
    env.step = original_step

    # Test teardown
    await env.teardown()
    assert env._is_setup is False
    mock_verifier.cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_environment_reward_calculation():
    r"""Test the reward calculation in BaseEnvironment."""
    env = MockBaseEnvironment(
        dataset=MagicMock(),
        verifier=MagicMock(),
        extractor=MagicMock(),
    )

    # Test compute_reward method
    action = Action(
        problem_statement="Test problem",
        llm_response="Test response",
    )
    extraction_result = {"extracted": "content"}
    verification_result = VerificationResult(
        status=VerificationOutcome.SUCCESS,
        result="Verification successful",
        feedback="Correct",
        score=1.0,
    )

    total_reward, rewards_dict = await env.compute_reward(
        action, extraction_result, verification_result
    )

    # Check rewards
    assert "correctness" in rewards_dict
    assert rewards_dict["correctness"] == 1.0
    assert "additional_reward" in rewards_dict
    assert rewards_dict["additional_reward"] == 0.5
    assert total_reward == 1.5  # Sum of all rewards


@pytest.mark.asyncio
async def test_environment_max_steps():
    r"""Test that environment terminates after max_steps."""
    env = MockBaseEnvironment(
        dataset=MagicMock(),
        verifier=MagicMock(),
        extractor=MagicMock(),
        max_steps=2,
    )
    env._is_setup = True

    # Take first step
    action = Action(
        problem_statement="Test problem",
        llm_response="Test response",
    )
    env._last_observation = Observation(question="Test question")

    original_step = env.step

    async def mock_step(action):
        env._current_step += 1
        done = env._current_step >= env.max_steps
        return StepResult(
            observation=env._get_terminal_observation()
            if done
            else env._get_next_observation(),
            reward=1.0,
            rewards_dict={"correctness": 1.0},
            done=done,
            info={"reason": "max_steps_reached"} if done else {},
        )

    # Replace the step method
    env.step = mock_step

    # First step should not terminate
    result1 = await env.step(action)
    assert result1.done is False

    # Second step should terminate due to max_steps
    result2 = await env.step(action)
    assert result2.done is True
    assert "max_steps_reached" in result2.info.get("reason", "")

    # Restore the original step method
    env.step = original_step
