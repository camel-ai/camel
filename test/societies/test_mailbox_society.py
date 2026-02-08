# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from collections import deque

import pytest

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.mailbox_society import (
    AgentCard,
    MailboxMessage,
    MailboxSociety,
)
from camel.toolkits import AgentDiscoveryToolkit, MailboxToolkit
from camel.types import ModelPlatformType, ModelType


class TestMailboxMessage:
    r"""Test cases for MailboxMessage class."""

    def test_message_creation(self):
        r"""Test creating a mailbox message."""
        msg = MailboxMessage(
            sender_id="agent1",
            recipient_id="agent2",
            content="Hello",
            subject="Greeting",
        )

        assert msg.sender_id == "agent1"
        assert msg.recipient_id == "agent2"
        assert msg.content == "Hello"
        assert msg.subject == "Greeting"
        assert msg.timestamp is not None

    def test_message_str(self):
        r"""Test string representation of message."""
        msg = MailboxMessage(
            sender_id="agent1",
            recipient_id="agent2",
            content="Test message",
        )

        str_repr = str(msg)
        assert "agent1" in str_repr
        assert "agent2" in str_repr


class TestAgentCard:
    r"""Test cases for AgentCard class."""

    def test_agent_card_creation(self):
        r"""Test creating an agent card."""
        card = AgentCard(
            agent_id="test_agent",
            description="A test agent",
            capabilities=["chat", "search"],
            tags=["helper", "assistant"],
        )

        assert card.agent_id == "test_agent"
        assert card.description == "A test agent"
        assert len(card.capabilities) == 2
        assert len(card.tags) == 2

    def test_agent_card_to_dict(self):
        r"""Test converting agent card to dictionary."""
        card = AgentCard(
            agent_id="test_agent",
            description="A test agent",
            capabilities=["chat"],
            tags=["helper"],
        )

        card_dict = card.to_dict()
        assert card_dict["agent_id"] == "test_agent"
        assert card_dict["description"] == "A test agent"
        assert card_dict["capabilities"] == ["chat"]
        assert card_dict["tags"] == ["helper"]

    def test_agent_card_str(self):
        r"""Test string representation of agent card."""
        card = AgentCard(
            agent_id="test_agent",
            description="A test agent",
            capabilities=["chat"],
        )

        str_repr = str(card)
        assert "test_agent" in str_repr
        assert "A test agent" in str_repr


class TestMailboxToolkit:
    r"""Test cases for MailboxToolkit class."""

    def test_mailbox_initialization(self):
        r"""Test initializing a mailbox toolkit."""
        message_router = {}
        toolkit = MailboxToolkit("agent1", message_router)

        assert toolkit.agent_id == "agent1"
        assert "agent1" in message_router
        assert isinstance(message_router["agent1"], deque)

    def test_send_message_success(self):
        r"""Test sending a message successfully."""
        message_router = {}
        toolkit1 = MailboxToolkit("agent1", message_router)
        _ = MailboxToolkit("agent2", message_router)

        result = toolkit1.send_message(
            "agent2", "Hello agent2", subject="Greeting"
        )

        assert "sent successfully" in result.lower()
        assert len(message_router["agent2"]) == 1

    def test_send_message_invalid_recipient(self):
        r"""Test sending a message to an invalid recipient."""
        message_router = {}
        toolkit = MailboxToolkit("agent1", message_router)

        result = toolkit.send_message("nonexistent", "Hello")

        assert "error" in result.lower()
        assert "not found" in result.lower()

    def test_receive_messages(self):
        r"""Test receiving messages from mailbox."""
        message_router = {}
        toolkit1 = MailboxToolkit("agent1", message_router)
        toolkit2 = MailboxToolkit("agent2", message_router)

        # Send a message
        toolkit1.send_message("agent2", "Test message", subject="Test")

        # Receive the message
        result = toolkit2.receive_messages()

        assert "agent1" in result
        assert "Test message" in result
        assert len(message_router["agent2"]) == 0  # Message removed

    def test_receive_messages_empty_mailbox(self):
        r"""Test receiving messages when mailbox is empty."""
        message_router = {}
        toolkit = MailboxToolkit("agent1", message_router)

        result = toolkit.receive_messages()

        assert "no messages" in result.lower()

    def test_check_messages(self):
        r"""Test checking message count."""
        message_router = {}
        toolkit1 = MailboxToolkit("agent1", message_router)
        toolkit2 = MailboxToolkit("agent2", message_router)

        # Initially no messages
        result = toolkit2.check_messages()
        assert "no unread messages" in result.lower()

        # Send messages
        toolkit1.send_message("agent2", "Message 1")
        toolkit1.send_message("agent2", "Message 2")

        result = toolkit2.check_messages()
        assert "2 unread messages" in result

    def test_peek_messages(self):
        r"""Test peeking at messages without removing them."""
        message_router = {}
        toolkit1 = MailboxToolkit("agent1", message_router)
        toolkit2 = MailboxToolkit("agent2", message_router)

        # Send messages
        toolkit1.send_message("agent2", "Message 1")
        toolkit1.send_message("agent2", "Message 2")

        # Peek at messages
        result = toolkit2.peek_messages()

        assert "agent1" in result
        assert len(message_router["agent2"]) == 2  # Messages not removed

    def test_get_available_agents(self):
        r"""Test getting list of available agents."""
        message_router = {}
        toolkit1 = MailboxToolkit("agent1", message_router)
        _ = MailboxToolkit("agent2", message_router)
        _ = MailboxToolkit("agent3", message_router)

        result = toolkit1.get_available_agents()

        assert "agent2" in result
        assert "agent3" in result
        assert "agent1" not in result


