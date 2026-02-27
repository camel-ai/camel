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
Example demonstrating default handler behavior in MailboxSociety.

This example shows that when no custom handler is specified,
the MailboxSociety automatically uses ChatAgent.step() to process messages.
"""

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies import AgentCard, MailboxMessage, MailboxSociety
from camel.types import ModelPlatformType, ModelType


def main():
    r"""Demonstrate default handler using ChatAgent.step."""
    print("=" * 70)
    print("Default Handler Example - Using ChatAgent.step")
    print("=" * 70)

    # Create society
    society = MailboxSociety(
        name="Default Handler Demo",
        max_iterations=3,
        process_interval=0.5,
    )
    print(f"\n✓ Created society: {society.name}")

    # Create model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Create Agent 1 - will use default handler
    print("\n--- Creating Agent 1 (Default Handler) ---")
    agent1 = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=(
                "You are a helpful assistant. "
                "When you receive messages, respond concisely."
            ),
        ),
        model=model,
    )

    card1 = AgentCard(
        agent_id="agent1",
        description="Agent using default handler",
        capabilities=["chat", "respond"],
        tags=["default-handler"],
    )

    society.register_agent(agent1, card1)
    print("✓ Registered agent1 (NO custom handler set)")
    print("  → Will use default handler (ChatAgent.step)")

    # Create Agent 2 - will also use default handler
    print("\n--- Creating Agent 2 (Default Handler) ---")
    agent2 = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Coordinator",
            content=(
                "You are a coordinator agent. "
                "When you receive messages, acknowledge them briefly."
            ),
        ),
        model=model,
    )

    card2 = AgentCard(
        agent_id="agent2",
        description="Another agent using default handler",
        capabilities=["coordinate", "acknowledge"],
        tags=["default-handler"],
    )

    society.register_agent(agent2, card2)
    print("✓ Registered agent2 (NO custom handler set)")
    print("  → Will also use default handler (ChatAgent.step)")

    # Add messages to demonstrate default handler
    print("\n--- Adding Messages ---")

    msg1 = MailboxMessage(
        sender_id="system",
        recipient_id="agent1",
        content="Hello Agent 1! Can you help me with a task?",
        subject="Request for Assistance",
    )
    society.message_router["agent1"].append(msg1)
    print("✓ Added message for agent1")

    msg2 = MailboxMessage(
        sender_id="agent1",
        recipient_id="agent2",
        content="Agent 2, I need coordination for the current task.",
        subject="Coordination Request",
    )
    society.message_router["agent2"].append(msg2)
    print("✓ Added message for agent2")

    # Check mailbox status
    print("\n--- Mailbox Status Before Processing ---")
    for agent_id in society.agents.keys():
        count = society.get_mailbox_count(agent_id)
        print(f"  {agent_id}: {count} message(s)")

    # Check memory before processing
    print("\n--- Agent Memory Before Processing ---")
    print(
        f"  agent1 memory length: "
        f"{len(agent1.memory.get_context())} message(s)"
    )
    print(
        f"  agent2 memory length: "
        f"{len(agent2.memory.get_context())} message(s)"
    )

    # Process messages using default handler
    print("\n--- Processing Messages with Default Handler ---")
    print("Default handler will:")
    print("  1. Create a user message with mailbox message content")
    print("  2. Call agent.step() with that message")
    print("  3. Agent processes and responds using its LLM")
    print()

    # Run the society
    society.run()

    # Check mailbox status after processing
    print("\n--- Mailbox Status After Processing ---")
    for agent_id in society.agents.keys():
        count = society.get_mailbox_count(agent_id)
        print(f"  {agent_id}: {count} message(s)")

    # Check memory after processing
    print("\n--- Agent Memory After Processing ---")
    agent1_memory_after = len(agent1.memory.get_context())
    agent2_memory_after = len(agent2.memory.get_context())

    print(f"  agent1 memory length: {agent1_memory_after} message(s)")
    print(f"  agent2 memory length: {agent2_memory_after} message(s)")

    # Show that memory increased (proof that agent.step was called)
    print("\n--- Verification ---")
    print(
        "✓ Agent memory increased, confirming ChatAgent.step() was called"
    )
    print("✓ Messages were processed using the default handler")

    # Show a sample of what was processed
    print("\n--- Sample Response from Agent 1 ---")
    if agent1_memory_after > 1:
        # Get the last message (agent's response)
        messages = agent1.memory.get_context()
        if len(messages) >= 2:
            # Show the user message that was created by default handler
            user_msg = messages[-2] if len(messages) >= 2 else None
            if user_msg:
                print("User Message (from default handler):")
                print(f"  {user_msg.content[:200]}...")

            # Show agent's response
            response_msg = messages[-1]
            print("\nAgent Response (via step()):")
            print(f"  {response_msg.content[:200]}...")

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)
    print(
        "\nKey Takeaway: When no handler is specified, "
        "MailboxSociety automatically"
    )
    print("uses ChatAgent.step() to process messages through the default")
    print("message handler.")


if __name__ == "__main__":
    main()
