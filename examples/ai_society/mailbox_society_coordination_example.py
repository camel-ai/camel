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

This example shows a realistic scenario where ChatAgents autonomously use
MailboxToolkit and AgentDiscoveryToolkit to coordinate on a project:

1. A Project Manager agent discovers team members using AgentDiscoveryToolkit
2. Assigns tasks by sending messages via MailboxToolkit
3. Team members (Researcher, Writer, Reviewer) autonomously:
   - Check their mailboxes for tasks
   - Complete their work
   - Send results to appropriate team members
   - Coordinate with each other

Key Features Demonstrated:
- Autonomous tool usage by ChatAgents (not manual invocation)
- Agent discovery based on capabilities
- Multi-step coordination workflow
- Message passing between agents
- Collaborative task completion
"""

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
        system_instructions (str): Specific instructions for this agent's role.
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
            "- Check your mailbox regularly for new tasks\n"
            "- Send results to appropriate team members\n\n"
            "Always use the tools provided to accomplish your tasks. "
            "Be proactive in checking messages and coordinating with others."
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


def run_agent_step(
    agent: ChatAgent, agent_id: str, prompt: str, step_description: str
):
    r"""Execute one step for an agent and display the interaction.

    Args:
        agent (ChatAgent): The agent to run.
        agent_id (str): Agent identifier for display.
        prompt (str): The user prompt to send to the agent.
        step_description (str): Description of what this step does.
    """
    print(f"\n{'='*70}")
    print(f"[{agent_id.upper()}] {step_description}")
    print(f"{'='*70}")
    print(f"Prompt: {prompt}")
    print(f"\n{'-'*70}")

    # Create user message
    user_message = BaseMessage.make_user_message(
        role_name="User", content=prompt
    )

    # Agent processes and responds (will use tools autonomously)
    response = agent.step(user_message)

    print(f"Response: {response.msg.content}")
    print(f"{'-'*70}")


def main():
    r"""Demonstrate full autonomous agent coordination."""
    print("=" * 70)
    print("AUTONOMOUS AGENT COORDINATION EXAMPLE")
    print("Scenario: Research Team Project on 'AI Safety in Healthcare'")
    print("=" * 70)

    # Create the mailbox society
    society = MailboxSociety(name="AI Research Team")
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
            "Coordinates team and assigns tasks based on member capabilities"
        ),
        capabilities=["project_management", "task_assignment", "coordination"],
        tags=["management", "coordination"],
        system_instructions=(
            "Your job is to:\n"
            "1. Discover available team members using discovery tools\n"
            "2. Assign tasks to appropriate team members based on their "
            "capabilities\n"
            "3. Send clear task assignments via messages\n"
            "4. Track project progress"
        ),
        society=society,
    )
    society.register_agent(manager_agent, manager_card)
    print(f"✓ Registered: {manager_card.agent_id}")

    # Researcher - does research
    researcher_agent, researcher_card = create_agent(
        agent_id="researcher",
        role_name="Research Specialist",
        description=(
            "Conducts research and gathers information on assigned topics"
        ),
        capabilities=["research", "data_analysis", "literature_review"],
        tags=["research", "analysis"],
        system_instructions=(
            "Your job is to:\n"
            "1. Check your mailbox for research assignments\n"
            "2. Conduct thorough research on assigned topics\n"
            "3. Send research findings to the writer via messages"
        ),
        society=society,
    )
    society.register_agent(researcher_agent, researcher_card)
    print(f"✓ Registered: {researcher_card.agent_id}")

    # Writer - creates content
    writer_agent, writer_card = create_agent(
        agent_id="writer",
        role_name="Content Writer",
        description="Writes articles and documentation based on research",
        capabilities=["writing", "documentation", "content_creation"],
        tags=["writing", "content"],
        system_instructions=(
            "Your job is to:\n"
            "1. Check your mailbox for research findings\n"
            "2. Write clear and engaging content based on the research\n"
            "3. Send your draft to the reviewer via messages"
        ),
        society=society,
    )
    society.register_agent(writer_agent, writer_card)
    print(f"✓ Registered: {writer_card.agent_id}")

    # Reviewer - reviews content
    reviewer_agent, reviewer_card = create_agent(
        agent_id="reviewer",
        role_name="Quality Reviewer",
        description="Reviews content for quality, accuracy, and clarity",
        capabilities=["review", "quality_assurance", "feedback"],
        tags=["review", "quality"],
        system_instructions=(
            "Your job is to:\n"
            "1. Check your mailbox for content to review\n"
            "2. Review content for quality and accuracy\n"
            "3. Provide constructive feedback to the writer\n"
            "4. Notify the project manager when review is complete"
        ),
        society=society,
    )
    society.register_agent(reviewer_agent, reviewer_card)
    print(f"✓ Registered: {reviewer_card.agent_id}")

    print(f"\n✓ Team assembled: {len(society.agents)} agents ready")

    # ========================================================================
    # PHASE 2: Project Manager Discovers Team and Assigns Tasks
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: Project Manager Discovers Team and Assigns Tasks")
    print("=" * 70)

    # Step 1: Manager discovers team members
    run_agent_step(
        agent=manager_agent,
        agent_id="project_manager",
        prompt=(
            "We have a new project: 'AI Safety in Healthcare'. "
            "Use the discovery tools to find all available team members "
            "and their capabilities. List what you find."
        ),
        step_description="Discovering team members",
    )

    # Step 2: Manager assigns task to researcher
    run_agent_step(
        agent=manager_agent,
        agent_id="project_manager",
        prompt=(
            "Now use the mailbox tools to send a message to the researcher. "
            "Ask them to research 'AI Safety in Healthcare' and provide "
            "key findings about risks, benefits, and current practices. "
            "Send a clear and specific task assignment."
        ),
        step_description="Assigning research task",
    )

    # ========================================================================
    # PHASE 3: Researcher Receives Task and Conducts Research
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 3: Researcher Works on Assignment")
    print("=" * 70)

    # Step 3: Researcher checks mailbox
    run_agent_step(
        agent=researcher_agent,
        agent_id="researcher",
        prompt=(
            "Check your mailbox for any new assignments. "
            "If you have a message, read it and acknowledge what task "
            "you need to complete."
        ),
        step_description="Checking for assignments",
    )

    # Step 4: Researcher completes research and sends findings
    run_agent_step(
        agent=researcher_agent,
        agent_id="researcher",
        prompt=(
            "Based on the research task you received, provide your research "
            "findings on AI Safety in Healthcare. Include:\n"
            "- Key risks and challenges\n"
            "- Potential benefits\n"
            "- Current best practices\n\n"
            "Then use the discovery tools to find the writer, and send "
            "your research findings to them via the mailbox tools."
        ),
        step_description="Conducting research and sharing findings",
    )

    # ========================================================================
    # PHASE 4: Writer Creates Content
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 4: Writer Creates Content from Research")
    print("=" * 70)

    # Step 5: Writer checks mailbox
    run_agent_step(
        agent=writer_agent,
        agent_id="writer",
        prompt=(
            "Check your mailbox for any research findings or assignments. "
            "Read any messages you have received."
        ),
        step_description="Checking for research findings",
    )

    # Step 6: Writer creates article
    run_agent_step(
        agent=writer_agent,
        agent_id="writer",
        prompt=(
            "Based on the research findings you received, write a brief "
            "article (3-4 paragraphs) about AI Safety in Healthcare. "
            "Make it clear and accessible. Then use the discovery tools "
            "to find the reviewer and send your draft to them for review "
            "via the mailbox tools."
        ),
        step_description="Writing article and sending for review",
    )

    # ========================================================================
    # PHASE 5: Reviewer Provides Feedback
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 5: Reviewer Provides Feedback")
    print("=" * 70)

    # Step 7: Reviewer checks mailbox
    run_agent_step(
        agent=reviewer_agent,
        agent_id="reviewer",
        prompt=(
            "Check your mailbox for any content to review. "
            "Read the message if you have one."
        ),
        step_description="Checking for content to review",
    )

    # Step 8: Reviewer provides feedback
    run_agent_step(
        agent=reviewer_agent,
        agent_id="reviewer",
        prompt=(
            "Review the article you received. Provide constructive feedback "
            "on:\n"
            "- Clarity and readability\n"
            "- Accuracy based on the research\n"
            "- Any improvements needed\n\n"
            "Then send your feedback to the writer, and notify the project "
            "manager that the review is complete using the mailbox tools."
        ),
        step_description="Reviewing and providing feedback",
    )

    # ========================================================================
    # PHASE 6: Check Final Status
    # ========================================================================
    print("\n" + "=" * 70)
    print("PHASE 6: Project Completion - Final Status")
    print("=" * 70)

    # Step 9: Manager checks status
    run_agent_step(
        agent=manager_agent,
        agent_id="project_manager",
        prompt=(
            "Check your mailbox to see if the reviewer has sent any "
            "completion notifications. Summarize the project status."
        ),
        step_description="Checking project status",
    )

    # Display final mailbox status
    print("\n" + "=" * 70)
    print("FINAL MAILBOX STATUS")
    print("=" * 70)
    for agent_id in society.agents.keys():
        count = society.get_mailbox_count(agent_id)
        print(f"  {agent_id}: {count} unread message(s)")

    print("\n" + "=" * 70)
    print("COORDINATION EXAMPLE COMPLETED!")
    print("=" * 70)
    print("\nKey Achievements:")
    print("✓ Agents autonomously used discovery tools to find collaborators")
    print("✓ Agents autonomously sent and received messages")
    print("✓ Multi-step workflow completed through agent coordination")
    print("✓ Each agent fulfilled their role using provided tools")
    print("\nThis demonstrates how ChatAgents can coordinate complex")
    print("tasks using MailboxToolkit and AgentDiscoveryToolkit!")
    print("=" * 70)


if __name__ == "__main__":
    main()
