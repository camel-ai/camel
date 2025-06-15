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
from typing import Any, Dict, Tuple
from unittest.mock import AsyncMock, MagicMock

import pytest

from camel.environments import (
    Action,
    Observation,
)
from camel.environments.multi_step import MultiStepEnv

pytestmark = pytest.mark.heavy_dependency


class MockMultiStepEnv(MultiStepEnv):
    def _get_initial_state(self) -> Dict[str, Any]:
        """Return the initial state with a step counter."""
        return {"step": 0}

    async def _update_state(self, action: Action) -> None:
        """Increment the step counter based on the action."""
        self._state["step"] += 1

    def _get_next_observation(self) -> Observation:
        """Return an observation reflecting the current step."""
        return Observation(question=f"Step {self._state['step']}")

    def _get_terminal_observation(self) -> Observation:
        """Return the terminal observation when the episode ends."""
        return Observation(question="Episode ended")

    async def compute_reward(self) -> Tuple[float, Dict[str, float]]:
        """Return a fixed reward and reward breakdown."""
        return 1.0, {"step_reward": 1.0}

    def _is_done(self) -> bool:
        """End the episode after 2 steps."""
        return self._state["step"] >= 2

    async def _setup(self) -> None:
        """Perform any setup tasks (empty for this mock)."""
        pass

    async def _close(self) -> None:
        """Perform any cleanup tasks (empty for this mock)."""
        pass


@pytest.mark.asyncio
async def test_multi_step_env_lifecycle():
    # Create a mock extractor
    mock_extractor = MagicMock()
    mock_extractor.setup = AsyncMock()
    mock_extractor.cleanup = AsyncMock()
    mock_extractor.extract = AsyncMock(return_value="extracted_answer")

    env = MockMultiStepEnv(extractor=mock_extractor, max_steps=3)
    await env.setup()
    assert env._is_setup is True
    mock_extractor.setup.assert_awaited_once()

    observation = await env.reset()
    assert isinstance(observation, Observation)
    assert observation.question == "Step 0"

    # Test first step
    action1 = Action(llm_response="Response 1")
    # FIXME: index set to 0 temporarily until we have batched MultiStep
    obs, reward, done, info = await env.step(action1)
    assert reward == 1.0
    assert done is False
    assert obs.question == "Step 1"
    assert env._current_step == 1
    assert env._state["step"] == 1
    mock_extractor.extract.assert_called_once_with("Response 1")

    # Test second step
    action2 = Action(llm_response="Response 2")
    # FIXME: index set to 0 temporarily until we have batched MultiStep
    obs2, reward2, done2, info = await env.step(action2)
    assert reward2 == 1.0
    assert done2 is True
    assert obs2.question == "Episode ended"
    assert env._current_step == 2
    assert env._state["step"] == 2
    assert mock_extractor.extract.call_count == 2
    mock_extractor.extract.assert_called_with("Response 2")

    await env.close()
    assert env._is_setup is False
    mock_extractor.cleanup.assert_awaited_once()


@pytest.mark.asyncio
async def test_multi_step_env_error_handling():
    mock_extractor = MagicMock()
    mock_extractor.setup = AsyncMock()
    mock_extractor.cleanup = AsyncMock()
    mock_extractor.extract = MagicMock(return_value="extracted_answer")

    env = MockMultiStepEnv(extractor=mock_extractor, max_steps=3)
    action = Action(index=0, llm_response="Test response")
    # FIXME: index set to 0 temporarily until we have batched MultiStep

    # **Test Case 1: Environment not set up**
    # Attempt to step without setup, expect RuntimeError
    with pytest.raises(
        RuntimeError,
        match=re.escape("Environment not set up. Call setup() first."),
    ):
        await env.step(action)

    # **Test Case 2: Episode has ended**
    # Setup and reset, then mark episode as ended
    await env.setup()
    await env.reset()
    env._episode_ended = True
    with pytest.raises(
        RuntimeError, match=re.escape("Episode has ended. Call reset() first.")
    ):
        await env.step(action)

    # **Test Case 3: No current observation**
    # Reset to initialize, then clear last observation
    await env.reset()
    env._last_observation = None
    with pytest.raises(
        RuntimeError,
        match=re.escape("No current observation. Call reset() first."),
    ):
        await env.step(action)

    # **Test Case 4: Extractor failure**
    # Configure extractor to raise an exception
    mock_extractor.extract = AsyncMock(
        side_effect=Exception("Extractor error")
    )
    await env.reset()
    with pytest.raises(Exception, match="Extractor error"):
        await env.step(action)

    # **Test Case 5: Maximum steps reached**
    # Create a new environment with max_steps=1
    # Reset extractor for Test Case 5
    mock_extractor.extract = AsyncMock(return_value="extracted_answer")
    env_max_steps = MockMultiStepEnv(extractor=mock_extractor, max_steps=1)
    await env_max_steps.setup()
    await env_max_steps.reset()
    # First step should end the episode due to max_steps
    obs, reward, done, info = await env_max_steps.step(action)
    assert done is True, "Episode should be done after reaching max_steps"
    assert env_max_steps._current_step == 1, "Current step should be 1"
    assert env_max_steps.max_steps == 1, "Max steps should be 1"
    assert obs.question == "Episode ended", "Should reach terminal observation"
