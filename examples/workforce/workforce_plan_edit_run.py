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
Workforce Plan-Edit-Run Example
================================

Demonstrates the two-phase workforce execution with human-in-the-loop:

1. **Plan** — decompose a task into subtasks
2. **Review** — user inspects and edits the plan in terminal
3. **Run**  — execute the final plan

Usage:
    python examples/workforce/workforce_plan_edit_run.py
"""

import asyncio

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.societies.workforce import Workforce
from camel.tasks import Task


def print_plan(plan):
    """Print the current plan in a readable format."""
    print(f"\n  Subtasks ({len(plan.subtasks)}):")
    for i, subtask in enumerate(plan.subtasks, 1):
        deps = plan.dependency_graph.get(subtask.id, [])
        dep_str = f" (depends on: {deps})" if deps else ""
        # Truncate long content for display
        content = subtask.content
        if len(content) > 120:
            content = content[:120] + "..."
        print(f"    {i}. [{subtask.id}] {content}{dep_str}")


def edit_loop(plan):
    """Interactive editing loop. Returns True if user wants to proceed."""
    while True:
        print("\n  Commands:")
        print("    [enter]       - proceed with current plan")
        print("    edit <n> <text> - replace subtask n's content")
        print("    append <n> <text> - append text to subtask n")
        print("    delete <n>    - remove subtask n")
        print("    quit          - abort without running")

        user_input = input("\n  > ").strip()

        if not user_input:
            return True

        if user_input.lower() == "quit":
            return False

        parts = user_input.split(maxsplit=2)
        cmd = parts[0].lower()

        if cmd == "edit" and len(parts) == 3:
            try:
                idx = int(parts[1]) - 1
                if 0 <= idx < len(plan.subtasks):
                    old = plan.subtasks[idx].content
                    plan.subtasks[idx].content = parts[2]
                    print(f"    Updated subtask {idx + 1}")
                    print(f"      Before: {old[:80]}...")
                    print(f"      After:  {parts[2][:80]}...")
                else:
                    print(f"    Invalid index. Range: 1-{len(plan.subtasks)}")
            except ValueError:
                print("    Usage: edit <number> <new content>")

        elif cmd == "append" and len(parts) == 3:
            try:
                idx = int(parts[1]) - 1
                if 0 <= idx < len(plan.subtasks):
                    plan.subtasks[idx].content += " " + parts[2]
                    print(f"    Appended to subtask {idx + 1}")
                else:
                    print(f"    Invalid index. Range: 1-{len(plan.subtasks)}")
            except ValueError:
                print("    Usage: append <number> <extra text>")

        elif cmd == "delete" and len(parts) >= 2:
            try:
                idx = int(parts[1]) - 1
                if 0 <= idx < len(plan.subtasks):
                    removed = plan.subtasks.pop(idx)
                    # Clean up dependency references
                    plan.dependency_graph.pop(removed.id, None)
                    for task_id in plan.dependency_graph:
                        deps = plan.dependency_graph[task_id]
                        if removed.id in deps:
                            deps.remove(removed.id)
                    print(f"    Removed: {removed.content[:80]}...")
                else:
                    print(f"    Invalid index. Range: 1-{len(plan.subtasks)}")
            except ValueError:
                print("    Usage: delete <number>")
        else:
            print("    Unknown command. Try: edit, append, delete, or quit")

        print_plan(plan)


async def main():
    # --- Build workforce ---
    researcher = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Researcher",
            content="You are a research specialist. You find and gather "
            "information on any topic.",
        ),
    )
    analyst = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Analyst",
            content="You are a business analyst. You analyze findings "
            "and identify key insights.",
        ),
    )
    writer = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Writer",
            content="You are a report writer. You synthesize analysis "
            "into clear, concise reports.",
        ),
    )

    workforce = Workforce("Research Team")
    workforce.add_single_agent_worker(
        "Researcher who gathers information", worker=researcher
    )
    workforce.add_single_agent_worker(
        "Analyst who processes findings", worker=analyst
    )
    workforce.add_single_agent_worker(
        "Writer who creates final reports", worker=writer
    )

    # --- PHASE 1: Plan ---
    task = Task(
        content="Write a market analysis report about electric vehicles "
        "covering: market size, key players, and future trends.",
        id="main-task",
    )

    print("=" * 60)
    print("PHASE 1: Planning")
    print("=" * 60)

    plan = await workforce.plan_task_async(task)
    print_plan(plan)

    # --- PHASE 2: Interactive editing ---
    print("\n" + "=" * 60)
    print("PHASE 2: Review & Edit")
    print("=" * 60)

    should_run = edit_loop(plan)

    if not should_run:
        print("\nAborted.")
        return

    # --- PHASE 3: Execute ---
    print("\n" + "=" * 60)
    print(f"PHASE 3: Executing ({len(plan.subtasks)} subtasks)")
    print("=" * 60)

    result = await workforce.run_plan_async(plan)

    print("\n" + "=" * 60)
    print(f"RESULT: {result.state}")
    print("=" * 60)
    print(result.result or "(no result)")


if __name__ == "__main__":
    asyncio.run(main())
