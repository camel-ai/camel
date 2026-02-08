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
Example demonstrating the mailbox-based multi-agent system with entry point.

This example shows how to:
1. Create a mailbox society with processing entry point
2. Register multiple agents with different capabilities
3. Set up message handlers for agents
4. Use the run() entry point to process messages automatically
5. Demonstrate pause/resume/stop controls
"""

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies import AgentCard, MailboxMessage, MailboxSociety
from camel.types import ModelPlatformType, ModelType


def main():
    r"""Demonstrate mailbox society with entry point."""
    print("=" * 70)
    print("Mailbox Society with Entry Point Example")
    print("=" * 70)

    # Create society with custom parameters
    society = MailboxSociety(
        name="Collaborative Team",
        max_iterations=5,  # Process for 5 iterations
        process_interval=0.5,  # Check every 0.5 seconds
    )
    print(f"\n✓ Created society: {society.name}")
    print(f"  Max iterations: {society.max_iterations}")
    print(f"  Process interval: {society.process_interval}s")

    # Create model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Create agents
    print("\n--- Creating Agents ---")

    # Agent 1: Task Coordinator
    coordinator = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Coordinator",
            content=(
                "You are a task coordinator. When you receive messages, "
                "you coordinate tasks and delegate to team members."
            ),
        ),
        model=model,
    )

    coordinator_card = AgentCard(
        agent_id="coordinator",
        description="Coordinates tasks and delegates work",
        capabilities=["coordination", "task_management"],
        tags=["coordinator", "manager"],
    )

    # Agent 2: Worker
    worker = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Worker",
            content=(
                "You are a worker agent. When you receive tasks, "
                "you work on them and report back."
            ),
        ),
        model=model,
    )

    worker_card = AgentCard(
        agent_id="worker",
        description="Executes assigned tasks",
        capabilities=["execution", "implementation"],
        tags=["worker", "executor"],
    )

    # Register agents
    society.register_agent(coordinator, coordinator_card)
    society.register_agent(worker, worker_card)
    print(f"✓ Registered {len(society.agents)} agents")

    # Set up custom message handlers
    print("\n--- Setting Up Message Handlers ---")

    processed_messages = []

    def coordinator_handler(agent: ChatAgent, message: MailboxMessage):
        r"""Custom handler for coordinator agent."""
        print(f"\n[Coordinator] Received from {message.sender_id}:")
        print(f"  Subject: {message.subject}")
        print(f"  Content: {message.content}")
        processed_messages.append(("coordinator", message))

        # Coordinator might send a response back
        if "request" in message.content.lower():
            # Simulate sending a response
            response = MailboxMessage(
                sender_id="coordinator",
                recipient_id=message.sender_id,
                content="Task acknowledged and assigned to worker",
                subject=f"Re: {message.subject}",
            )
            society.message_router[message.sender_id].append(response)
            print("  → Sent response back")

    def worker_handler(agent: ChatAgent, message: MailboxMessage):
        r"""Custom handler for worker agent."""
        print(f"\n[Worker] Received from {message.sender_id}:")
        print(f"  Subject: {message.subject}")
        print(f"  Content: {message.content}")
        processed_messages.append(("worker", message))

        # Worker processes and might report back
        if "task" in message.content.lower():
            response = MailboxMessage(
                sender_id="worker",
                recipient_id="coordinator",
                content="Task completed successfully",
                subject="Task Status Update",
            )
            society.message_router["coordinator"].append(response)
            print("  → Sent completion status to coordinator")

    society.set_message_handler("coordinator", coordinator_handler)
    society.set_message_handler("worker", worker_handler)
    print("✓ Set up custom message handlers")

    # Add initial messages to mailboxes
    print("\n--- Adding Initial Messages ---")

    # Worker sends a request to coordinator
    msg1 = MailboxMessage(
        sender_id="worker",
        recipient_id="coordinator",
        content="I have completed my previous task. Request new assignment.",
        subject="Task Request",
    )
    society.message_router["coordinator"].append(msg1)
    print("✓ Worker → Coordinator: Task request")

    # Check mailbox counts
    print("\nMailbox status before processing:")
    for agent_id in society.agents.keys():
        count = society.get_mailbox_count(agent_id)
        print(f"  {agent_id}: {count} message(s)")

    # Use the entry point to process messages
    print("\n--- Starting Message Processing (Entry Point) ---")
    print(
        "The society will now process messages automatically "
        "using the run() entry point..."
    )
    print()

    # Run the society (this will process messages for max_iterations)
    society.run()

    # Check results
    print("\n--- Processing Complete ---")
    print(f"Total iterations: {society._iteration_count}")
    print(f"Messages processed: {len(processed_messages)}")

    print("\nProcessed messages:")
    for i, (agent_id, msg) in enumerate(processed_messages, 1):
        print(f"  {i}. [{agent_id}] from {msg.sender_id}: {msg.subject}")

    # Check final mailbox counts
    print("\nMailbox status after processing:")
    for agent_id in society.agents.keys():
        count = society.get_mailbox_count(agent_id)
        print(f"  {agent_id}: {count} message(s)")

    # Demonstrate reset
    print("\n--- Demonstrating Reset ---")
    society.reset()
    print("✓ Society reset")
    print(f"  Iteration count: {society._iteration_count}")
    print(f"  Message handlers cleared: {len(society._message_handlers)}")

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


def demonstrate_async_usage():
    r"""Demonstrate async usage of the society."""
    import asyncio

    print("\n\n" + "=" * 70)
    print("Async Usage Example")
    print("=" * 70)

    async def async_example():
        society = MailboxSociety(
            name="Async Team", max_iterations=3, process_interval=0.2
        )

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        # Create simple agent
        agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Agent", content="A simple agent"
            ),
            model=model,
        )

        card = AgentCard(
            agent_id="agent1",
            description="A simple agent",
            capabilities=["basic"],
        )

        society.register_agent(agent, card)

        # Add a message
        society.message_router["agent1"].append(
            MailboxMessage(
                sender_id="system",
                recipient_id="agent1",
                content="Test async message",
            )
        )

        print(f"Starting async processing for {society.name}...")

        # Use async entry point
        await society.run_async()

        print("Async processing completed!")
        print(f"  Iterations: {society._iteration_count}")

    # Run the async example
    asyncio.run(async_example())

    print("=" * 70)


if __name__ == "__main__":
    main()
    demonstrate_async_usage()