class TestAgentDiscoveryToolkit:
    r"""Test cases for AgentDiscoveryToolkit class."""

    def test_list_all_agents(self):
        r"""Test listing all agents."""
        agent_registry = {
            "agent1": AgentCard(
                "agent1", "Agent 1 description", ["skill1"]
            ),
            "agent2": AgentCard(
                "agent2", "Agent 2 description", ["skill2"]
            ),
        }

        toolkit = AgentDiscoveryToolkit("agent1", agent_registry)
        result = toolkit.list_all_agents()

        assert "agent2" in result
        assert "agent1" not in result  # Should not list self

    def test_search_agents_by_capability(self):
        r"""Test searching agents by capability."""
        agent_registry = {
            "agent1": AgentCard(
                "agent1", "Agent 1", ["search", "analyze"]
            ),
            "agent2": AgentCard("agent2", "Agent 2", ["search", "write"]),
            "agent3": AgentCard("agent3", "Agent 3", ["compute"]),
        }

        toolkit = AgentDiscoveryToolkit("agent1", agent_registry)
        result = toolkit.search_agents_by_capability("search")

        assert "agent2" in result
        assert "agent3" not in result

    def test_search_agents_by_tag(self):
        r"""Test searching agents by tag."""
        agent_registry = {
            "agent1": AgentCard(
                "agent1", "Agent 1", [], tags=["helper"]
            ),
            "agent2": AgentCard(
                "agent2", "Agent 2", [], tags=["helper", "assistant"]
            ),
            "agent3": AgentCard("agent3", "Agent 3", [], tags=["worker"]),
        }

        toolkit = AgentDiscoveryToolkit("agent1", agent_registry)
        result = toolkit.search_agents_by_tag("helper")

        assert "agent2" in result
        assert "agent3" not in result

    def test_search_agents_by_description(self):
        r"""Test searching agents by description."""
        agent_registry = {
            "agent1": AgentCard("agent1", "A helpful assistant", []),
            "agent2": AgentCard("agent2", "A data analyst", []),
            "agent3": AgentCard("agent3", "A helpful coordinator", []),
        }

        toolkit = AgentDiscoveryToolkit("agent1", agent_registry)
        result = toolkit.search_agents_by_description("helpful")

        assert "agent3" in result
        assert "agent2" not in result

    def test_get_agent_details(self):
        r"""Test getting details of a specific agent."""
        agent_registry = {
            "agent1": AgentCard("agent1", "Agent 1", ["skill1"]),
            "agent2": AgentCard("agent2", "Agent 2", ["skill2"]),
        }

        toolkit = AgentDiscoveryToolkit("agent1", agent_registry)
        result = toolkit.get_agent_details("agent2")

        assert "agent2" in result
        assert "Agent 2" in result

    def test_get_agent_details_not_found(self):
        r"""Test getting details of a non-existent agent."""
        agent_registry = {
            "agent1": AgentCard("agent1", "Agent 1", ["skill1"]),
        }

        toolkit = AgentDiscoveryToolkit("agent1", agent_registry)
        result = toolkit.get_agent_details("nonexistent")

        assert "not found" in result.lower()


