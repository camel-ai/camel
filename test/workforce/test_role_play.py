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

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.societies.role_playing import (
    RolePlaying,
    with_timeout,
)


@pytest.mark.asyncio
async def test_with_timeout_function():
    """Test the with_timeout function handles completions and timeouts correctly"""
    # Test normal operation (successful completion)
    mock_coro = AsyncMock()
    mock_coro.return_value = "success"
    result = await with_timeout(mock_coro(), context="test operation")
    assert result == "success"

    # Test timeout handling
    mock_timeout_coro = AsyncMock()
    mock_timeout_coro.side_effect = asyncio.TimeoutError("Simulated timeout")

    with pytest.raises(asyncio.TimeoutError) as exc_info:
        await with_timeout(
            mock_timeout_coro(), context="test timeout operation"
        )

    assert "Timed out while test timeout operation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_user_agent_timeout():
    """Test handling timeout from user agent in RolePlaying.astep"""
    # Create mock agents
    mock_user_agent = AsyncMock(spec=ChatAgent)
    mock_user_agent.astep.side_effect = asyncio.TimeoutError()
    mock_user_agent.role_name = "mock_user"

    # Add model_backend to both mock agents
    mock_user_agent.model_backend = MagicMock()
    mock_user_agent.model_backend.model_config_dict = {}

    mock_assistant_agent = AsyncMock(spec=ChatAgent)
    mock_assistant_agent.model_backend = MagicMock()
    mock_assistant_agent.model_backend.model_config_dict = {}

    # Create RolePlaying instance with mocked agents
    role_playing = RolePlaying("assistant", "user")
    role_playing.assistant_agent = mock_assistant_agent
    role_playing.user_agent = mock_user_agent

    # Create mock message
    mock_msg = MagicMock(spec=BaseMessage)

    # Test that TimeoutError is propagated
    with pytest.raises(asyncio.TimeoutError):
        await role_playing.astep(mock_msg)

    # Verify the user agent's astep was called
    mock_user_agent.astep.assert_called_once_with(mock_msg)
    # Verify the assistant agent's astep was not called
    mock_assistant_agent.astep.assert_not_called()


@pytest.mark.asyncio
async def test_assistant_agent_timeout():
    """Test handling timeout from assistant agent in RolePlaying.astep"""
    # Create mock agents with model_backend
    mock_user_agent = AsyncMock(spec=ChatAgent)
    mock_user_agent.model_backend = MagicMock()
    mock_user_agent.model_backend.model_config_dict = {}

    mock_assistant_agent = AsyncMock(spec=ChatAgent)
    mock_assistant_agent.model_backend = MagicMock()
    mock_assistant_agent.model_backend.model_config_dict = {}

    # Configure user_agent to return normal response and assistant_agent to timeout
    mock_user_response = MagicMock(spec=ChatAgentResponse)
    mock_user_response.msgs = [MagicMock(spec=BaseMessage)]
    mock_user_response.terminated = False
    mock_user_agent.astep.return_value = mock_user_response
    mock_user_agent.role_name = "mock_user"

    mock_assistant_agent.astep.side_effect = asyncio.TimeoutError()
    mock_assistant_agent.role_name = "mock_assistant"

    # Create RolePlaying instance with mocked agents
    role_playing = RolePlaying("assistant", "user")
    role_playing.assistant_agent = mock_assistant_agent
    role_playing.user_agent = mock_user_agent
    role_playing._reduce_message_options = lambda msgs: msgs[
        0
    ]  # Mock this function

    # Create mock message
    mock_msg = MagicMock(spec=BaseMessage)

    # Test that TimeoutError is propagated
    with pytest.raises(asyncio.TimeoutError):
        await role_playing.astep(mock_msg)

    # Verify both agents' astep methods were called
    mock_user_agent.astep.assert_called_once_with(mock_msg)
    mock_assistant_agent.astep.assert_called_once()


