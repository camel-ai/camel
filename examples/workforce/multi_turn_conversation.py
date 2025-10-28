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
Multi-turn Workforce Conversation Example

This example demonstrates a multi-turn conversation where:
- User provides input via terminal
- Previous task and summary are passed as context to each new turn
- Two agents (Researcher and Writer) collaborate on tasks

Example conversation to try:
    Turn 1: "What is machine learning?"
    Turn 2: "Can you give me an example application?"
    Turn 3: "How does that relate to what you explained earlier?"

Or try:
    Turn 1: "Tell me about Paris"
    Turn 2: "What are the top 3 attractions there?"
    Turn 3: "Which one would you recommend based on our discussion?"
"""

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.types import ModelPlatformType, ModelType

# Set up agents
research_agent = ChatAgent(
    system_message=BaseMessage.make_assistant_message(
        role_name="Researcher",
        content="You are a research specialist who gathers and analyzes information. "
        "You focus on finding facts and providing detailed context.",
    ),
    model=ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    ),
)

writer_agent = ChatAgent(
    system_message=BaseMessage.make_assistant_message(
        role_name="Writer",
        content="You are a professional writer who creates clear, concise responses. "
        "You synthesize information into well-structured answers.",
    ),
    model=ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    ),
)

# Create workforce with 2 agents
workforce = Workforce('Multi-turn Assistant Team')
workforce.add_single_agent_worker(
    "A researcher who gathers and analyzes information", worker=research_agent
).add_single_agent_worker(
    "A writer who synthesizes information into clear responses",
    worker=writer_agent,
)

# Initialize conversation history
previous_task = None
previous_summary = None
turn_number = 0

print("=== Multi-turn Workforce Conversation ===")
print("Type your task/question (or 'quit' to exit)")
print("=" * 50)

# Multi-turn conversation loop
while True:
    turn_number += 1
    print(f"\n--- Turn {turn_number} ---")

    # Get user input from terminal
    user_input = input("You: ").strip()

    if user_input.lower() in ['quit', 'exit', 'q']:
        print("Exiting conversation. Goodbye!")
        break

    if not user_input:
        print("Please enter a valid task or question.")
        continue

    # Build task content with context from previous turn
    task_content = user_input
    if previous_task and previous_summary:
        task_content = (
            f"Previous task: {previous_task}\n"
            f"Previous summary: {previous_summary}\n\n"
            f"New task: {user_input}"
        )

    # Create and process task
    task = Task(content=task_content, id=str(turn_number))
    task_result = workforce.process_task(task)

    # Display response
    print(f"\nAssistant: {task_result.result}")

    # Store for next turn
    previous_task = user_input
    previous_summary = task_result.result

print("\n--- Conversation Complete ---")
print(f"Total turns: {turn_number}")
