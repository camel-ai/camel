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

    async def reset(self):
        return Observation(question="Initial question")

    async def step(self, action):
        return StepResult(
            observation=Observation(question="Next question"),
            reward=1.0,
            done=False,
            info={}
        )

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_base_environment_lifecycle():
    env = MockBaseEnvironment()

    # Test reset
    observation = await env.reset()
    assert isinstance(observation, Observation)
    assert observation.question == "Initial question"

    # Test step
    action = Action(problem_statement="Test problem", llm_response="Test response")
    result = await env.step(action)
    assert isinstance(result, StepResult)
    assert result.reward == 1.0
    assert result.done is False
    assert isinstance(result.observation, Observation)

    # Test close
    await env.close()
