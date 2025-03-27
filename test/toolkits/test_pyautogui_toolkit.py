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

import os
import time
import subprocess
from camel.toolkits import PyAutoGUIToolkit

# Create the toolkit instance
pyautogui_toolkit = PyAutoGUIToolkit()

# Basic screen operations
print("==== Screen Operations ====")
screen_size = pyautogui_toolkit.get_screen_size()
print(f"Screen size: {screen_size}")

mouse_pos = pyautogui_toolkit.get_mouse_position()
print(f"Current mouse position: {mouse_pos}")

# Extract screen dimensions for positioning
width, height = map(int, screen_size.split(": ")[1].split("x"))
center_x, center_y = width // 2, height // 2

# Mouse operations
print("\n==== Mouse Operations ====")
print(f"Moving mouse to center ({center_x}, {center_y})...")
pyautogui_toolkit.mouse_move(center_x, center_y, duration=1)
time.sleep(1)

print("Clicking mouse...")
pyautogui_toolkit.mouse_click(button='left', clicks=1)
time.sleep(1)

print("Dragging mouse...")
start_x, start_y = width // 4, height // 4
end_x, end_y = width // 4 * 3, height // 4 * 3
drag_result = pyautogui_toolkit.mouse_drag(start_x, start_y, end_x, end_y, duration=1)
print(drag_result)
time.sleep(1)

print("Scrolling down...")
scroll_result = pyautogui_toolkit.scroll(-3)
print(scroll_result)
time.sleep(1)

# Keyboard operations
print("\n==== Keyboard Operations ====")
print("Pressing Escape key...")
key_result = pyautogui_toolkit.press_key("escape")
print(key_result)
time.sleep(1)

print("Using hotkey combination Alt+Tab...")
hotkey_result = pyautogui_toolkit.hotkey("alt", "tab")
print(hotkey_result)
time.sleep(1)

# Terminal typing demonstration
print("\n==== Terminal Typing Demonstration ====")

# 1. First we'll open a terminal window using the toolkit method
print("Opening terminal using toolkit.open_terminal()...")
terminal_result = pyautogui_toolkit.open_terminal(wait_time=2.0)
print(terminal_result)
# Terminal should now be open

# 2. Now type some commands
print("Typing 'echo Hello from PyAutoGUI' in terminal...")
pyautogui_toolkit.keyboard_type("echo Hello from PyAutoGUI", interval=0.1)
time.sleep(0.5)

# 3. Press Enter to execute
print("Pressing Enter...")
pyautogui_toolkit.press_key("enter")
time.sleep(1)

# 4. Type another command to capture output to a file
print("Typing command to save output to file...")
output_file = os.path.expanduser("~/Desktop/pyautogui_output.txt")
command = f"echo 'Terminal test at {time.strftime('%Y-%m-%d %H:%M:%S')}' > {output_file}"
pyautogui_toolkit.keyboard_type(command, interval=0.1)
time.sleep(0.5)

# 5. Press Enter to execute
pyautogui_toolkit.press_key("enter")
time.sleep(1)

# 6. Read back the file we created
print("\nReading the output file:")
if os.path.exists(output_file):
    file_content = pyautogui_toolkit.read_file(output_file)
    print(f"Content: {file_content}")
else:
    print("Output file not found, may need more time to be created")

# 7. Close the terminal with Command+W
print("\nClosing terminal window...")
pyautogui_toolkit.hotkey("command", "w")
time.sleep(0.5)
# If Terminal asks to confirm, press Enter to confirm
pyautogui_toolkit.press_key("enter")

# File operations
print("\n==== File Operations ====")
test_file = os.path.expanduser("~/Desktop/pyautogui_test.txt")
test_content = "This is a test file created by PyAutoGUIToolkit\nTime: " + time.strftime("%Y-%m-%d %H:%M:%S")

print(f"Writing to file: {test_file}")
write_result = pyautogui_toolkit.write_to_file(test_file, test_content)
print(write_result)

print(f"Reading from file: {test_file}")
read_result = pyautogui_toolkit.read_file(test_file)
print(f"File content: {read_result}")

# Screenshot
print("\n==== Screenshot ====")
print("Taking screenshot...")
screenshot_result = pyautogui_toolkit.take_screenshot()
print(screenshot_result)

'''
Example output:
==== Screen Operations ====
Screen size: 1920x1080
Current mouse position: (960, 540)

==== Mouse Operations ====
Moving mouse to center (960, 540)...
Clicking mouse...
Dragging mouse...
Dragged from (480, 270) to (1440, 810)
Scrolling down...
Scrolled -3 click(s)

==== Keyboard Operations ====
Pressing Escape key...
Pressed key: escape
Using hotkey combination Alt+Tab...
Hotkey pressed: alt+tab

==== Terminal Typing Demonstration ====
Opening terminal using toolkit.open_terminal()...
Terminal opened on Darwin
Typing 'echo Hello from PyAutoGUI' in terminal...
Pressing Enter...
Typing command to save output to file...
Reading the output file:
Content: Terminal test at 2025-03-27 16:59:00

Closing terminal window...

==== File Operations ====
Writing to file: /Users/mac/Desktop/pyautogui_test.txt
Content written to /Users/mac/Desktop/pyautogui_test.txt
Reading from file: /Users/mac/Desktop/pyautogui_test.txt
File content: This is a test file created by PyAutoGUIToolkit
Time: 2025-03-27 16:59:00

==== Screenshot ====
Taking screenshot...
Screenshot saved to /Users/mac/camel_screenshots/screenshot_1718053740.png

'''