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

import os
import time
import dotenv
import subprocess
import inspect

# Load environment variables from .env file (including OPENAI_API_KEY)
dotenv.load_dotenv()

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.configs import ChatGPTConfig
from camel.toolkits import PyAutoGUIToolkit, FunctionTool
from camel.types import ModelType, ModelPlatformType

class VerbosePyAutoGUIToolkit(PyAutoGUIToolkit):
    """A wrapper around PyAutoGUIToolkit that prints each operation as it happens."""
    
    def __init__(self):
        # Initialize the parent class first
        super().__init__()
        
        # Get screen size directly from pyautogui instead of using the method
        # since get_screen_size() returns a formatted string
        import pyautogui
        self.screen_width, self.screen_height = pyautogui.size()
        self.screen_center = (self.screen_width // 2, self.screen_height // 2)
        
        # Define safe boundaries (10% margin from edges)
        self.safe_margin = 0.1
        self.safe_min_x = int(self.screen_width * self.safe_margin)
        self.safe_max_x = int(self.screen_width * (1 - self.safe_margin))
        self.safe_min_y = int(self.screen_height * self.safe_margin)
        self.safe_max_y = int(self.screen_height * (1 - self.safe_margin))
        
        # Disable PyAutoGUI failsafe (use with caution)
        # pyautogui.FAILSAFE = False
        
        # Wrap all methods with logging
        self._wrap_toolkit_methods()
    
    def _get_safe_coordinates(self, x, y):
        """Ensure coordinates are within safe boundaries."""
        safe_x = max(self.safe_min_x, min(x, self.safe_max_x))
        safe_y = max(self.safe_min_y, min(y, self.safe_max_y))
        
        if safe_x != x or safe_y != y:
            print(f"[Safety] Adjusted coordinates from ({x}, {y}) to ({safe_x}, {safe_y})")
        
        return safe_x, safe_y
    
    def _wrap_toolkit_methods(self):
        """Wrap all public methods of the toolkit with logging functionality."""
        # Get all methods from the PyAutoGUIToolkit class
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            # Skip private methods and get_tools
            if name.startswith('_') or name == 'get_tools':
                continue
                
            # Create a wrapper for this method
            wrapped_method = self._create_logging_wrapper(name, method)
            
            # Replace the original method with the wrapped version
            setattr(self, name, wrapped_method)
    
    def _create_logging_wrapper(self, method_name, method):
        """Create a wrapper that logs the method call and its result."""
        # Get the original method's signature
        signature = inspect.signature(method)
        
        # List of methods that affect mouse position
        mouse_position_methods = [
            'mouse_move', 'mouse_click', 'mouse_drag', 'scroll',
            'press_key', 'hotkey', 'keyboard_type'
        ]
        
        # Create a wrapper function that preserves the original signature
        def wrapper(*args, **kwargs):
            # Apply safety checks for mouse operations
            if method_name == 'mouse_move' and len(args) > 2:
                # For mouse_move(self, x, y, ...)
                kwargs['x'], kwargs['y'] = self._get_safe_coordinates(args[1], args[2])
                args = list(args)
                args[1], args[2] = kwargs['x'], kwargs['y']
                args = tuple(args)
            elif method_name == 'mouse_drag' and len(args) > 4:
                # For mouse_drag(self, start_x, start_y, end_x, end_y, ...)
                start_x, start_y = self._get_safe_coordinates(args[1], args[2])
                end_x, end_y = self._get_safe_coordinates(args[3], args[4])
                args = list(args)
                args[1], args[2], args[3], args[4] = start_x, start_y, end_x, end_y
                args = tuple(args)
            elif method_name == 'mouse_click' and len(args) > 2:
                # For mouse_click with x, y coordinates
                kwargs['x'], kwargs['y'] = self._get_safe_coordinates(args[1], args[2])
                args = list(args)
                args[1], args[2] = kwargs['x'], kwargs['y']
                args = tuple(args)
            elif method_name == 'scroll' and 'x' in kwargs and 'y' in kwargs:
                # For scroll with x, y coordinates in kwargs
                kwargs['x'], kwargs['y'] = self._get_safe_coordinates(kwargs['x'], kwargs['y'])
            
            # Format the arguments for display
            arg_strings = []
            if len(args) > 1:  # Skip 'self'
                arg_strings.extend([str(arg) for arg in args[1:]])
            
            # Add keyword arguments
            if kwargs:
                arg_strings.extend([f"{k}={v}" for k, v in kwargs.items()])
            
            arg_display = ', '.join(arg_strings)
            
            # Log the operation start
            print(f"\n[Operation Start] {method_name}({arg_display})")
            
            try:
                # Measure execution time
                start_time = time.time()
                result = method(*args, **kwargs)
                elapsed_time = time.time() - start_time
                
                # Format the result for display
                result_str = str(result)
                if len(result_str) > 100:
                    result_str = result_str[:97] + "..."
                
                # Log the successful completion
                print(f"[Operation Complete] {method_name} - Duration: {elapsed_time:.2f}s")
                print(f"[Operation Result] {result_str}")
                
                # Move mouse back to center after any mouse-affecting operation
                if method_name in mouse_position_methods:
                    print(f"[Safety] Moving mouse back to screen center ({self.screen_center[0]}, {self.screen_center[1]})")
                    # Use the original method from parent class to avoid recursion
                    super(VerbosePyAutoGUIToolkit, self).mouse_move(
                        x=self.screen_center[0], 
                        y=self.screen_center[1], 
                        duration=0.5
                    )
                
                return result
            except Exception as e:
                # Log the error
                print(f"[Operation Error] {method_name} - {str(e)}")
                
                # Even in case of error, try to move mouse back to center
                if method_name in mouse_position_methods:
                    try:
                        print(f"[Safety Recovery] Moving mouse back to screen center")
                        super(VerbosePyAutoGUIToolkit, self).mouse_move(
                            x=self.screen_center[0], 
                            y=self.screen_center[1], 
                            duration=0.5
                        )
                    except:
                        # If this fails too, we can't do much more
                        pass
                
                raise  # Re-raise the exception
        
        # Make the wrapper function look like the original
        wrapper.__name__ = method.__name__
        wrapper.__doc__ = method.__doc__
        wrapper.__module__ = method.__module__
        wrapper.__signature__ = signature
        
        return wrapper
    
    def get_tools(self):
        """Return a filtered list of tools that excludes those not implemented in parent class."""
        # 直接指定要使用的方法，避免调用不存在的方法
        available_methods = [
            self.mouse_move,
            self.mouse_click,
            self.keyboard_type,
            self.take_screenshot,
            self.get_screen_size,
            self.get_mouse_position,
            self.press_key,
            self.hotkey,
            self.mouse_drag,
            self.scroll,
            self.write_to_file,
            self.read_file,
            self.open_terminal,
        ]
        
        # 检查是否有双击、右击和中键点击方法
        optional_methods = ['double_click', 'right_click', 'middle_click']
        for method_name in optional_methods:
            if hasattr(self, method_name):
                available_methods.append(getattr(self, method_name))
        
        # 创建FunctionTool实例列表
        return [FunctionTool(method) for method in available_methods]

def setup_pyautogui_agent(model_type=ModelType.GPT_3_5_TURBO, temperature=0.1):
    """Create and setup a CAMEL agent with PyAutoGUI tools.
    
    Args:
        model_type: The model type to use (default: GPT-3.5-TURBO)
        temperature: Model temperature for output variation (default: 0.1)
        
    Returns:
        agent: Configured ChatAgent with PyAutoGUI tools
    """
    # Define system message with capabilities and safety guidelines
    system_message = """You are an advanced automation assistant with the ability to control the computer's GUI.
You can use PyAutoGUI toolkit to perform various operations such as:

1. Screen operations: get screen size, take screenshots, determine mouse position
2. Mouse operations: move cursor, click, drag, scroll
3. Keyboard operations: type text, press keys, use keyboard shortcuts
4. File operations: read and write files
5. Terminal operations: open and interact with terminal windows

IMPORTANT SAFETY RULES:
- Always check screen size before moving the mouse to avoid errors
- Keep mouse movements within safe areas of the screen
- Introduce small delays between operations for reliability
- Be careful with keyboard shortcuts that might close applications
- Always confirm understanding of requested tasks before execution

When asked to perform a task, think step by step:
1. What information do you need first? (e.g., screen size)
2. What is the safest way to accomplish the goal?
3. How can you verify the operation succeeded?

Explain your process clearly as you execute commands."""

    # Create model
    model_config = ChatGPTConfig(temperature=temperature)
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=model_type,
        model_config_dict=model_config.as_dict(),
    )
    
    # Create toolkit with verbose output
    toolkit = VerbosePyAutoGUIToolkit()
    
    # Create agent
    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=toolkit.get_tools(),
    )
    
    return agent

