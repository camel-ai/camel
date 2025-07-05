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

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.societies.workforce import Workforce
from camel.tasks import Task
from camel.toolkits import AgentCommunicationToolkit


def create_messaging_workforce():
    r"""Create a workforce where agents can communicate with each other."""

    # 1. Initialize the message toolkit
    msg_toolkit = AgentCommunicationToolkit(max_message_history=100)

    # 2. Create agents with specific roles
    researcher = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Researcher",
            content=(
                "You are a Research Specialist. ALWAYS use send_message to "
                "share your findings with the writer. First use "
                "list_available_agents to see who you can message, then "
                "send your research findings to the writer."
            ),
        )
    )

    writer = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Writer",
            content=(
                "You are a Content Writer. ALWAYS use send_message to "
                "coordinate. After creating content, send it to the "
                "reviewer for feedback. Use messaging tools to communicate "
                "with team members."
            ),
        )
    )

    reviewer = ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Reviewer",
            content=(
                "You are a Content Reviewer. ALWAYS use send_message to "
                "provide feedback to the writer. Use messaging tools to "
                "coordinate and ensure quality. Send detailed feedback via "
                "messages."
            ),
        )
    )

    # 3. Register agents with the message toolkit using role names that match
    msg_toolkit.register_agent("Researcher", researcher)
    msg_toolkit.register_agent("Writer", writer)
    msg_toolkit.register_agent("Reviewer", reviewer)

    # 4. Add messaging tools to each agent
    message_tools = msg_toolkit.get_tools()
    for agent in [researcher, writer, reviewer]:
        for tool in message_tools:
            agent.add_tool(tool)

    # 5. Create workforce and add workers with matching names
    workforce = Workforce("Content Creation Team")
    workforce.add_single_agent_worker("Researcher", researcher)
    workforce.add_single_agent_worker("Writer", writer)
    workforce.add_single_agent_worker("Reviewer", reviewer)

    return workforce, msg_toolkit


async def demonstrate_coordination():
    r"""Show how agents coordinate using messaging during task execution."""

    print("🏗️  Setting up messaging-enabled workforce...")
    workforce, msg_toolkit = create_messaging_workforce()

    print("📋 Available agents:")
    print(msg_toolkit.list_available_agents())

    # Create a task that requires coordination
    task = Task(
        content=(
            "IMPORTANT: You MUST use the messaging tools for coordination! "
            "\n\nTask: Research and write a brief article about the "
            "benefits of AI collaboration."
            "\n\nRequired workflow:"
            "\n1. Researcher: First use list_available_agents(), then "
            "send_message() to share findings with writer"
            "\n2. Writer: Use send_message() to send draft to reviewer for "
            "feedback"
            "\n3. Reviewer: Use send_message() to provide feedback to writer"
            "\n\nYou MUST demonstrate inter-agent messaging capabilities!"
        ),
        id="collaborative_article_task",
    )

    print(f"\n🎯 Processing coordinated task: {task.id}")

    # Process the task
    result = await workforce.process_task_async(task)

    print(f"\n✅ Task Status: {result.state}")
    result_preview = result.result[:200] if result.result else "No result"
    print(f"📄 Result Preview: {result_preview}...")

    # Show message exchange that occurred
    print("\n💬 Message Activity Summary:")
    for agent_id in ["researcher", "writer", "reviewer"]:
        history = msg_toolkit.get_message_history(agent_id, limit=5)
        print(f"\n{agent_id.upper()}:")
        print(history)

    print("\n📊 Final Toolkit Status:")
    print(msg_toolkit.get_toolkit_status())

    # Add a demonstration of manual messaging
    print("\n🔧 Manual messaging demonstration:")
    print("Sending a coordination message...")
    manual_result = msg_toolkit.send_message(
        message=(
            "Great job everyone! The collaboration workflow is working "
            "perfectly."
        ),
        receiver_id="researcher",
        sender_id="system",
    )
    print(f"Manual message result: {manual_result}")

    # Show updated history
    print("\n📝 Updated message history:")
    updated_history = msg_toolkit.get_message_history("researcher", limit=3)
    print(updated_history)


if __name__ == "__main__":
    print("🚀 AgentCommunicationToolkit + Workforce Quick Start")
    print("=" * 60)

    # Try workforce demo first
    try:
        asyncio.run(demonstrate_coordination())
    except Exception as e:
        print(f"⚠️  Workforce demo failed: {e}")
