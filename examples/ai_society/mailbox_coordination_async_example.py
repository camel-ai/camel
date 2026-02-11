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
Full example demonstrating autonomous agent coordination in MailboxSociety.

This example shows how ChatAgents autonomously coordinate using
MailboxToolkit and AgentDiscoveryToolkit through the run_async interface
with initial messages. The agents work together on a research project:

1. Project Manager receives initial task and discovers team members
2. Researcher receives task assignment, conducts research
3. Writer receives research findings, creates article
4. Reviewer receives draft, provides feedback

Key Features Demonstrated:
- Using run_async() with initial_messages parameter
- Autonomous agent coordination through message passing
- Agents discover collaborators using AgentDiscoveryToolkit
- Agents communicate using MailboxToolkit
- Complete workflow from single initial task
"""

import asyncio

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies import AgentCard, MailboxSociety
from camel.toolkits import AgentDiscoveryToolkit, MailboxToolkit
from camel.types import ModelPlatformType, ModelType


def create_agent(
    agent_id: str,
    role_name: str,
    description: str,
    capabilities: list[str],
    tags: list[str],
    system_instructions: str,
    society: MailboxSociety,
) -> tuple[ChatAgent, AgentCard]:
    r"""Create an agent equipped with mailbox and discovery toolkits.

    Args:
        agent_id (str): Unique identifier for the agent.
        role_name (str): Role name for the agent.
        description (str): Description of the agent's purpose.
        capabilities (list[str]): List of agent capabilities.
        tags (list[str]): Tags for categorizing the agent.
        system_instructions (str): Specific instructions for this
            agent's role.
        society (MailboxSociety): The society to register the agent with.

    Returns:
        tuple[ChatAgent, AgentCard]: The created agent and its card.
    """
    # Create agent card for discovery
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

    # Create system message with role-specific instructions
    system_message = BaseMessage.make_assistant_message(
        role_name=role_name,
        content=(
            f"You are {role_name}, an AI agent with ID '{agent_id}'.\n\n"
            f"ROLE: {description}\n"
            f"CAPABILITIES: {', '.join(capabilities)}\n\n"
            f"{system_instructions}\n\n"
            "AVAILABLE TOOLS:\n"
            "- Use discovery tools to find other agents by their "
            "capabilities\n"
            "- Use mailbox tools to send and receive messages\n"
            "- Check your mailbox regularly for new tasks using "
            "check_messages and receive_messages\n"
            "- Send results to appropriate team members using "
            "send_message\n\n"
            "Work autonomously: Check your mailbox, process tasks, "
            "coordinate with others, and complete your work. "
            "Be proactive!"
        ),
    )

    # Create toolkits with shared access to society data
    mailbox_toolkit = MailboxToolkit(
        agent_id=agent_id,
        message_router=society.message_router,
    )

    discovery_toolkit = AgentDiscoveryToolkit(
        agent_id=agent_id,
        agent_registry=society.agent_cards,
    )

    # Create agent with both toolkits
    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=[*mailbox_toolkit.get_tools(), *discovery_toolkit.get_tools()],
    )

    return agent, card


async def main():
    r"""Demonstrate autonomous agent coordination with run_async."""
    print("=" * 70)
    print("AUTONOMOUS AGENT COORDINATION WITH RUN_ASYNC")
    print("Scenario: Research Team Project on 'AI Safety in Healthcare'")
    print("=" * 70)

    # Create the mailbox society with finite iterations for demo
    society = MailboxSociety(
        name="AI Research Team",
        max_iterations=15,  # Limit iterations for demo
        process_interval=0.1,  # Quick processing
    )
    print(f"\n✓ Created society: {society.name}")

    # ========================================================================
    # PHASE 1: Create Team Members
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: Creating Team Members")
    print("=" * 70)

    # Project Manager - coordinates the team
    manager_agent, manager_card = create_agent(
        agent_id="project_manager",
        role_name="Project Manager",
        description=(
            "Coordinates team and assigns tasks based on capabilities"
        ),
        capabilities=["project_management", "coordination"],
        tags=["management"],
        system_instructions=(
            "When you receive a project task:\n"
            "1. Use discovery tools to find team members\n"
            "2. Identify who can do research (capability: 'research')\n"
            "3. Send them a clear research task via send_message\n"
            "4. Keep checking your mailbox for status updates"
        ),
        society=society,
    )
    society.register_agent(manager_agent, manager_card)
    print(f"✓ Registered: {manager_card.agent_id}")

    # Researcher - does research
    researcher_agent, researcher_card = create_agent(
        agent_id="researcher",
        role_name="Research Specialist",
        description="Conducts research and gathers information",
        capabilities=["research", "data_analysis"],
        tags=["research"],
        system_instructions=(
            "When you receive a research task:\n"
            "1. Conduct thorough research on the topic\n"
            "2. Use discovery tools to find the writer "
            "(capability: 'writing')\n"
            "3. Send your research findings to the writer via "
            "send_message\n"
            "4. Include key points about risks, benefits, and practices"
        ),
        society=society,
    )
    society.register_agent(researcher_agent, researcher_card)
    print(f"✓ Registered: {researcher_card.agent_id}")

    # Writer - creates content
    writer_agent, writer_card = create_agent(
        agent_id="writer",
        role_name="Content Writer",
        description="Writes articles based on research",
        capabilities=["writing", "content_creation"],
        tags=["writing"],
        system_instructions=(
            "When you receive research findings:\n"
            "1. Write a clear, engaging article based on the research\n"
            "2. Make it 3-4 paragraphs, accessible to general audience\n"
            "3. Use discovery tools to find the reviewer "
            "(capability: 'review')\n"
            "4. Send your article draft to the reviewer via send_message"
        ),
        society=society,
    )
    society.register_agent(writer_agent, writer_card)
    print(f"✓ Registered: {writer_card.agent_id}")

    # Reviewer - reviews content
    reviewer_agent, reviewer_card = create_agent(
        agent_id="reviewer",
        role_name="Quality Reviewer",
        description="Reviews content for quality and accuracy",
        capabilities=["review", "quality_assurance"],
        tags=["review"],
        system_instructions=(
            "When you receive an article to review:\n"
            "1. Review for clarity, accuracy, and quality\n"
            "2. Provide constructive feedback\n"
            "3. Send feedback to the writer via send_message\n"
            "4. Send completion notice to project_manager via send_message"
        ),
        society=society,
    )
    society.register_agent(reviewer_agent, reviewer_card)
    print(f"✓ Registered: {reviewer_card.agent_id}")

    print(f"\n✓ Team assembled: {len(society.agents)} agents ready")

    # ========================================================================
    # PHASE 2: Send Initial Task and Run Autonomously
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: Starting Autonomous Coordination")
    print("=" * 70)

    # Prepare initial task message for the project manager
    initial_task = (
        "NEW PROJECT: Write a comprehensive article about "
        "'AI Safety in Healthcare'.\n\n"
        "Your task:\n"
        "1. Discover available team members\n"
        "2. Assign research task to someone with 'research' capability\n"
        "3. The research should cover risks, benefits, and best practices\n"
        "4. Monitor progress and coordinate the team\n\n"
        "Use your tools to discover team members and coordinate via messages."
    )

    print("\nInitial task message sent to project_manager:")
    print(f"  {initial_task[:100]}...")

    print("\n" + "-" * 70)
    print("Starting autonomous processing with run_async()...")
    print("Agents will now coordinate independently!")
    print("-" * 70 + "\n")

    # Run the society with initial message
    # Agents will autonomously check mailboxes, use tools, and coordinate
    await society.run_async(
        initial_messages={
            "project_manager": initial_task,
        }
    )

    # ========================================================================
    # PHASE 3: Check Final Status
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: Coordination Complete - Final Status")
    print("=" * 70)

    print(f"\nTotal iterations: {society._iteration_count}")
    print("\nFinal mailbox status:")
    for agent_id in society.agents.keys():
        count = society.get_mailbox_count(agent_id)
        status = "unread message(s)" if count > 0 else "mailbox clear"
        print(f"  {agent_id}: {count} {status}")

    print("\n" + "=" * 70)
    print("COORDINATION EXAMPLE COMPLETED!")
    print("=" * 70)
    print("\nKey Achievements:")
    print("✓ Used run_async() with initial_messages parameter")
    print("✓ Single initial task triggered complete workflow")
    print("✓ Agents autonomously discovered collaborators")
    print("✓ Agents autonomously coordinated via messages")
    print("✓ Multi-step project completed without manual intervention")
    print("\nThis demonstrates the power of autonomous agent coordination")
    print("using MailboxSociety's run_async interface!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
