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
from unittest.mock import Mock, patch

import pytest

from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.societies import RolePlaying
from services.role_playing_mcp.server import (
    chat_step,
    clone_session,
    create_session,
    delete_session,
    get_available_scenarios,
    get_session_info,
)


@pytest.fixture
def mock_role_playing():
    mock = Mock(spec=RolePlaying)
    mock.assistant_agent = Mock()
    mock.assistant_agent.role_name = "test_assistant"
    mock.user_agent = Mock()
    mock.user_agent.role_name = "test_user"
    mock.task_prompt = "test prompt"
    mock.with_task_specify = True
    mock.with_task_planner = False
    mock.with_critic_in_the_loop = False

    # Mock init_chat method
    init_msg = BaseMessage.make_assistant_message(
        role_name="test_assistant", content="Initial message"
    )
    mock.init_chat.return_value = init_msg

    return mock


@pytest.fixture
def mock_context():
    return Mock()


def test_get_available_scenarios():
    scenarios = get_available_scenarios()
    assert isinstance(scenarios, dict)
    # Verify each scenario has the expected keys
    for scenario_info in scenarios.values():
        assert "assistant_role_name" in scenario_info
        assert "user_role_name" in scenario_info
        assert "task_prompt" in scenario_info


@pytest.mark.asyncio
async def test_create_session_success(mock_role_playing):
    with patch(
        "services.role_playing_mcp.server.RolePlaying",
        return_value=mock_role_playing,
    ):
        result = create_session(
            assistant_role_name="test_assistant",
            user_role_name="test_user",
            task_prompt="test prompt",
            task_type="AI_SOCIETY",
        )

        assert "session_id" in result
        assert result["assistant_role"] == "test_assistant"
        assert result["user_role"] == "test_user"
        assert result["task_prompt"] == "test prompt"
        assert result["initial_message"] == "Initial message"


@pytest.mark.asyncio
async def test_create_session_with_scenario(mock_role_playing):
    with patch(
        "services.role_playing_mcp.server.RolePlaying",
        return_value=mock_role_playing,
    ):
        result = create_session(scenario_name="python_developer")
        assert "session_id" in result
        assert "assistant_role" in result
        assert "user_role" in result
        assert "task_prompt" in result


@pytest.mark.asyncio
async def test_chat_step_success(mock_role_playing, mock_context):
    # Mock step method to return appropriate responses
    assistant_msg = BaseMessage.make_assistant_message(
        role_name="test_assistant", content="Assistant response"
    )
    user_msg = BaseMessage.make_user_message(
        role_name="test_user", content="User response"
    )
    mock_role_playing.step.return_value = (
        ChatAgentResponse(msgs=[assistant_msg], terminated=False, info={}),
        ChatAgentResponse(msgs=[user_msg], terminated=False, info={}),
    )

    with patch(
        "services.role_playing_mcp.server.active_sessions",
        {"test_session": mock_role_playing},
    ):
        result = chat_step("test_session", "Test message", mock_context)

        assert not result["terminated"]
        assert result["assistant_response"] == "Assistant response"
        assert result["user_response"] == "User response"


@pytest.mark.asyncio
async def test_chat_step_session_not_found(mock_context):
    result = chat_step("nonexistent_session", "Test message", mock_context)
    assert "error" in result


@pytest.mark.asyncio
async def test_get_session_info_success(mock_role_playing):
    with patch(
        "services.role_playing_mcp.server.active_sessions",
        {"test_session": mock_role_playing},
    ):
        result = get_session_info("test_session")

        assert result["assistant_role"] == "test_assistant"
        assert result["user_role"] == "test_user"
        assert result["task_prompt"] == "test prompt"
        assert result["with_task_specify"] is True
        assert result["with_task_planner"] is False
        assert result["with_critic"] is False


def test_get_session_info_not_found():
    result = get_session_info("nonexistent_session")
    assert "error" in result


def test_delete_session_success(mock_role_playing):
    with patch(
        "services.role_playing_mcp.server.active_sessions",
        {"test_session": mock_role_playing},
    ):
        result = delete_session("test_session")
        assert "success" in result


def test_delete_session_not_found():
    result = delete_session("nonexistent_session")
    assert "error" in result


@pytest.mark.asyncio
async def test_clone_session_success(mock_role_playing):
    # Mock clone method
    mock_role_playing.clone.return_value = mock_role_playing

    with patch(
        "services.role_playing_mcp.server.active_sessions",
        {"test_session": mock_role_playing},
    ):
        result = clone_session(
            "test_session", "new test prompt", with_memory=False
        )

        assert "session_id" in result
        assert result["assistant_role"] == "test_assistant"
        assert result["user_role"] == "test_user"
        assert result["task_prompt"] == "new test prompt"
        assert result["initial_message"] == "Initial message"


def test_clone_session_not_found():
    result = clone_session("nonexistent_session", "new prompt")
    assert "error" in result
