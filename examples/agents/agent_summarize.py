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
Agent Summarization Examples

This module contains two demonstrations:

1. Food Preference Memory Example:
   Agent1 learns user's food preferences and creates a summary.
   Agent2 retrieves Agent1's memory and continues similar tasks.

2. Terminal Toolkit & Summarization Example:
   Agent performs terminal operations using CAMEL's terminal toolkit,
   then summarizes its terminal session and displays the summary.
"""

import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import TerminalToolkit
from camel.types import ModelPlatformType, ModelType


def food_preference_demo():
    """
    Simple demonstration of food preference learning and memory transfer.
    """
    print("=" * 60)
    print("🍽️  FOOD PREFERENCE MEMORY DEMO")
    print("=" * 60)

    # Setup
    working_dir = "food_demo"
    os.makedirs(working_dir, exist_ok=True)

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # ========================================================================
    # PHASE 1: Agent1 learns user food preferences
    # ========================================================================
    print("\n🥗 PHASE 1: Agent1 - Learning Food Preferences")
    print("-" * 50)

    agent1 = ChatAgent(
        model=model,
        agent_id="food_agent_001",
    )

    # User shares all preferences at once
    print("\n👤 User tells Agent1 their food preferences...")

    response1 = agent1.step("""
    Here are my food preferences:
    
    LIKES:
    - Italian food, pasta, pizza
    - Grilled chicken and salmon
    - Fresh vegetables: broccoli, spinach, tomatoes
    - Rice and quinoa
    - Moderate spices, garlic, basil
    
    DISLIKES:
    - Beef and pork
    - Mushrooms (hate them!)
    - Very spicy food
    - Dairy products (lactose intolerant)
    - Cilantro
    
    Please remember these preferences for future meal suggestions.
    """)

    print("✅ Agent1 learned all preferences")
    print(f"Response: {response1.msgs[0].content[:150]}...")

    # Agent1 summarizes
    print("\n📝 Agent1 creating summary...")
    agent1.summarize(working_directory=working_dir)

    print(f"✅ Memory saved to: {working_dir}/.camel/food_agent_001.md")

    # ========================================================================
    # PHASE 2: Agent2 retrieves memory and answers questions
    # ========================================================================
    print("\n" + "=" * 60)
    print("🤖 PHASE 2: Agent2 - Using Retrieved Memory")
    print("-" * 50)

    agent2 = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
        agent_id="food_agent_002",
    )

    # Agent2 retrieves Agent1's knowledge
    print("\n🧠 Agent2 retrieving Agent1's memory...")

    try:
        agent2.retrieve_summary(
            path=f"{working_dir}/.camel/food_agent_001.md",
            working_directory=working_dir,
            append_to_system=True,
        )
        print("✅ Agent2 loaded Agent1's memory successfully")

    except FileNotFoundError:
        print("❌ Could not find Agent1's summary")
        return

    # Test Agent2's knowledge
    print("\n🔍 Testing Agent2's knowledge...")

    test_response = agent2.step("What foods does the user like?")
    print("\nQ: What foods does the user like?")
    print(f"A: {test_response.msgs[0].content}")

    test_response2 = agent2.step("What foods does the user dislike?")
    print("\nQ: What foods does the user dislike?")
    print(f"A: {test_response2.msgs[0].content}")

    # ========================================================================
    # RESULTS
    # ========================================================================
    print("\n" + "=" * 60)
    print("🎉 DEMO COMPLETE")
    print("=" * 60)

    print("✅ Agent1: Learned user preferences")
    print("✅ Agent2: Retrieved memory and answered questions correctly")
    print("✅ Memory transfer successful!")


"""
============================================================
🍽️  FOOD PREFERENCE MEMORY DEMO
============================================================

🥗 PHASE 1: Agent1 - Learning Food Preferences
--------------------------------------------------

👤 User tells Agent1 their food preferences...
✅ Agent1 learned all preferences
Response: Got it — thank you. I've noted these preferences and will use them 
when suggesting meals in this conversation:

