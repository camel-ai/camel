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
import threading
import time

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import FileWriteToolkit, ThinkingToolkit
from camel.types import ModelPlatformType, ModelType


def create_simple_workforce():
    r"""Create a simple workforce for demonstration."""
    thinking_toolkit = ThinkingToolkit()
    file_write_toolkit = FileWriteToolkit()

    # Create a simple search agent
    poet_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Poet Agent",
            content=(
                "You are a poet.Before you write the poem, you need "
                "to think about the poem and the content."
            ),
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
        tools=[*thinking_toolkit.get_tools()],
    )

    # Create a file write agent
    file_write_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="File Write Agent",
            content="You are a file write agent.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
        tools=[*file_write_toolkit.get_tools()],
    )

    workforce = Workforce('Simple Demo Workforce')
    workforce.add_single_agent_worker("Poet Agent", poet_agent)
    workforce.add_single_agent_worker("File Write Agent", file_write_agent)

    return workforce


def simple_intervention_menu(workforce: Workforce):
    """Simple intervention menu for quick operations."""
    while True:
        print("\n🎮 INTERVENTION MODE")
        print("Select an option:")
        print("  1. Show pending/completed tasks")
        print("  2. Modify a task")
        print("  3. Add a new task")
        print("  4. Resume execution")
        print("  5. Stop workforce")

        try:
            choice = input("\nEnter choice (1-5): ").strip()

            if choice == "1":
                pending = workforce.get_pending_tasks()
                completed = workforce.get_completed_tasks()
                print(f"\n📝 Pending ({len(pending)}):")
                for i, task in enumerate(pending, 1):
                    print(f"  {i}. [{task.id}] {task.content}")
                print(f"\n✅ Completed ({len(completed)}):")
                for i, task in enumerate(completed, 1):
                    print(f"  {i}. [{task.id}] {task.content}")

                # Show current workforce status
                status = workforce.get_workforce_status()
                print(
                    f"\n📊 Status: {status['state']} | Pending: "
                    f"{status['pending_tasks_count']} | Completed: "
                    f"{status['completed_tasks_count']}"
                )

            elif choice == "2":
                pending = workforce.get_pending_tasks()
                if not pending:
                    print("❌ No pending tasks")
                    continue
                print("\nPending tasks:")
                for i, task in enumerate(pending, 1):
                    print(f"  {i}. [{task.id}] {task.content}")
                try:
                    num = int(input("Task number to modify: "))
                    if 1 <= num <= len(pending):
                        task = pending[num - 1]
                        new_content = input("New content: ")
                        if new_content.strip():
                            workforce.modify_task_content(task.id, new_content)
                            print("✅ Modified!")
                except ValueError:
                    print("❌ Invalid number")

            elif choice == "3":
                content = input("New task content: ")
                if content.strip():
                    task = workforce.add_task(content, as_subtask=True)
                    print(f"✅ Added task: {task.id}")

            elif choice == "4":
                print("▶️ Resuming...")
                return True

            elif choice == "5":
                print("🛑 Stopping...")
                return False

            else:
                print("❌ Invalid choice. Please enter 1-5.")

        except (KeyboardInterrupt, EOFError):
            print("\n🔄 Enter 4 to resume or 5 to stop")


def main():
    r"""Main demo function."""

    # Create workforce and task
    workforce = create_simple_workforce()
    task = Task(
        content=(
            "write a poem about the sun and the moon" "then write the md file"
        ),
        id="sun_and_moon",
    )

    print(f"📋 Task: {task.content}")
    print()

    # Start workforce in background
    def run_workforce():
        try:
            asyncio.run(workforce.process_task_async(task, interactive=True))
            print("\n🎉 Task completed!")
        except Exception as e:
            print(f"\n❌ Error: {e}")

    workforce_thread = threading.Thread(target=run_workforce)
    workforce_thread.daemon = True
    workforce_thread.start()

    print("⏳ Waiting for initial task decomposition...")
    # Wait until workforce enters RUNNING state or timeout
    start_wait = time.time()
    while True:
        status = workforce.get_workforce_status()
        if status["state"] != "idle" or status["pending_tasks_count"] > 0:
            break
        if time.time() - start_wait > 10:
            print("⚠️  Timed out waiting for workforce to start.")
            break
        time.sleep(0.2)

    print("🔄 Workforce is running... Press 'h' + Enter to intervene!")

    # Input monitoring
    intervention_active = False

    while workforce_thread.is_alive():
        try:
            user_input = input().strip().lower()

            if user_input == 'h' and not intervention_active:
                intervention_active = True
                print("\n⏸️ Pausing workforce...")
                workforce.pause()
                time.sleep(0.5)

                should_continue = simple_intervention_menu(workforce)

                if should_continue:
                    workforce.resume()
                    intervention_active = False
                    print(
                        "🔄 Workforce resumed! Press 'h' + Enter to "
                        "intervene again."
                    )
                else:
                    workforce.stop_gracefully()
                    break

        except KeyboardInterrupt:
            print("\n🛑 Force stopping...")
            workforce.stop_gracefully()
            break
        except EOFError:
            break

    workforce_thread.join(timeout=5)

    # Final status
    print("\n📊 Final Status:")
    status = workforce.get_workforce_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print("\n👋 Demo finished!")


if __name__ == "__main__":
    main()