@pytest.mark.asyncio
async def test_recovery_from_timeout():
    """Test RolePlaying can recover from an agent timeout"""
    # Create mock agents with model_backend
    mock_user_agent = AsyncMock(spec=ChatAgent)
    mock_user_agent.model_backend = MagicMock()
    mock_user_agent.model_backend.model_config_dict = {}

    mock_assistant_agent = AsyncMock(spec=ChatAgent)
    mock_assistant_agent.model_backend = MagicMock()
    mock_assistant_agent.model_backend.model_config_dict = {}

    # First call to user_agent.astep will timeout, second will succeed
    call_count = 0

    async def user_agent_side_effect(msg):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise asyncio.TimeoutError("Simulated timeout")

        response = MagicMock(spec=ChatAgentResponse)
        response.msgs = [MagicMock(spec=BaseMessage)]
        response.terminated = False
        response.info = {}
        return response

    mock_user_agent.astep.side_effect = user_agent_side_effect
    mock_user_agent.role_name = "mock_user"

    # Assistant agent returns normal response
    mock_assistant_response = MagicMock(spec=ChatAgentResponse)
    mock_assistant_response.msgs = [MagicMock(spec=BaseMessage)]
    mock_assistant_response.terminated = False
    mock_assistant_response.info = {}
    mock_assistant_agent.astep.return_value = mock_assistant_response
    mock_assistant_agent.role_name = "mock_assistant"

    # Create RolePlaying instance with mocked agents
    role_playing = RolePlaying("assistant", "user")
    role_playing.assistant_agent = mock_assistant_agent
    role_playing.user_agent = mock_user_agent
    role_playing._reduce_message_options = lambda msgs: msgs[
        0
    ]  # Mock this function

    # Create mock message
    mock_msg = MagicMock(spec=BaseMessage)

    # First attempt should raise TimeoutError
    with pytest.raises(asyncio.TimeoutError):
        await role_playing.astep(mock_msg)

    # Second attempt should succeed
    user_response, assistant_response = await role_playing.astep(mock_msg)

    # Verify both responses are returned
    assert user_response is not None
    assert assistant_response is not None
    assert user_response.terminated is False
    assert assistant_response.terminated is False

    # Verify both agents were called the expected number of times
    assert mock_user_agent.astep.call_count == 2
    assert mock_assistant_agent.astep.call_count == 1


@pytest.mark.asyncio
async def test_integration_with_timeout():
    """Test the full RolePlaying.astep flow with various timeout points"""

    # Setup patching of with_timeout - properly await the coroutine
    async def mock_with_timeout(coro, **kwargs):
        # Make sure we await the coroutine
        return await coro

    # Create properly structured return values
    mock_user_msg = MagicMock(spec=BaseMessage)
    mock_assistant_msg = MagicMock(spec=BaseMessage)

    mock_user_response = MagicMock(spec=ChatAgentResponse)
    mock_user_response.msgs = [mock_user_msg]
    mock_user_response.terminated = False
    mock_user_response.info = {}

    mock_assistant_response = MagicMock(spec=ChatAgentResponse)
    mock_assistant_response.msgs = [mock_assistant_msg]
    mock_assistant_response.terminated = False
    mock_assistant_response.info = {}

    # Create mocked agents that return proper values
    mock_user_agent = AsyncMock(spec=ChatAgent)
    mock_user_agent.astep.return_value = mock_user_response
    mock_user_agent.role_name = "mock_user"
    mock_user_agent.model_backend = MagicMock()
    mock_user_agent.model_backend.model_config_dict = {}

    mock_assistant_agent = AsyncMock(spec=ChatAgent)
    mock_assistant_agent.astep.return_value = mock_assistant_response
    mock_assistant_agent.role_name = "mock_assistant"
    mock_assistant_agent.model_backend = MagicMock()
    mock_assistant_agent.model_backend.model_config_dict = {}

    # Create RolePlaying instance
    role_playing = RolePlaying("assistant", "user")
    role_playing.assistant_agent = mock_assistant_agent
    role_playing.user_agent = mock_user_agent
    role_playing._reduce_message_options = lambda msgs: msgs[
        0
    ]  # Mock this function

    # Create test message
    test_msg = MagicMock(spec=BaseMessage)

    # Test the normal flow (no timeouts)
    with patch(
        "camel.societies.role_playing.with_timeout",
        side_effect=mock_with_timeout,
    ):
        user_response, assistant_response = await role_playing.astep(test_msg)

        # validate response
        assert len(user_response.msgs) == 1
        assert user_response.terminated is False
        assert user_response.info == {}

        assert len(assistant_response.msgs) == 1
        assert assistant_response.terminated is False
        assert assistant_response.info == {}

    # verify both agents were called
    mock_user_agent.astep.assert_called_with(test_msg)
    mock_assistant_agent.astep.assert_called_with(mock_user_msg)
