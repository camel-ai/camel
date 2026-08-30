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

import time

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import WechatyToolkit
from camel.types import ModelPlatformType, ModelType
from camel.configs import ChatGPTConfig


def main():
    # Initialize Wechaty toolkit
    wechaty_toolkit = WechatyToolkit()

    # Create model
    # model = ModelFactory.create(
    #     model_platform=ModelPlatformType.DEFAULT,
    #     model_type=ModelType.DEFAULT,
    # )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1,
        model_config_dict=ChatGPTConfig().as_dict(),
    )

    # Create agent with Wechaty toolkit
    agent = ChatAgent(
        system_message="You are a WeChat assistant. Help test WeChat functions.",
        model=model,
        tools=wechaty_toolkit.get_tools(),
    )

    # Wait for connection
    print("Waiting for WeChat connection...")
    time.sleep(3)

    # Test 1: Get contacts list
    print("\n" + "="*50)
    print("Test 1: Get Contacts List")
    print("="*50)
    response = agent.step("Get my WeChat contacts list")
    print("Response:", response.msgs[0].content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")

    # Test 2: Get rooms list
    print("\n" + "="*50)
    print("Test 2: Get Rooms List")
    print("="*50)
    response = agent.step("Get my WeChat group rooms list")
    print("Response:", response.msgs[0].content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")

    # Test 3: Get contact info
    print("\n" + "="*50)
    print("Test 3: Get Contact Info")
    print("="*50)
    response = agent.step("Get detailed information about the first contact in my contacts list")
    print("Response:", response.msgs[0].content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")

    # Test 4: Get room info
    print("\n" + "="*50)
    print("Test 4: Get Room Info")
    print("="*50)
    response = agent.step("Get detailed information about the first room in my rooms list")
    print("Response:", response.msgs[0].content)
    print("Tool calls:")
    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"  {i}. {tool_call.tool_name}({tool_call.args})")

    # # Test 5: Send message (demo only)
    # print("\n" + "="*50)
    # print("Test 5: Send Message (Demo)")
    # print("="*50)
    # print("DEMO: To test sending messages, modify the code below:")
    # print("response = agent.step('Send message \"Hello!\" to contact \"Friend Name\"')")
    # print("(Skipped for safety)")

    # # Test 6: Send room message (demo only)
    # print("\n" + "="*50)
    # print("Test 6: Send Room Message (Demo)")
    # print("="*50)
    # print("DEMO: To test sending room messages, modify the code below:")
    # print("response = agent.step('Send message \"Hello everyone!\" to room \"Group Name\"')")
    # print("(Skipped for safety)")

    # # Test 7: Send file (demo only)
    # print("\n" + "="*50)
    # print("Test 7: Send File (Demo)")
    # print("="*50)
    # print("DEMO: To test sending files, modify the code below:")
    # print("response = agent.step('Send file \"/path/to/file.txt\" to contact \"Friend Name\"')")
    # print("(Skipped for safety)")

    # print("\n" + "="*50)
    # print("All tests completed!")
    # print("="*50)


if __name__ == "__main__":
    try:
        import wechaty
        print("Wechaty dependency found")
    except ImportError:
        print("Wechaty not installed. Please run: pip install wechaty")
        exit(1)
    
    # Check for token
    import os
    token = os.environ.get("WECHATY_TOKEN", "")
    if not token:
        print("WARNING: No WECHATY_TOKEN found!")
        print("Please set your Wechaty token:")
        print("export WECHATY_TOKEN='your_token_here'")
        print("Get free token from: https://wechaty.js.org/zh/docs/specs/token")
        print()
    
    main()