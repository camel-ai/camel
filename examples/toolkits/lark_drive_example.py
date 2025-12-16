# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
"""
Lark Agent Example - Testing Tool Calling Sequences

This example demonstrates how a ChatAgent uses the LarkToolkit to create
documents in Lark. It tests whether the agent correctly identifies which
tools to call for different scenarios:

1. Create document in default location (root folder - automatic)
2. Create document in an existing folder (by name)
3. Create document in a new folder

The example shows the complete tool calling sequence for each scenario,
helping you understand how the agent reasons about which tools to use.

Prerequisites:
1. Create an app at https://open.larksuite.com/app
2. Enable OAuth 2.0 and add http://localhost:9000/callback as redirect URI
3. Enable permissions: docx:document, drive:drive, drive:drive:readonly
4. Set environment variables:
   - LARK_APP_ID: Your application ID
   - LARK_APP_SECRET: Your application secret

Usage:
    python examples/toolkits/lark_drive_example.py
"""

import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import LarkToolkit
from camel.types import ModelPlatformType, ModelType


def print_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f" {title}")
    print(f"{'='*70}")


def print_tool_calls(tool_calls: list):
    """Pretty print the tool calling sequence."""
    if not tool_calls:
        print("  No tool calls made")
        return

    print(f"\n  Tool Calling Sequence ({len(tool_calls)} calls):")
    print("  " + "-" * 50)

    for i, call in enumerate(tool_calls, 1):
        print(f"\n  Step {i}: {call.tool_name}")

        # Print arguments
        if call.args:
            print("    Arguments:")
            for key, value in call.args.items():
                # Truncate long values
                str_value = str(value)
                if len(str_value) > 60:
                    str_value = str_value[:60] + "..."
                print(f"      {key}: {str_value}")

        # Print result summary
        if call.result:
            result_str = str(call.result)
            if len(result_str) > 100:
                result_str = result_str[:100] + "..."
            print(f"    Result: {result_str}")


