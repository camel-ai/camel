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

import json
import time
import uuid
from unittest.mock import MagicMock

import pytest

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.toolkits.message_agent_toolkit import (
    AgentCommunicationToolkit,
    AgentMessage,
)


class TestAgentMessage:
    r"""Test suite for the AgentMessage class."""

    def test_agent_message_initialization(self):
        r"""Test AgentMessage initialization with core parameters."""
        message_id = str(uuid.uuid4())
        sender_id = "agent1"
        receiver_id = "agent2"
        content = "Hello, this is a test message"
        timestamp = time.time()

        message = AgentMessage(
            message_id=message_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            timestamp=timestamp,
        )

        assert message.id == message_id
        assert message.sender_id == sender_id
        assert message.receiver_id == receiver_id
        assert message.content == content
        assert message.timestamp == timestamp
        assert isinstance(message, BaseMessage)


class TestAgentCommunicationToolkit:
    r"""Test suite for the AgentCommunicationToolkit class."""

    @pytest.fixture
    def mock_agent(self):
        r"""Create a mock ChatAgent for testing."""
        agent = MagicMock(spec=ChatAgent)
        agent.step.return_value = MagicMock(
            msgs=[MagicMock(content="Mock response")]
        )
        return agent

    @pytest.fixture
    def toolkit(self):
        r"""Create a AgentCommunicationToolkit instance for testing."""
        return AgentCommunicationToolkit()

    @pytest.fixture
    def toolkit_with_agents(self):
        r"""Create a AgentCommunicationToolkit with pre-registered agents."""
        agent1 = MagicMock(spec=ChatAgent)
        agent1.step.return_value = MagicMock(
            msgs=[MagicMock(content="Agent1 response")]
        )

        agent2 = MagicMock(spec=ChatAgent)
        agent2.step.return_value = MagicMock(
            msgs=[MagicMock(content="Agent2 response")]
        )

        toolkit = AgentCommunicationToolkit(
            agents={"agent1": agent1, "agent2": agent2}
        )
        return toolkit

    def test_register_agent(self, toolkit, mock_agent):
        r"""Test agent registration."""
        result = toolkit.register_agent("test_agent", mock_agent)

        assert "test_agent" in toolkit.agents
        assert toolkit.agents["test_agent"] == mock_agent
        assert "registered successfully" in result.lower()

    def test_send_message_success(self, toolkit_with_agents):
        r"""Test successful message sending."""
        result = toolkit_with_agents.send_message(
            message="Hello, agent2!",
            receiver_id="agent2",
            sender_id="agent1",
        )

        assert "delivered" in result.lower()
        assert "agent2" in result
        assert len(toolkit_with_agents._message_history["agent1"]) == 1
        assert len(toolkit_with_agents._message_history["agent2"]) == 1

    def test_send_message_with_metadata(self, toolkit_with_agents):
        r"""Test message sending with metadata."""
        metadata = {"priority": "high"}
        result = toolkit_with_agents.send_message(
            message="Urgent message",
            receiver_id="agent2",
            sender_id="agent1",
            metadata_json=json.dumps(metadata),
        )

        assert "delivered" in result.lower()
        history = toolkit_with_agents._message_history["agent1"]
        assert history[0].metadata == metadata

    def test_send_message_agent_not_found(self, toolkit_with_agents):
        r"""Test sending message to non-existent agent."""
        result = toolkit_with_agents.send_message(
            message="Hello",
            receiver_id="nonexistent",
            sender_id="agent1",
        )

        assert "error" in result.lower()
        assert "not found" in result.lower()

    def test_send_message_empty_content(self, toolkit_with_agents):
        r"""Test sending message with empty content."""
        with pytest.raises(
            ValueError, match="Message content cannot be empty"
        ):
            toolkit_with_agents.send_message(
                message="",
                receiver_id="agent2",
                sender_id="agent1",
            )

    def test_broadcast_message(self, toolkit_with_agents):
        r"""Test broadcast message functionality."""
        result = toolkit_with_agents.broadcast_message(
            message="Broadcast to all",
            sender_id="system",
        )

        assert "broadcast completed" in result.lower()
        assert "agent1:" in result
        assert "agent2:" in result

    def test_get_message_history(self, toolkit_with_agents):
        r"""Test retrieving message history."""
        toolkit_with_agents.send_message("Hello", "agent2", "agent1")

        result = toolkit_with_agents.get_message_history("agent1")

        assert "message history" in result.lower()
        assert "agent1" in result
        assert "hello" in result.lower()

    def test_list_available_agents(self, toolkit_with_agents):
        r"""Test listing available agents."""
        result = toolkit_with_agents.list_available_agents()

        assert "available agents" in result.lower()
        assert "agent1" in result
        assert "agent2" in result

    def test_get_tools_returns_function_tools(self, toolkit):
        r"""Test that get_tools returns proper FunctionTool objects."""
        tools = toolkit.get_tools()

        assert len(tools) == 5
        tool_names = [tool.func.__name__ for tool in tools]

        expected_tools = [
            "send_message",
            "broadcast_message",
            "list_available_agents",
            "get_message_history",
            "get_conversation_thread",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_message_history_size_management(self, toolkit_with_agents):
        r"""Test message history size management."""
        toolkit_with_agents.max_message_history = 3

        # Send more messages than the limit
        for i in range(5):
            toolkit_with_agents.send_message(
                f"Message {i}", "agent2", "agent1"
            )

        history = toolkit_with_agents._message_history["agent1"]
        assert len(history) == 3