def run_automated_demo():
    """Run a fully automated demonstration of all PyAutoGUI toolkit features without any user intervention.
    
    This function executes a sequence of tasks that demonstrate all the capabilities
    of the PyAutoGUI toolkit in a single continuous flow.
    """
    print("\n==== AUTOMATED PYAUTOGUI TOOLKIT DEMONSTRATION ====\n")
    print("This demonstration will showcase all PyAutoGUI toolkit features automatically")
    print("No user input is required. Please do not interrupt the process.\n")
    
    # Setup the agent
    agent = setup_pyautogui_agent(temperature=0.1)
    
    # Define comprehensive tasks that cover all toolkit capabilities
    tasks = [
        # Task 1: Screen Information and Basic Mouse Operations
        """Perform these steps in sequence without asking for confirmation:
1. Get the current screen size and mouse position
2. Move the mouse to the center of the screen 
3. Click at that position
4. Take a screenshot to document the result""",
        
        # Task 2: File Operations and Advanced Mouse Actions
        """Continuing the demonstration, please perform these steps without asking for confirmation:
1. Create a text file on the Desktop named "pyautogui_demo.txt" containing the current date/time
2. Read the file back to verify it was created correctly
3. Get the screen size and calculate safe coordinates for a drag operation
4. Move the mouse to perform a drag operation from 20% of screen width/height to 80% of screen width/height
5. Scroll down a few clicks to simulate reviewing content""",
        
        # Task 3: Keyboard and Terminal Operations
        """Complete the demonstration by performing these final steps without asking for confirmation:
1. Move the mouse to the center of the screen for safety
2. Press the Escape key (which is safe and typically just closes dialogs)
3. Use a hotkey combination like Alt+Tab briefly to demonstrate keyboard shortcuts
4. Open a terminal window
5. Type a short message like 'echo "PyAutoGUI Test Complete"' 
6. Press Enter to execute the command
7. Wait briefly to see the output and then close the terminal"""
    ]
    
    # Execute each task automatically with minimal delay between tasks
    for i, task in enumerate(tasks):
        print(f"\n{'='*60}")
        print(f"EXECUTING TASK {i+1} OF {len(tasks)}")
        print(f"{'='*60}\n")
        print(f"Instruction: {task}\n")
        
        # Get agent response and execute actions
        response = agent.step(task)
        
        # Display results of the current task
        print(f"\nTask {i+1} Summary:")
        print("-" * 40)
        print(response.msg.content)
        
        # Brief pause between tasks
        if i < len(tasks) - 1:
            print(f"\nMoving to next task in 2 seconds...")
            time.sleep(2)
    
    print("\n" + "="*60)
    print("AUTOMATED DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nAll PyAutoGUI toolkit features have been demonstrated.")
    print("Check the desktop for created files and screenshots.\n")

def main():
    """Main function to run the automated demo."""
    print("Starting PyAutoGUI toolkit automated demonstration...")
    run_automated_demo()

if __name__ == "__main__":
    main()