def main():
    """Run the Lark Agent examples."""
    print_header("Lark Agent Example - Tool Calling Sequences")

    # Check environment variables
    print("\nChecking environment variables...")
    app_id_set = os.environ.get("LARK_APP_ID")
    app_secret_set = os.environ.get("LARK_APP_SECRET")
    print(f"  LARK_APP_ID: {'Set' if app_id_set else 'NOT SET'}")
    print(f"  LARK_APP_SECRET: {'Set' if app_secret_set else 'NOT SET'}")

    if not app_id_set or not app_secret_set:
        print("\nPlease set the required environment variables first.")
        return

    # Initialize toolkit and authenticate
    print("\nInitializing LarkToolkit...")
    toolkit = LarkToolkit()

    print("\nStarting OAuth authentication...")
    print("A browser window will open for you to log in to Lark.")

    auth_result = toolkit.authenticate(
        port=9000,
        timeout=120,
        open_browser=True,
    )

    if "error" in auth_result:
        print(f"\nAuthentication failed: {auth_result['error']}")
        return

    print("\nAuthentication successful!")

    # Get toolkit tools
    tools = toolkit.get_tools()
    print(f"\nAvailable tools ({len(tools)}):")
    for tool in tools:
        print(f"  - {tool.func.__name__}")

    # Create the model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Define system message for the agent
    system_message = """You are a helpful assistant that manages Lark \
documents.
You have access to Lark Drive and Document APIs to:
- Get the user's root folder token
- List contents of folders
- Create new folders
- Create documents in specific folders
- Add content blocks to documents

When creating documents, always ensure they are placed in a proper folder
so they appear in the user's document list. If no folder is specified,
the document will automatically be created in the user's root folder.

When asked to create a document in a specific folder by name, first list
the folder contents to find the folder token, then create the document there.

When asked to create a document in a new folder, first create the folder,
then create the document in that new folder."""

    # Initialize the agent
    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=tools,
    )

    # =========================================================================
    # SCENARIO 1: Create document in default location (automatic root folder)
    # =========================================================================
    print_header("SCENARIO 1: Create Document (Default Location)")

    query1 = """Create a Lark document titled 'Meeting Notes - Q4 Planning'
    with a heading that says 'Q4 Planning Meeting' and a bullet point
    that says 'Discuss budget allocation'."""

    print(f"\nUser Query: {query1}")
    print("\nExpected Tool Sequence:")
    print("  1. lark_create_document (auto-fetches root folder internally)")
    print("  2. lark_create_block (heading)")
    print("  3. lark_create_block (bullet)")

    agent.reset()
    response = agent.step(query1)

    print("\nAgent Response:")
    print(f"  {response.msgs[0].content[:500]}...")

    print_tool_calls(response.info.get('tool_calls', []))

    # =========================================================================
    # SCENARIO 2: Create document in existing folder by name
    # =========================================================================
    print_header("SCENARIO 2: Create Document in Existing Folder by Name")

    # First, let's create a folder to use for this test
    print("\nSetup: Creating a test folder 'Agent Test Folder'...")
    setup_result = toolkit.lark_create_folder("Agent Test Folder")
    if "error" in setup_result:
        print(f"  Warning: Could not create test folder: {setup_result}")
    else:
        print(f"  Created folder with token: {setup_result['token']}")

    query2 = """Find my folder called 'Agent Test Folder' and create a
    document inside it titled 'Project Roadmap'. Add a heading that says
    'Project Roadmap 2025'."""

    print(f"\nUser Query: {query2}")
    print("\nExpected Tool Sequence:")
    print("  1. lark_list_folder_contents (to find 'Agent Test Folder')")
    print("  2. lark_create_document (with folder_token)")
    print("  3. lark_create_block (heading)")

    agent.reset()
    response = agent.step(query2)

    print("\nAgent Response:")
    print(f"  {response.msgs[0].content[:500]}...")

    print_tool_calls(response.info.get('tool_calls', []))

    # =========================================================================
    # SCENARIO 3: Create document in a new folder
    # =========================================================================
    print_header("SCENARIO 3: Create Document in a New Folder")

    query3 = """Create a new folder called 'Recipe Collection' and then
    create a document inside it called 'Chinese Menu'. Add a heading
    'Chinese Restaurant Menu' and bullet points for 'Spring Rolls - $6.99',
    'Kung Pao Chicken - $12.99', and 'Fried Rice - $8.99'."""

    print(f"\nUser Query: {query3}")
    print("\nExpected Tool Sequence:")
    print("  1. lark_create_folder ('Recipe Collection')")
    print("  2. lark_create_document (with new folder_token)")
    print("  3. lark_create_block (heading)")
    print("  4. lark_create_block (bullet) x3")

    agent.reset()
    response = agent.step(query3)

    print("\nAgent Response:")
    print(f"  {response.msgs[0].content[:500]}...")

    print_tool_calls(response.info.get('tool_calls', []))

    # =========================================================================
    # SCENARIO 4: List folders and describe contents
    # =========================================================================
    print_header("SCENARIO 4: List and Describe Folder Contents")

    query4 = """List all the folders in my Lark Drive root folder and tell
    me what's there."""

    print(f"\nUser Query: {query4}")
    print("\nExpected Tool Sequence:")
    print("  1. lark_list_folder_contents (root)")

    agent.reset()
    response = agent.step(query4)

    print("\nAgent Response:")
    print(f"  {response.msgs[0].content[:500]}...")

    print_tool_calls(response.info.get('tool_calls', []))

    # =========================================================================
    # SCENARIO 5: Complex multi-step task
    # =========================================================================
    print_header("SCENARIO 5: Complex Multi-Step Task")

    query5 = """I want to organize my work. Please:
    1. Create a folder called 'Work Projects'
    2. Inside that folder, create another folder called 'Q1 2025'
    3. Create a document in the Q1 2025 folder called 'January Tasks'
    4. Add a heading 'Tasks for January 2025' and two todo items:
       'Complete project proposal' and 'Review team feedback'"""

    print(f"\nUser Query: {query5}")
    print("\nExpected Tool Sequence:")
    print("  1. lark_create_folder ('Work Projects')")
    print("  2. lark_create_folder ('Q1 2025', parent=Work Projects)")
    print("  3. lark_create_document (in Q1 2025)")
    print("  4. lark_create_block (heading)")
    print("  5. lark_create_block (todo) x2")

    agent.reset()
    response = agent.step(query5)

    print("\nAgent Response:")
    print(f"  {response.msgs[0].content[:800]}...")

    print_tool_calls(response.info.get('tool_calls', []))

    # =========================================================================
    # Summary
    # =========================================================================
    print_header("SUMMARY")

    print("""
This example demonstrated how the ChatAgent uses LarkToolkit tools to:

1. SCENARIO 1 - Default Location:
   - Agent calls lark_create_document which auto-fetches root folder
   - No explicit folder lookup needed

2. SCENARIO 2 - Existing Folder by Name:
   - Agent first calls lark_list_folder_contents to find folder
   - Then creates document with the found folder_token

3. SCENARIO 3 - New Folder:
   - Agent creates folder first with lark_create_folder
   - Uses returned token to create document in new folder

4. SCENARIO 4 - List Contents:
   - Agent calls lark_list_folder_contents to explore drive

5. SCENARIO 5 - Complex Multi-Step:
   - Agent chains multiple folder and document operations
   - Demonstrates nested folder creation

The agent correctly identifies which tools to call based on the
natural language request, showing proper understanding of the
Lark Drive and Document API workflow.
""")

    print("=" * 70)
    print(" All scenarios completed! Check your Lark Drive for the created")
    print(" folders and documents.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
