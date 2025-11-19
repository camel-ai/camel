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
"""
Example demonstrating the use of MessageSummarizer for conversation
summarization.

This example shows:
1. Using MessageSummarizer standalone for structured summaries
2. Using ChatAgent.asummarize() which delegates to MessageSummarizer
3. Custom prompts and working directories
4. Parallel summarization of multiple agents
5. ContextSummarizerToolkit integration with MessageSummarizer
6. Adding toolkit tools to agents for self-managed memory
"""

import asyncio

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import ContextSummarizerToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils.message_summarizer import MessageSummarizer


def example_1_standalone_message_summarizer():
    """Example 1: Using MessageSummarizer standalone for summaries."""
    print("\n" + "=" * 70)
    print("Example 1: Standalone MessageSummarizer with Structured Output")
    print("=" * 70 + "\n")

    # Create a MessageSummarizer instance
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )
    summarizer = MessageSummarizer(model_backend=model)

    # Create some sample messages
    messages = [
        BaseMessage.make_user_message(
            role_name="User",
            content=(
                "I need help building a Python web scraper for news "
                "articles."
            ),
        ),
        BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=(
                "I can help you build a web scraper. We'll use "
                "BeautifulSoup and requests."
            ),
        ),
        BaseMessage.make_user_message(
            role_name="User",
            content="Great! Can we also add support for handling pagination?",
        ),
        BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=(
                "Yes, we can iterate through pages by following 'next' "
                "links."
            ),
        ),
    ]

    # Generate structured summary using the summarize method
    summary = summarizer.summarize(messages)

    print("Structured Summary:")
    print(f"  Summary: {summary.summary}")
    print(f"  Participants: {summary.participants}")
    print(f"  Key Topics: {summary.key_topics_and_entities}")
    print(f"  Decisions: {summary.decisions_and_outcomes}")
    print(f"  Action Items: {summary.action_items}")
    print(f"  Progress: {summary.progress_on_main_task}")


async def example_2_chat_agent_asummarize():
    """Example 2: Using ChatAgent.asummarize() for summarization."""
    print("\n" + "=" * 70)
    print("Example 2: ChatAgent.asummarize() with File Persistence")
    print("=" * 70 + "\n")

    # Create a ChatAgent
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant",
            content="You are a helpful coding assistant.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        ),
    )

    # Simulate a conversation
    user_messages = [
        "Can you help me optimize a SQL query?",
        "It's taking too long to run on large datasets.",
        "The query joins 3 tables and has multiple WHERE clauses.",
    ]

    for msg in user_messages:
        agent.step(msg)

    # Summarize the conversation and save to file
    result = await agent.asummarize(
        filename="sql_optimization_session",
        working_directory="./conversation_summaries",
        include_summaries=False,
        add_user_messages=True,
    )

    print("Summary Result:")
    print(f"  Status: {result['status']}")
    print(f"  File Path: {result['file_path']}")
    print(f"  Summary Preview: {result['summary'][:200]}...")


async def example_3_custom_prompt():
    """Example 3: Using custom summary prompts."""
    print("\n" + "=" * 70)
    print("Example 3: Custom Summary Prompt")
    print("=" * 70 + "\n")

    # Create a ChatAgent
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant",
            content="You are a project management assistant.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        ),
    )

    # Simulate a project discussion
    messages = [
        "We need to discuss the Q4 roadmap.",
        "What are the key features we should prioritize?",
        "Let's focus on user authentication and payment integration.",
    ]

    for msg in messages:
        agent.step(msg)

    # Custom prompt for project-focused summary
    custom_prompt = """
    Summarize the following project discussion.
    Focus on:
    1. Project goals and objectives
    2. Key features and priorities
    3. Timeline and milestones (if mentioned)
    4. Team assignments (if mentioned)
    5. Next steps and action items

    Provide a concise, actionable summary.
    """

    # Summarize with custom prompt
    result = await agent.asummarize(
        summary_prompt=custom_prompt,
        filename="q4_roadmap_discussion",
        working_directory="./project_summaries",
    )

    print("Custom Summary Result:")
    print(f"  Status: {result['status']}")
    print(f"  File Path: {result['file_path']}")