Summary I'll follow
- Likes: Italian (...

📝 Agent1 creating summary...
Summary saved to: food_demo/.camel/food_agent_001.md
✅ Memory saved to: food_demo/.camel/food_agent_001.md

============================================================
🤖 PHASE 2: Agent2 - Using Retrieved Memory
--------------------------------------------------

🧠 Agent2 retrieving Agent1's memory...
Summary retrieved from: food_demo/.camel/food_agent_001.md
Summary appended to system message (3378 characters)
✅ Agent2 loaded Agent1's memory successfully

🔍 Testing Agent2's knowledge...

Q: What foods does the user like?
A: The user likes:
- Italian food (pasta, pizza)
- Grilled chicken
- Salmon
- Fresh vegetables: broccoli, spinach, tomatoes
- Rice and quinoa
- Moderate spice levels
- Garlic
- Basil

Q: What foods does the user dislike?
A: The user dislikes/avoids:
- Mushrooms (strong dislike)
- Beef and pork
- Very spicy foods
- Cilantro
- Dairy (lactose intolerance — avoid dairy)

============================================================
🎉 DEMO COMPLETE
============================================================
✅ Agent1: Learned user preferences
✅ Agent2: Retrieved memory and answered questions correctly
✅ Memory transfer successful!
"""


def terminal_toolkit_demo():
    """
    Demonstration of terminal toolkit operations with agent summarization.
    Agent performs terminal commands, then summarizes the session.
    """
    # Setup
    working_dir = "terminal_demo"
    os.makedirs(working_dir, exist_ok=True)

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Create terminal toolkit
    terminal_toolkit = TerminalToolkit(working_directory=working_dir)

    # ========================================================================
    # Agent with terminal toolkit performs various operations
    # ========================================================================

    agent = ChatAgent(
        system_message="You are a system administrator assistant with "
        "access to terminal commands. Help with file system operations "
        "and provide detailed reports.",
        model=model,
        agent_id="terminal_agent_001",
        tools=terminal_toolkit.get_tools(),
    )

    # Task 1: System information gathering
    agent.step("""
    Please help me gather basic system information by:
    1. Checking the current directory
    2. Listing all files in the current directory
    3. Creating a text file called 'system_info.txt' with current date
    4. Displaying the contents of the file you created
    """)

    # Task 2: File operations and search
    agent.step("""
    Now please help me with file management:
    1. Create a subdirectory called 'test_data'
    2. Create three sample files in that directory with different content
    3. Search for specific text patterns in those files
    4. Generate a summary report of what you found
    """)

    # Task 3: Cleanup operations
    agent.step("""
    Finally, help me organize by:
    1. Listing all files and directories we created
    2. Checking disk usage of our working directory
    3. Creating a final summary file with all operations performed
    """)

    # Agent summarizes its terminal session
    agent.summarize(working_directory=working_dir)
    summary_path = f"{working_dir}/.camel/terminal_agent_001.md"

    # Display summary content
    if os.path.exists(summary_path):
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary_content = f.read()
                print(summary_content)
        except Exception as e:
            print(f"❌ Error reading summary file: {e}")
    else:
        print("❌ Summary file not found")


"""
============================================================
# Agent Conversation Summary

    **Agent ID:** terminal_agent_001
    **Generated:** 2025-08-28 16:52:45
    **Agent Type:** ChatAgent

    ---

    Conversation Summary

1) Conversation Overview
- Main topics:
  - Basic system inspection (current directory, directory listing).
  - File creation and simple file management inside a working directory.
  - Searching files for text patterns and generating a report of matches.
  - Organizing results and creating a final summary of operations.
- Key themes:
  - Reproducible shell-based operations.
  - Simple text processing (grep) and file reporting.
  - Ensuring a clear audit of created/modified files and disk usage.

2) Important Decisions / Conclusions
- Work was performed in: /Users/jinx0a/Repo/camel/terminal_demo
- Created a working subdirectory test_data (or used existing) to hold sample 
files and reports.
- Patterns selected for text search: TODO, ERROR, IMPORTANT.
- A scan summary was written into test_data/scan_summary.txt and a final 
summary into final_operations_summary.txt.
- Noted issue: the scan_summary.txt was created inside test_data and then 
included in the grep scan, causing the summary to include its own output and
inflate pattern totals. Corrected totals (excluding the summary file) were
computed and reported.

3) Action Items — Tasks Completed (with key outputs)
- Inspected current directory:
  - pwd -> /Users/jinx0a/Repo/camel/terminal_demo
  - ls -la -> listed files and directories in the working directory.
"""


def cleanup_demo():
    """Clean up demo files"""
    import shutil

    if os.path.exists("food_demo"):
        shutil.rmtree("food_demo")
        print("🧹 Cleaned up food demo files")

    if os.path.exists("terminal_demo"):
        shutil.rmtree("terminal_demo")
        print("🧹 Cleaned up terminal demo files")


if __name__ == "__main__":
    try:
        # Run food preference demo
        # food_preference_demo()

        # print("\n" + "=" * 80)
        # print("🔄 RUNNING SECOND DEMO...")
        # print("=" * 80)

        # Run terminal toolkit demo
        terminal_toolkit_demo()

        print("\n" + "-" * 40)
        cleanup = input("Clean up demo files? (y/N): ").strip().lower()
        if cleanup in ['y', 'yes']:
            cleanup_demo()
        else:
            print("Demo files kept for inspection.")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
