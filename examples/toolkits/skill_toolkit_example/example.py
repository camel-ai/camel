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
Skill Toolkit Example

This example demonstrates how to use SkillToolkit with an agent.
The agent uses tool calls to interact with skills.

Skills are defined in .camel/skills/ directory:
  - data-analyzer: For analyzing datasets
  - report-writer: For generating reports
  - code-reviewer: For reviewing code

Run this example from the skill_toolkit_example directory:
    cd examples/toolkits/skill_toolkit_example
    python example.py
"""

import os
from pathlib import Path

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import SkillToolkit, TerminalToolkit
from camel.types import ModelPlatformType, ModelType

# Set working directory to this example folder so skills are discovered
EXAMPLE_DIR = Path(__file__).parent.resolve()
os.chdir(EXAMPLE_DIR)

# Create model (change platform/type as needed)
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_5_2,
)

# Create skill toolkit - discovers skills from .camel/skills/
skill_toolkit = SkillToolkit(working_directory=str(EXAMPLE_DIR))

# Create terminal toolkit - enables script execution from skills
terminal_toolkit = TerminalToolkit(working_directory=str(EXAMPLE_DIR))

# Create agent with both skill and terminal tools
agent = ChatAgent(
    system_message="You are a helpful assistant that uses skills and "
    "can execute scripts.",
    model=model,
    tools=[*skill_toolkit.get_tools(), *terminal_toolkit.get_tools()],
)


def main():
    # Example 1: Agent lists available skills via tool call
    print("=" * 60)
    print("Example 1: Agent lists available skills")
    print("=" * 60)
    agent.reset()
    response = agent.step("What skills are available? ")
    print(f"\n{response.msgs[0].content}")

    # Example 2: Agent loads a specific skill via tool call
    print("\n" + "=" * 60)
    print("Example 2: Agent loads the data-analyzer skill")
    print("=" * 60)

    agent.reset()
    response = agent.step("Load the data-analyzer skill")
    print(f"\n{response.msgs[0].content[:500]}...")

    # Example 3: Agent executes a script from a skill
    print("\n" + "=" * 60)
    print("Example 3: Agent executes script from data-analyzer skill")
    print("=" * 60)

    task = """
    Load the data-analyzer skill and run its analysis script
    with sample data [10, 20, 30, 40, 50].
    """

    print(f"\nTask: {task.strip()}")
    print("\nAgent response:")
    agent.reset()
    response = agent.step(task)
    print(response.msgs[0].content)

    # Example 4: Agent uses skills to complete a complex task
    print("\n" + "=" * 60)
    print("Example 4: Agent uses skills for analysis task")
    print("=" * 60)

    task = """
    I have sales data showing monthly revenue:
    Jan: $10,000, Feb: $12,000, Mar: $9,500, Apr: $15,000

    Please analyze this data and write a brief report.
    Use the appropriate skills to help with this task.
    """

    print(f"\nTask: {task.strip()}")
    print("\nAgent response:")
    agent.reset()
    response = agent.step(task)
    print(response.msgs[0].content)


if __name__ == "__main__":
    main()
