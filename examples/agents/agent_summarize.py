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
"""Example showing how to summarize an agent conversation to markdown."""

from __future__ import annotations

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType


def calculate_add(a: int, b: int) -> int:
    """Add two integers and return the result."""

    return a + b


def calculate_multiply(a: int, b: int) -> int:
    """Multiply two integers and return the product."""

    return a * b


def main() -> None:
    """Run a short interaction and persist the summary to markdown."""

    system_message = (
        "You are a helpful assistant that can call math tools when needed."
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    add_tool = FunctionTool(calculate_add)
    multiply_tool = FunctionTool(calculate_multiply)

    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=[add_tool, multiply_tool],
    )

    # Interact with the agent so it has context to summarize.
    agent.step("We are preparing a math practice worksheet for students.")

    agent.step(
        "Compute 27 + 15 using the add tool to double-check the answer."
    )

    agent.step("Now multiply the result by 3.")

    # Summarize the conversation to a markdown file in the context directory.
    summary_result = agent.summarize(filename="math_planning_summary")

    print(summary_result.get("status", ""))
    if summary_result.get("file_path"):
        print(f"Summary saved to: {summary_result['file_path']}")

    if summary_result.get("summary"):
        print("Generated summary:\n")
        print(summary_result["summary"])


'''
Markdown file 'math_planning_summary.md' saved successfully
Summary saved to: context_files/session_20250918_192642_141905/math_planning_summary.md
Generated summary:

- Context
  - User is preparing a math practice worksheet for students.
  - Assistant offered to tailor the worksheet and asked clarifying questions (grade/age, topics, number of problems, answer key vs step-by-step, difficulty, time/layout).

- Key decisions made in conversation
  - Assistant provided a ready-to-use sample worksheet for Grade 6 (mixed skills) with 12 problems and a brief answer key.
  - User requested numerical checks using tools for arithmetic steps.

- Actions performed (completed)
  - Assistant used tools to verify calculations:
    - calculate_add(27, 15) → 42 (reported: 27 + 15 = 42)
    - calculate_multiply(42, 3) → 126 (reported: 42 * 3 = 126)

- Pending action items (who can/should act)
  - Assistant: prepare a customized worksheet based on user preferences (grade/topic/number of problems/difficulty).
  - Assistant: format the worksheet as a printable PDF or Google Doc if requested.
  - Assistant: provide full step-by-step solutions if the user wants them.
  - User: specify preferences (see open questions) so assistant can generate the customized worksheet.

- Open questions / user choices to confirm
  - What grade or age range should the worksheet target?
  - Which topics to include (arithmetic, fractions, decimals, ratios, pre-algebra, algebra, geometry, word problems, etc.)?
  - How many problems total?
  - Answer key only or full step-by-step solutions?
  - Preferred difficulty level (review, mixed, challenge)?
  - Any time limit, point values, or layout/format requirements?
  - Do you want the worksheet as a PDF or Google Doc?

- Next suggested step
  - User provides the preferences above and/or confirms whether to use the provided Grade 6 sample; assistant will generate the customized worksheet (with chosen format and solution detail).
'''  # noqa: E501


if __name__ == "__main__":
    main()
