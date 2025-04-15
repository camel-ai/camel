# examples/toolkits/pyautogui_toolkit.py
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

"""Example of using the PyAutoGUI toolkit with CAMEL agents for GUI automation."""

import dotenv
import time

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.toolkits import PyAutoGUIToolkit
from camel.types import ModelPlatformType, ModelType

# Load environment variables from .env file (including OPENAI_API_KEY)
dotenv.load_dotenv()

# Set up logging
logger = get_logger(__name__)

def setup_pyautogui_agent(model_type=ModelType.GPT_4O_MINI, temperature=0.1):
    r"""Create and setup a CAMEL agent with PyAutoGUI tools.
    
    Args:
        model_type: The model type to use (default: GPT-4O-MINI)
        temperature: Model temperature parameter (default: 0.1)
        
    Returns:
        ChatAgent: A configured agent with PyAutoGUI tools
    """
    # Create a model with specified parameters
    model_config = ChatGPTConfig(temperature=temperature)
    model = ModelFactory.create(
        model_type=model_type,
        model_platform=ModelPlatformType.OPENAI,
        model_config_dict=model_config.as_dict(),
    )
    
    # Create PyAutoGUI toolkit and get available tools
    toolkit = PyAutoGUIToolkit()
    tools = toolkit.get_tools()
    
    # System message for the agent
    system_message = (
        "You are an AutoGUI assistant that can control the computer using "
        "the PyAutoGUI toolkit. "
        "You can move the mouse, click, type text, take screenshots, and more. "
        "Always respect safety boundaries when interacting with the GUI. "
        "When asked to perform operations, use the provided tools and describe "
        "what you're doing. "
        "Monitor for potential errors and handle them appropriately."
    )
    
    # Create and configure the agent
    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=tools,
    )
    
    return agent

def run_automated_demo():
    r"""Run an automated demonstration of all PyAutoGUI toolkit features.
    
    This demonstration will:
    1. Get screen size and mouse position
    2. Move mouse to different positions
    3. Click at a position
    4. Type some text
    5. Take a screenshot
    """
    # Print introduction
    print("\n==== AUTOMATED PYAUTOGUI TOOLKIT DEMONSTRATION ====\n")
    print("This demonstration will showcase all PyAutoGUI toolkit features automatically")
    print("No user input is required. Please do not interrupt the process.\n")
    
    # Create a chat agent with PyAutoGUI tools
    agent = setup_pyautogui_agent()
    
    # Define a series of tasks to showcase all toolkit features
    tasks = [
        # Task 1: Get screen information and take a screenshot
        "Perform these steps in sequence without asking for confirmation:\n"
        "1. Get the current screen size and mouse position\n"
        "2. Move the mouse to the center of the screen \n"
        "3. Click at that position\n"
        "4. Take a screenshot to document the result\n",
        
        # Task 2: Keyboard entry and key pressing
        "Perform these steps in sequence without asking for confirmation:\n"
        "1. Open a terminal window\n"
        "2. Type 'echo \"Hello from CAMEL PyAutoGUI\"'\n"
        "3. Press the Enter key\n"
        "4. Press the key combination Ctrl+C to exit the process if needed\n",
        
        # Task 3: Complex mouse operations
        "Perform these steps in sequence without asking for confirmation:\n"
        "1. Move the mouse to the top left quadrant of the screen (25% of screen width and height)\n"
        "2. Drag the mouse to the bottom right quadrant (75% of screen width and height)\n"
        "3. Scroll the mouse wheel down a few clicks\n"
        "4. Take a screenshot to document the result\n",
    ]
    
    # Run each task in sequence
    for i, task in enumerate(tasks):
        print("\n" + "=" * 60)
        print(f"EXECUTING TASK {i+1} OF {len(tasks)}")
        print("=" * 60 + "\n")
        print(f"Instruction: {task}")
        print("")
        
        # Execute the task
        response = agent.step(task)
        
        # Print the agent's response
        print(f"\nAgent response: {response.msg.content}")
        
        # Pause before the next task
        if i < len(tasks) - 1:
            print("\nWaiting a moment before the next task...")
            time.sleep(3)
            print("")

def main():
    r"""Main function to run the PyAutoGUI toolkit example."""
    print("Starting PyAutoGUI toolkit automated demonstration...\n")
    run_automated_demo()
    print("\nPyAutoGUI toolkit demonstration completed.")

if __name__ == "__main__":
    main()