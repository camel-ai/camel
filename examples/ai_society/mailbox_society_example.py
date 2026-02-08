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

"""
Example demonstrating the mailbox-based multi-agent system.

This example shows how to:
1. Create a mailbox society
2. Register multiple agents with different capabilities
3. Equip agents with mailbox and discovery toolkits
4. Enable agents to discover and communicate with each other
5. Demonstrate agent-to-agent message passing
"""

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies import AgentCard, MailboxSociety
from camel.toolkits import AgentDiscoveryToolkit, MailboxToolkit
from camel.types import ModelPlatformType, ModelType


def create_agent_with_mailbox(
    agent_id: str,
    role_name: str,
    description: str,
    capabilities: list[str],
    tags: list[str],
    society: MailboxSociety,
) -> tuple[ChatAgent, AgentCard]:
    r"""Create an agent with mailbox and discovery capabilities.

    Args:
        agent_id (str): Unique identifier for the agent.
        role_name (str): Role name for the agent.
        description (str): Description of the agent's purpose.
        capabilities (list[str]): List of agent capabilities.
        tags (list[str]): Tags for categorizing the agent.
        society (MailboxSociety): The society to register the agent with.

    Returns:
        tuple[ChatAgent, AgentCard]: The created agent and its card.
    """
    # Create the agent card
    card = AgentCard(
        agent_id=agent_id,
        description=description,
        capabilities=capabilities,
        tags=tags,
    )

    # Create model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Create system message
    system_message = BaseMessage.make_assistant_message(
        role_name=role_name,
        content=(
            f"You are {role_name}, an AI agent with ID '{agent_id}'.\n"
            f"Your role: {description}\n"
            f"Your capabilities: {', '.join(capabilities)}\n\n"
            "You can communicate with other agents using your mailbox tools. "
            "Use the agent discovery tools to find other agents and learn "
            "about their capabilities. "
            "When working on tasks, collaborate with other agents by "
            "sending them messages."
        ),
    )

    # Create mailbox and discovery toolkits
    mailbox_toolkit = MailboxToolkit(
        agent_id=agent_id,
        message_router=society.message_router,
    )

    discovery_toolkit = AgentDiscoveryToolkit(
        agent_id=agent_id,
        agent_registry=society.agent_cards,
    )

    # Create the agent with toolkits
    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=[*mailbox_toolkit.get_tools(), *discovery_toolkit.get_tools()],
    )

    return agent, card


def main():
    r"""Demonstrate mailbox-based multi-agent communication."""
    print("=" * 70)
    print("Mailbox-Based Multi-Agent System Example")
    print("=" * 70)

    # Create the mailbox society
    society = MailboxSociety(name="Research Team")
    print(f"\n✓ Created society: {society.name}")

    # Create and register agents
    print("\n--- Creating Agents ---")

    # Research agent - specializes in finding information
    researcher_agent, researcher_card = create_agent_with_mailbox(
        agent_id="researcher",
        role_name="Research Specialist",
        description="Specializes in finding and analyzing information",
        capabilities=["research", "data_analysis", "literature_review"],
        tags=["research", "analysis"],
        society=society,
    )
    society.register_agent(researcher_agent, researcher_card)
    print(f"✓ Registered: {researcher_card.agent_id}")

    # Writer agent - specializes in content creation
    writer_agent, writer_card = create_agent_with_mailbox(
        agent_id="writer",
        role_name="Content Writer",
        description="Specializes in creating well-written content",
        capabilities=["writing", "editing", "summarization"],
        tags=["writing", "content"],
        society=society,
    )
    society.register_agent(writer_agent, writer_card)
    print(f"✓ Registered: {writer_card.agent_id}")

    # Reviewer agent - specializes in quality assurance
    reviewer_agent, reviewer_card = create_agent_with_mailbox(
        agent_id="reviewer",
        role_name="Quality Reviewer",
        description="Specializes in reviewing and improving content quality",
        capabilities=["review", "feedback", "quality_assurance"],
        tags=["review", "quality"],
        society=society,
    )
    society.register_agent(reviewer_agent, reviewer_card)
    print(f"✓ Registered: {reviewer_card.agent_id}")

    print(f"\n✓ Society now has {len(society.agents)} agents")

    # Demonstrate agent discovery
    print("\n--- Agent Discovery ---")
    researcher_discovery = AgentDiscoveryToolkit(
        "researcher", society.agent_cards
    )

    # List all agents
    print("\nResearcher lists all available agents:")
    result = researcher_discovery.list_all_agents()
    print(result)

    # Search for agents by capability
    print("\nResearcher searches for agents with 'writing' capability:")
    result = researcher_discovery.search_agents_by_capability("writing")
    print(result)

    # Get details of a specific agent
    print("\nResearcher gets details about the writer:")
    result = researcher_discovery.get_agent_details("writer")
    print(result)

    # Demonstrate message passing
    print("\n--- Message Passing ---")
    researcher_mailbox = MailboxToolkit(
        "researcher", society.message_router
    )
    writer_mailbox = MailboxToolkit("writer", society.message_router)
    reviewer_mailbox = MailboxToolkit("reviewer", society.message_router)

    # Researcher sends a message to writer
    print("\n1. Researcher sends a task to Writer:")
    result = researcher_mailbox.send_message(
        recipient_id="writer",
        content=(
            "I've completed research on AI agents. "
            "Please write a summary article about the findings."
        ),
        subject="Article Writing Task",
    )
    print(f"   {result}")

    # Writer checks messages
    print("\n2. Writer checks mailbox:")
    result = writer_mailbox.check_messages()
    print(f"   {result}")

    # Writer receives and reads the message
    print("\n3. Writer receives the message:")
    result = writer_mailbox.receive_messages(max_messages=1)
    print(f"   {result}")

    # Writer sends message to reviewer
    print("\n4. Writer sends draft to Reviewer:")
    result = writer_mailbox.send_message(
        recipient_id="reviewer",
        content="I've written the article draft. Please review it.",
        subject="Article Review Request",
    )
    print(f"   {result}")

    # Reviewer receives and reads the message
    print("\n5. Reviewer receives the message:")
    result = reviewer_mailbox.receive_messages(max_messages=1)
    print(f"   {result}")

    # Demonstrate broadcast
    print("\n--- Broadcast Message ---")
    print("\nReviewer broadcasts a message to all agents:")
    count = society.broadcast_message(
        sender_id="reviewer",
        content=(
            "Team meeting at 3 PM today to discuss the project progress."
        ),
        subject="Team Meeting Announcement",
    )
    print(f"✓ Message broadcast to {count} agents")

    # Check mailboxes
    print("\nMailbox status:")
    for agent_id in ["researcher", "writer", "reviewer"]:
        count = society.get_mailbox_count(agent_id)
        print(f"  {agent_id}: {count} message(s)")

    # Demonstrate peek functionality
    print("\n--- Peek at Messages ---")
    print("\nResearcher peeks at messages without removing them:")
    result = researcher_mailbox.peek_messages(max_messages=2)
    print(result)

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