class TestMailboxSociety:
    r"""Test cases for MailboxSociety class."""

    def test_society_creation(self):
        r"""Test creating a mailbox society."""
        society = MailboxSociety("TestSociety")

        assert society.name == "TestSociety"
        assert len(society.agents) == 0
        assert len(society.agent_cards) == 0

    @pytest.mark.model_backend
    def test_register_agent(self):
        r"""Test registering an agent in the society."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Assistant", content="You are a helpful assistant."
            ),
            model=model,
        )

        card = AgentCard(
            agent_id="agent1",
            description="A test agent",
            capabilities=["chat"],
        )

        society.register_agent(agent, card)

        assert "agent1" in society.agents
        assert "agent1" in society.agent_cards
        assert "agent1" in society.message_router

    @pytest.mark.model_backend
    def test_register_duplicate_agent(self):
        r"""Test that registering a duplicate agent raises an error."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Assistant", content="You are a helpful assistant."
            ),
            model=model,
        )

        card = AgentCard(
            agent_id="agent1",
            description="A test agent",
            capabilities=["chat"],
        )

        society.register_agent(agent, card)

        # Try to register again with same ID
        with pytest.raises(ValueError, match="already registered"):
            society.register_agent(agent, card)

    @pytest.mark.model_backend
    def test_unregister_agent(self):
        r"""Test unregistering an agent from the society."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Assistant", content="You are a helpful assistant."
            ),
            model=model,
        )

        card = AgentCard(
            agent_id="agent1",
            description="A test agent",
            capabilities=["chat"],
        )

        society.register_agent(agent, card)
        society.unregister_agent("agent1")

        assert "agent1" not in society.agents
        assert "agent1" not in society.agent_cards

    def test_unregister_nonexistent_agent(self):
        r"""Test that unregistering a non-existent agent raises an error."""
        society = MailboxSociety("TestSociety")

        with pytest.raises(ValueError, match="not found"):
            society.unregister_agent("nonexistent")

    @pytest.mark.model_backend
    def test_get_agent(self):
        r"""Test getting an agent by ID."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Assistant", content="You are a helpful assistant."
            ),
            model=model,
        )

        card = AgentCard(
            agent_id="agent1",
            description="A test agent",
            capabilities=["chat"],
        )

        society.register_agent(agent, card)

        retrieved_agent = society.get_agent("agent1")
        assert retrieved_agent is not None
        assert retrieved_agent == agent

    def test_get_nonexistent_agent(self):
        r"""Test getting a non-existent agent returns None."""
        society = MailboxSociety("TestSociety")

        agent = society.get_agent("nonexistent")
        assert agent is None

    @pytest.mark.model_backend
    def test_search_agents(self):
        r"""Test searching for agents."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        # Create and register multiple agents
        card1 = AgentCard(
            agent_id="agent1",
            description="A helpful assistant",
            capabilities=["chat"],
            tags=["assistant"],
        )

        card2 = AgentCard(
            agent_id="agent2",
            description="A data analyst",
            capabilities=["analyze"],
            tags=["analyst"],
        )

        agent1 = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Assistant1", content="Agent 1"
            ),
            model=model,
        )

        agent2 = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Assistant2", content="Agent 2"
            ),
            model=model,
        )

        society.register_agent(agent1, card1)
        society.register_agent(agent2, card2)

        # Search by query
        results = society.search_agents(query="helpful")
        assert len(results) == 1
        assert results[0].agent_id == "agent1"

        # Search by tag
        results = society.search_agents(tags=["analyst"])
        assert len(results) == 1
        assert results[0].agent_id == "agent2"

        # Search by capability
        results = society.search_agents(capabilities=["chat"])
        assert len(results) == 1
        assert results[0].agent_id == "agent1"

    @pytest.mark.model_backend
    def test_broadcast_message(self):
        r"""Test broadcasting a message to all agents."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        # Register multiple agents
        for i in range(1, 4):
            agent = ChatAgent(
                system_message=BaseMessage.make_assistant_message(
                    role_name=f"Agent{i}", content=f"Agent {i}"
                ),
                model=model,
            )
            card = AgentCard(
                agent_id=f"agent{i}",
                description=f"Agent {i}",
                capabilities=["chat"],
            )
            society.register_agent(agent, card)

        # Broadcast from agent1
        count = society.broadcast_message(
            "agent1", "Hello everyone", subject="Announcement"
        )

        assert count == 2  # Message sent to 2 other agents
        assert len(society.message_router["agent2"]) == 1
        assert len(society.message_router["agent3"]) == 1
        assert len(society.message_router["agent1"]) == 0  # No self-message

    def test_broadcast_from_nonexistent_agent(self):
        r"""Test that broadcasting from a non-existent agent raises error."""
        society = MailboxSociety("TestSociety")

        with pytest.raises(ValueError, match="not found"):
            society.broadcast_message("nonexistent", "Hello")

    @pytest.mark.model_backend
    def test_get_mailbox_count(self):
        r"""Test getting mailbox message count."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        # Register agents
        agent1 = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Agent1", content="Agent 1"
            ),
            model=model,
        )
        card1 = AgentCard(
            agent_id="agent1", description="Agent 1", capabilities=["chat"]
        )
        society.register_agent(agent1, card1)

        # Initially empty
        count = society.get_mailbox_count("agent1")
        assert count == 0

        # Add messages
        society.message_router["agent1"].append(
            MailboxMessage("agent2", "agent1", "Test")
        )
        count = society.get_mailbox_count("agent1")
        assert count == 1

    def test_get_mailbox_count_nonexistent(self):
        r"""Test getting mailbox count for non-existent agent."""
        society = MailboxSociety("TestSociety")

        with pytest.raises(ValueError, match="not found"):
            society.get_mailbox_count("nonexistent")

    @pytest.mark.model_backend
    def test_clear_mailbox(self):
        r"""Test clearing an agent's mailbox."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        agent1 = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Agent1", content="Agent 1"
            ),
            model=model,
        )
        card1 = AgentCard(
            agent_id="agent1", description="Agent 1", capabilities=["chat"]
        )
        society.register_agent(agent1, card1)

        # Add messages
        society.message_router["agent1"].append(
            MailboxMessage("agent2", "agent1", "Test 1")
        )
        society.message_router["agent1"].append(
            MailboxMessage("agent2", "agent1", "Test 2")
        )

        # Clear mailbox
        count = society.clear_mailbox("agent1")
        assert count == 2
        assert len(society.message_router["agent1"]) == 0

    def test_society_str(self):
        r"""Test string representation of society."""
        society = MailboxSociety("TestSociety")

        str_repr = str(society)
        assert "TestSociety" in str_repr
        assert "total=0" in str_repr