async def example_4_parallel_summarization():
    """Example 4: Parallel summarization of multiple agent conversations."""
    print("\n" + "=" * 70)
    print("Example 4: Parallel Summarization of Multiple Agents")
    print("=" * 70 + "\n")

    # Create multiple agents for different tasks
    agent_1 = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="CodeReviewer",
            content="You are a code review assistant.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        ),
        agent_id="code_reviewer",
    )

    agent_2 = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="TestWriter",
            content="You are a test writing assistant.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        ),
        agent_id="test_writer",
    )

    # Simulate conversations
    agent_1.step("Review this function for performance issues.")
    agent_2.step("Write unit tests for the authentication module.")

    # Summarize both agents in parallel
    results = await asyncio.gather(
        agent_1.asummarize(filename="code_review_session"),
        agent_2.asummarize(filename="test_writing_session"),
    )

    print("Parallel Summarization Results:")
    for i, result in enumerate(results, 1):
        print(f"  Agent {i}:")
        print(f"    Status: {result['status']}")
        print(f"    File: {result['file_path']}")


def example_5_context_summarizer_toolkit():
    """Example 5: Using ContextSummarizerToolkit with MessageSummarizer."""
    print("\n" + "=" * 70)
    print("Example 5: ContextSummarizerToolkit Integration")
    print("=" * 70 + "\n")

    # Create a ChatAgent
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant",
            content="You are a helpful assistant with context management.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        ),
    )

    # Create ContextSummarizerToolkit with custom prompt template
    custom_template = """
    You are analyzing a technical conversation. Extract:
    - Main technical challenges discussed
    - Solutions implemented or proposed
    - Tools and technologies mentioned
    - Unresolved issues or blockers
    """

    toolkit = ContextSummarizerToolkit(
        agent=agent,
        working_directory="./toolkit_summaries",
        summary_prompt_template=custom_template,
    )

    # Simulate a long conversation that needs compression
    messages = [
        "I'm working on a microservices architecture.",
        "We need to implement service discovery.",
        "Should we use Consul or Eureka?",
        "Let's use Consul with Docker.",
        "How do we handle authentication across services?",
        "We should implement JWT tokens.",
        "What about rate limiting?",
        "We can use Redis for distributed rate limiting.",
        "We also need to set up monitoring.",
        "Let's use Prometheus and Grafana.",
        # ... Many more messages to simulate memory pressure
    ]

    for msg in messages:
        agent.step(msg)

    # Check if we should compress context
    should_compress = toolkit.should_compress_context(
        message_limit=10,  # Low limit for demo purposes
    )
    print(f"Should compress context: {should_compress}")

    if should_compress:
        # Use the toolkit to summarize and compress
        result = toolkit.summarize_full_conversation_history()
        print(f"\nCompression Result: {result}")

    # Get memory info
    memory_info = toolkit.get_conversation_memory_info()
    print(f"\nMemory Info:\n{memory_info}")

    # Search through conversation history
    search_results = toolkit.search_full_conversation_history(
        keywords=["authentication", "JWT", "tokens"],
        top_k=3,
    )
    print(f"\nSearch Results:\n{search_results}")

    # Get the current summary
    current_summary = toolkit.get_current_summary()
    if current_summary:
        print(f"\nCurrent Summary:\n{current_summary[:200]}...")


def example_6_toolkit_with_agent_tools():
    """Example 6: Using toolkit tools with an agent."""
    print("\n" + "=" * 70)
    print("Example 6: Agent with ContextSummarizer Tools")
    print("=" * 70 + "\n")

    # Create a ChatAgent with tools
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant",
            content=(
                "You are a helpful assistant with memory management tools. "
                "You can summarize conversations, search history, and check "
                "memory status."
            ),
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        ),
    )

    # Create toolkit and add its tools to the agent
    toolkit = ContextSummarizerToolkit(
        agent=agent,
        working_directory="./agent_with_tools_summaries",
    )

    # Add toolkit tools to agent
    agent.add_tools(toolkit.get_tools())

    # Simulate conversation
    print("Simulating conversation with memory management tools...")

    # Agent can now use summarization tools when needed
    print("\nAvailable Tools:")
    for tool in toolkit.get_tools():
        print(f"  - {tool.get_function_name()}")

    # The agent can now call these tools during conversations to manage
    # its own memory, especially useful for long-running conversations
    print("\nAgent now has access to:")
    print("  1. summarize_full_conversation_history()")
    print("  2. search_full_conversation_history(keywords, top_k)")
    print("  3. get_conversation_memory_info()")
    print(
        "\nThese tools use MessageSummarizer internally for unified "
        "summarization!"
    )


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("MessageSummarizer Examples")
    print("=" * 70)

    # Example 1: Standalone MessageSummarizer (synchronous)
    example_1_standalone_message_summarizer()

    # Examples 2-4: Async examples
    asyncio.run(example_2_chat_agent_asummarize())
    asyncio.run(example_3_custom_prompt())
    asyncio.run(example_4_parallel_summarization())

    # Examples 5-6: ContextSummarizerToolkit integration
    example_5_context_summarizer_toolkit()
    example_6_toolkit_with_agent_tools()

    print("\n" + "=" * 70)
    print("All examples completed!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
