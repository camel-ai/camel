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

import threading
import time
from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import SearchToolkit, FunctionTool
from camel.types import ModelPlatformType, ModelType


def create_simple_workforce():
    """Create a simple workforce for demonstration."""
    search_toolkit = SearchToolkit()
    
    # Create a simple search agent
    search_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Research Agent",
            content="You are a research agent that can search for information online.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
        tools=[FunctionTool(search_toolkit.search_wiki)],
    )
    
    # Create a planning agent
    planning_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Planning Agent",
            content="You are a planning agent that creates detailed plans and itineraries.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
    )
    
    workforce = Workforce('Simple Demo Workforce')
    workforce.add_single_agent_worker("Research Agent", search_agent)
    workforce.add_single_agent_worker("Planning Agent", planning_agent)
    
    return workforce


def print_instructions():
    """Print usage instructions."""
    print("🎯 SIMPLE HOTKEY INTERVENTION DEMO")
    print("=" * 50)
    print("📖 Instructions:")
    print("  1. The workforce will start automatically")
    print("  2. Press 'h' + Enter anytime to intervene")
    print("  3. In intervention mode, select options with numbers:")
    print("     1 - View current tasks")
    print("     2 - Modify tasks")
    print("     3 - Add new tasks")
    print("     4 - Save snapshots")
    print("     5 - Continue execution")
    print("     6 - Stop workforce")
    print("  4. Press Ctrl+C anytime to force stop")
    print("=" * 50)
    print()


def simple_intervention_menu(workforce):
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
                print(f"\n📊 Status: {status['state']} | Pending: {status['pending_tasks_count']} | Completed: {status['completed_tasks_count']}")
                    
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
                    task = workforce.add_task(content)
                    print(f"✅ Added task: {task.id}")
                
            elif choice == "4":
                print("▶️ Resuming...")
                return True
                
            elif choice == "5":
                print("🛑 Stopping...")
                return False
                
            else:
                print("❌ Invalid choice. Please enter 1-6.")
                
        except (KeyboardInterrupt, EOFError):
            print("\n🔄 Enter 5 to resume or 6 to stop")


def main():
    """Main demo function."""
    print_instructions()
    
    # Create workforce and task
    workforce = create_simple_workforce()
    task = Task(
        content="Research the top 5 tourist attractions in Tokyo and create a 2-day itinerary",
        id="tokyo_itinerary"
    )
    
    print(f"📋 Task: {task.content}")
    print()
    
    # Start workforce in background
    def run_workforce():
        try:
            result = workforce.process_task_with_intervention(task)
            print(f"\n🎉 Task completed!")
            print(f"Result: {result.result}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    workforce_thread = threading.Thread(target=run_workforce)
    workforce_thread.daemon = True
    workforce_thread.start()
    
    print("⏳ Waiting for initial task decomposition...")
    time.sleep(2)
    
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
                    print("🔄 Workforce resumed! Press 'h' + Enter to intervene again.")
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