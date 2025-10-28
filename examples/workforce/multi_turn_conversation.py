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
        content="You are a research specialist who gathers and "
        "analyzes information. You focus on finding facts and "
        "providing detailed context.",
    ),
    model=ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    ),
)

writer_agent = ChatAgent(
    system_message=BaseMessage.make_assistant_message(
        role_name="Writer",
        content="You are a professional writer who creates clear, "
        "concise responses. You synthesize information into "
        "well-structured answers.",
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

# Initialize conversation history for all rounds
conversation_history = []
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

    # Build task content with context from previous rounds
    history_context = ""
    for i in range(len(conversation_history)):
        item = conversation_history[i]
        history_context += f"Round {i+1}:\n"
        history_context += f"Task: {item['task']}\n"
        history_context += f"Result: {item['result']}\n\n"

    task_content = (
        f"{history_context}{'='*50}\nNew task: {user_input}"
        if history_context
        else user_input
    )

    # Create and process task
    task = Task(content=task_content, id=str(turn_number))
    task_result = workforce.process_task(task)

    # Display response
    print(f"\nAssistant: {task_result.result}")

    # Store all information from this round for future context
    round_info = {
        'task': user_input,
        'result': task_result.result,
    }

    conversation_history.append(round_info)

print("\n--- Conversation Complete ---")
print(f"Total turns: {turn_number}")
