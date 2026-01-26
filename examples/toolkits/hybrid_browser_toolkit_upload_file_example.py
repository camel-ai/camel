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
Example script to test the browser_upload_file functionality using ChatAgent.

This example demonstrates how to:
1. Create a test file
2. Use ChatAgent with browser tools to upload the file
3. Verify the upload was successful

Usage:
    python examples/toolkits/hybrid_browser_toolkit_upload_file_example.py
"""
import asyncio
import logging
import os
import tempfile

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import HybridBrowserToolkit
from camel.types import ModelPlatformType, ModelType

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ],
)

logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.toolkits.hybrid_browser_toolkit').setLevel(
    logging.DEBUG
)

USER_DATA_DIR = "User_Data"


def create_test_file() -> str:
    """Create a temporary test file for uploading."""
    test_content = """This is a test file for browser upload functionality.
Created by CAMEL hybrid_browser_toolkit example.
File upload test - success!
"""
    # Create a temporary file that persists
    fd, filepath = tempfile.mkstemp(suffix='.txt', prefix='camel_upload_test_')
    with os.fdopen(fd, 'w') as f:
        f.write(test_content)
    print(f"Created test file: {filepath}")
    return filepath


async def main() -> None:
    # test_file_path = create_test_file()
    test_file_path = '/Users/didi/Documents/opensource/camel/README.md'

    # Initialize the model
    model_backend = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict={"temperature": 0.0, "top_p": 1},
    )

    # Initialize toolkit with upload_file enabled
    custom_tools = [
        "browser_open",
        "browser_close",
        "browser_visit_page",
        "browser_click",
        "browser_type",
        "browser_enter",
        "browser_upload_file",  # Enable file upload tool
    ]

    web_toolkit = HybridBrowserToolkit(
        headless=False,
        user_data_dir=USER_DATA_DIR,
        enabled_tools=custom_tools,
        browser_log_to_file=True,
        stealth=True,
    )
    print(f"Enabled tools: {web_toolkit.enabled_tools}")

    # Create agent with browser tools
    agent = ChatAgent(
        model=model_backend,
        tools=[*web_toolkit.get_tools()],
        max_iteration=10,
    )

    # Define the task prompt with the actual file path
    TASK_PROMPT = f"""
Please help me test the file upload functionality:

1. First, visit the file upload test page: https://the-internet.herokuapp.com/upload
2. Use the browser_upload_file tool to upload the file at this path: {test_file_path}
   - You need to find the file input element (like "Choose File" button) and use its ref
   - The ref can be found in the page snapshot
3. Verify the upload was successful by checking if the page shows the uploaded filename

Report back whether the upload was successful or not.
"""

    try:
        print("\n" + "=" * 60)
        print("Task:", TASK_PROMPT)
        print("=" * 60 + "\n")

        response = await agent.astep(TASK_PROMPT)

        print(str(response.info['tool_calls']))
        print("\n" + "=" * 60)
        print("Response from agent:")
        print("=" * 60)
        print(response.msgs[0].content if response.msgs else "<no response>")

    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        print("\n--- Closing browser ---")
        await web_toolkit.browser_close()
        print("Browser closed.")



if __name__ == "__main__":
    asyncio.run(main())