class TestMailboxSocietyProcessing:
    r"""Test cases for MailboxSociety message processing."""

    def test_society_initialization_with_params(self):
        r"""Test creating society with custom parameters."""
        society = MailboxSociety(
            name="TestSociety", max_iterations=5, process_interval=0.1
        )

        assert society.name == "TestSociety"
        assert society.max_iterations == 5
        assert society.process_interval == 0.1
        assert not society._running
        assert not society._stop_requested

    def test_set_message_handler(self):
        r"""Test setting a custom message handler."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Agent", content="Test agent"
            ),
            model=model,
        )

        card = AgentCard(
            agent_id="agent1", description="Test agent", capabilities=["test"]
        )

        society.register_agent(agent, card)

        # Set a custom handler
        def custom_handler(agent, message):
            pass

        society.set_message_handler("agent1", custom_handler)

        assert "agent1" in society._message_handlers
        assert society._message_handlers["agent1"] == custom_handler

    def test_set_message_handler_invalid_agent(self):
        r"""Test setting handler for non-existent agent raises error."""
        society = MailboxSociety("TestSociety")

        def custom_handler(agent, message):
            pass

        with pytest.raises(ValueError, match="not found"):
            society.set_message_handler("nonexistent", custom_handler)

    @pytest.mark.asyncio
    async def test_process_messages_once(self):
        r"""Test processing messages once."""
        society = MailboxSociety("TestSociety")

        # Track processed messages
        processed = []

        def handler(agent, message):
            processed.append(message)

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        # Register agents
        for i in range(1, 3):
            agent = ChatAgent(
                system_message=BaseMessage.make_assistant_message(
                    role_name=f"Agent{i}", content=f"Agent {i}"
                ),
                model=model,
            )
            card = AgentCard(
                agent_id=f"agent{i}",
                description=f"Agent {i}",
                capabilities=["test"],
            )
            society.register_agent(agent, card)
            society.set_message_handler(f"agent{i}", handler)

        # Add messages
        society.message_router["agent1"].append(
            MailboxMessage("agent2", "agent1", "Message 1")
        )
        society.message_router["agent2"].append(
            MailboxMessage("agent1", "agent2", "Message 2")
        )

        # Process messages
        count = await society._process_messages_once()

        assert count == 2
        assert len(processed) == 2
        assert len(society.message_router["agent1"]) == 0
        assert len(society.message_router["agent2"]) == 0

    @pytest.mark.asyncio
    async def test_run_async(self):
        r"""Test async message processing."""
        society = MailboxSociety(
            "TestSociety", max_iterations=2, process_interval=0.1
        )

        processed_messages = []

        def handler(agent, message):
            processed_messages.append(message.content)

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Agent", content="Test agent"
            ),
            model=model,
        )

        card = AgentCard(
            agent_id="agent1", description="Test agent", capabilities=["test"]
        )

        society.register_agent(agent, card)
        society.set_message_handler("agent1", handler)

        # Add a message
        society.message_router["agent1"].append(
            MailboxMessage("agent2", "agent1", "Test message")
        )

        # Run processing
        await society.run_async()

        # Check that message was processed
        assert len(processed_messages) == 1
        assert "Test message" in processed_messages
        assert society._iteration_count == 2

    def test_stop(self):
        r"""Test stopping the society."""
        society = MailboxSociety("TestSociety")

        # Can't stop if not running
        society.stop()  # Should just log a warning

        # Start and stop
        society._running = True
        society.stop()

        assert society._stop_requested

    def test_pause_resume(self):
        r"""Test pausing and resuming the society."""
        society = MailboxSociety("TestSociety")

        # Can't pause/resume if not running
        society.pause()  # Should log warning
        society.resume()  # Should log warning

        # Test pause/resume when running
        society._running = True

        assert society._pause_event.is_set()  # Not paused initially

        society.pause()
        assert not society._pause_event.is_set()  # Now paused

        society.resume()
        assert society._pause_event.is_set()  # Resumed

    def test_reset(self):
        r"""Test resetting the society."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Agent", content="Test agent"
            ),
            model=model,
        )

        card = AgentCard(
            agent_id="agent1", description="Test agent", capabilities=["test"]
        )

        society.register_agent(agent, card)

        # Add messages and set state
        society.message_router["agent1"].append(
            MailboxMessage("agent2", "agent1", "Test")
        )
        society._iteration_count = 5

        def handler(agent, message):
            pass

        society.set_message_handler("agent1", handler)

        # Reset
        society.reset()

        assert len(society.message_router["agent1"]) == 0
        assert society._iteration_count == 0
        assert not society._stop_requested
        assert len(society._message_handlers) == 0

    def test_reset_while_running(self):
        r"""Test that reset fails while running."""
        society = MailboxSociety("TestSociety")
        society._running = True

        society.reset()  # Should log warning and not reset

        # State should remain unchanged (can't verify much without state)
        assert society._running

    @pytest.mark.asyncio
    @pytest.mark.model_backend
    async def test_default_handler_uses_agent_step(self):
        r"""Test that default handler uses ChatAgent.step when no custom
        handler is set."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        # Create agent WITHOUT setting a custom handler
        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="TestAgent",
                content="You are a test agent. Respond briefly.",
            ),
            model=model,
        )

        card = AgentCard(
            agent_id="agent1",
            description="Test agent",
            capabilities=["test"],
        )

        society.register_agent(agent, card)
        # NOTE: Not setting a custom handler - should use default

        # Add a message to the agent's mailbox
        society.message_router["agent1"].append(
            MailboxMessage(
                sender_id="agent2",
                recipient_id="agent1",
                content="Hello, please acknowledge this message.",
                subject="Test Message",
            )
        )

        # Verify mailbox has the message
        assert len(society.message_router["agent1"]) == 1

        # Process messages - should use default handler which calls
        # agent.step()
        count = await society._process_messages_once()

        # Verify message was processed
        assert count == 1
        assert len(society.message_router["agent1"]) == 0

        # Verify agent has memory of processing (agent.step was called)
        # The agent should have at least 2 messages in memory:
        # 1. User message created by default handler
        # 2. Assistant response
        assert len(agent.memory.get_context()) >= 2

    @pytest.mark.model_backend
    def test_default_message_handler_direct(self):
        r"""Test the _default_message_handler method directly."""
        society = MailboxSociety("TestSociety")

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="TestAgent", content="You are a test agent."
            ),
            model=model,
        )

        card = AgentCard(
            agent_id="agent1",
            description="Test agent",
            capabilities=["test"],
        )

        society.register_agent(agent, card)

        # Create a message
        message = MailboxMessage(
            sender_id="agent2",
            recipient_id="agent1",
            content="Test content",
            subject="Test subject",
        )

        # Get initial memory length
        initial_memory_length = len(agent.memory.get_context())

        # Call the default handler directly
        society._default_message_handler(agent, message)

        # Verify agent.step was called by checking memory increased
        # Should have at least one more message (the user message passed to
        # step)
        assert len(agent.memory.get_context()) > initial_memory_length
