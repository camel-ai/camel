# camel/toolkits/pyautogui_toolkit.py
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

from typing import List, Optional, Tuple

from camel.logger import get_logger
import subprocess
import os
import time
from camel.toolkits import BaseToolkit, FunctionTool

# Set up logging
logger = get_logger(__name__)


class PyAutoGUIToolkit(BaseToolkit):
    r"""A toolkit for automating GUI interactions using PyAutoGUI."""
    
    @dependencies_required('pyautogui')
    def __init__(self):
        super().__init__()
        # Import pyautogui here to make it an optional dependency
        import pyautogui
        # Configure PyAutoGUI for safety
        pyautogui.FAILSAFE = True  # Move mouse to upper-left to abort

        # Get screen size for safety boundaries
        self.screen_width, self.screen_height = pyautogui.size()
        # Define safe boundaries (10% margin from edges)
        self.safe_margin = 0.1
        self.safe_min_x = int(self.screen_width * self.safe_margin)
        self.safe_max_x = int(self.screen_width * (1 - self.safe_margin))
        self.safe_min_y = int(self.screen_height * self.safe_margin)
        self.safe_max_y = int(self.screen_height * (1 - self.safe_margin))
        self.screen_center = (self.screen_width // 2, self.screen_height // 2)
    
    def _get_safe_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        r"""Ensure coordinates are within safe boundaries to prevent triggering failsafe.
        
        Args:
            x (int): Original x-coordinate
            y (int): Original y-coordinate
            
        Returns:
            Tuple[int, int]: Safe coordinates
        """
        safe_x = max(self.safe_min_x, min(x, self.safe_max_x))
        safe_y = max(self.safe_min_y, min(y, self.safe_max_y))
        
        if safe_x != x or safe_y != y:
            logger.info(f"Safety: Adjusted coordinates from ({x}, {y}) to ({safe_x}, {safe_y})")
        
        return safe_x, safe_y

    def mouse_move(self, x: int, y: int, duration: float = 0.5) -> str:
        r"""Move mouse pointer to specified coordinates.
        
        Args:
            x (int): X-coordinate to move to.
            y (int): Y-coordinate to move to.
            duration (float): How long the movement should take in seconds.
                (default: :obj:`0.5`)
            
        Returns:
            str: Success or error message.
        """
        try:
            # Apply safety boundaries
            safe_x, safe_y = self._get_safe_coordinates(x, y)
            pyautogui.moveTo(safe_x, safe_y, duration=duration)
            return f"Mouse moved to position ({safe_x}, {safe_y})"
        except Exception as e:
            logger.error(f"Error moving mouse: {e}")
            return f"Error: {str(e)}"
            
    def mouse_click(
        self, 
        button: str = 'left', 
        clicks: int = 1,
        x: Optional[int] = None,
        y: Optional[int] = None
    ) -> str:
        r"""Click the mouse at current position.
        
        Args:
            button (str): Button to click ('left', 'middle', 'right').
                (default: :obj:`'left'`)
            clicks (int): Number of clicks.
                (default: :obj:`1`)
            x (Optional[int]): X-coordinate to click at. If None, uses current position.
                (default: :obj:`None`)
            y (Optional[int]): Y-coordinate to click at. If None, uses current position.
                (default: :obj:`None`)
                
        Returns:
            str: Success or error message.
        """
        try:
            # Apply safety boundaries if coordinates are specified
            if x is not None and y is not None:
                safe_x, safe_y = self._get_safe_coordinates(x, y)
                pyautogui.click(x=safe_x, y=safe_y, button=button, clicks=clicks)
            else:
                pyautogui.click(button=button, clicks=clicks)
            return f"Clicked {button} button {clicks} time(s)"
        except Exception as e:
            logger.error(f"Error clicking mouse: {e}")
            return f"Error: {str(e)}"
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        r"""Double-click the left mouse button.
        
        Args:
            x (Optional[int]): X-coordinate to double-click at. If None, uses current position.
                (default: :obj:`None`)
            y (Optional[int]): Y-coordinate to double-click at. If None, uses current position.
                (default: :obj:`None`)
            
        Returns:
            str: Success or error message.
        """
        try:
            # Apply safety boundaries if coordinates are specified
            if x is not None and y is not None:
                safe_x, safe_y = self._get_safe_coordinates(x, y)
                pyautogui.doubleClick(x=safe_x, y=safe_y)
            else:
                pyautogui.doubleClick()
            return f"Double-clicked at position ({safe_x}, {safe_y})"
        except Exception as e:
            logger.error(f"Error double-clicking: {e}")
            return f"Error: {str(e)}"
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        r"""Right-click the mouse.
        
        Args:
            x (Optional[int]): X-coordinate to right-click at. If None, uses current position.
                (default: :obj:`None`)
            y (Optional[int]): Y-coordinate to right-click at. If None, uses current position.
                (default: :obj:`None`)
            
        Returns:
            str: Success or error message.
        """
        try:
            # Apply safety boundaries if coordinates are specified
            if x is not None and y is not None:
                safe_x, safe_y = self._get_safe_coordinates(x, y)
                pyautogui.rightClick(x=safe_x, y=safe_y)
            else:
                pyautogui.rightClick()
            return f"Right-clicked at position ({safe_x}, {safe_y})"
        except Exception as e:
            logger.error(f"Error right-clicking: {e}")
            return f"Error: {str(e)}"
    
    def middle_click(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        r"""Middle-click the mouse.
        
        Args:
            x (Optional[int]): X-coordinate to middle-click at. If None, uses current position.
                (default: :obj:`None`)
            y (Optional[int]): Y-coordinate to middle-click at. If None, uses current position.
                (default: :obj:`None`)
            
        Returns:
            str: Success or error message.
        """
        try:
            # Apply safety boundaries if coordinates are specified
            if x is not None and y is not None:
                safe_x, safe_y = self._get_safe_coordinates(x, y)
                pyautogui.middleClick(x=safe_x, y=safe_y)
            else:
                pyautogui.middleClick()
            return f"Middle-clicked at position ({safe_x}, {safe_y})"
        except Exception as e:
            logger.error(f"Error middle-clicking: {e}")
            return f"Error: {str(e)}"
    
    def get_mouse_position(self) -> str:
        r"""Get current mouse position.
        
        Returns:
            str: Current mouse X and Y coordinates.
        """
        try:
            x, y = pyautogui.position()
            return f"Mouse position: ({x}, {y})"
        except Exception as e:
            logger.error(f"Error getting mouse position: {e}")
            return f"Error: {str(e)}"
    
    def get_screen_size(self) -> str:
        r"""Get screen size.
        
        Returns:
            str: Screen width and height.
        """
        try:
            width, height = pyautogui.size()
            return f"Screen size: {width}x{height}"
        except Exception as e:
            logger.error(f"Error getting screen size: {e}")
            return f"Error: {str(e)}"
    
    def take_screenshot(self, left: int = 0, top: int = 0, width: Optional[int] = None, height: Optional[int] = None) -> str:
        r"""Take a screenshot.
        
        Args:
            left (int): Left coordinate of the screenshot region.
                (default: :obj:`0`)
            top (int): Top coordinate of the screenshot region.
                (default: :obj:`0`)
            width (Optional[int]): Width of the screenshot region. If None, uses full screen width.
                (default: :obj:`None`)
            height (Optional[int]): Height of the screenshot region. If None, uses full screen height.
                (default: :obj:`None`)
            
        Returns:
            str: Path to the saved screenshot.
        """
        try:
            # Apply safety boundaries to all coordinates
            safe_left, safe_top = self._get_safe_coordinates(left, top)
            
            # If width or height is not specified, use the available space
            if width is None:
                width = self.screen_width - safe_left
            if height is None:
                height = self.screen_height - safe_top
                
            # Ensure the region doesn't exceed screen boundaries
            if safe_left + width > self.screen_width:
                width = self.screen_width - safe_left
            if safe_top + height > self.screen_height:
                height = self.screen_height - safe_top
            
            # Create directory for screenshots if it doesn't exist
            screenshots_dir = os.path.expanduser("~/camel_screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Take screenshot
            screenshot = pyautogui.screenshot(region=(safe_left, safe_top, width, height))
            
            # Save screenshot to file
            timestamp = int(time.time())
            screenshot_path = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
            screenshot.save(screenshot_path)
            
            return f"Screenshot saved to {screenshot_path}"
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return f"Error: {str(e)}"
    
    def mouse_drag(
        self, 
        start_x: int, 
        start_y: int, 
        end_x: int, 
        end_y: int, 
        duration: float = 0.5, 
        button: str = 'left'
    ) -> str:
        r"""Drag mouse from start position to end position.
        
        Args:
            start_x (int): Starting x-coordinate.
            start_y (int): Starting y-coordinate.
            end_x (int): Ending x-coordinate.
            end_y (int): Ending y-coordinate.
            duration (float): How long the drag should take in seconds.
                (default: :obj:`0.5`)
            button (str): Mouse button to use ('left', 'middle', 'right').
                (default: :obj:`'left'`)
            
        Returns:
            str: Success or error message.
        """
        try:
            # Apply safety boundaries to both start and end positions
            safe_start_x, safe_start_y = self._get_safe_coordinates(start_x, start_y)
            safe_end_x, safe_end_y = self._get_safe_coordinates(end_x, end_y)
            
            # Break operation into smaller steps for safety
            # First move to start position
            pyautogui.moveTo(safe_start_x, safe_start_y, duration=duration/3)
            # Then perform drag
            pyautogui.dragTo(safe_end_x, safe_end_y, duration=duration/3, button=button)
            # Finally, move to a safe position (screen center) afterwards
            pyautogui.moveTo(self.screen_center[0], self.screen_center[1], duration=duration/3)
            
            return f"Dragged from ({safe_start_x}, {safe_start_y}) to ({safe_end_x}, {safe_end_y})"
        except Exception as e:
            logger.error(f"Error dragging mouse: {e}")
            # Try to move to safe position even after error
            try:
                pyautogui.moveTo(self.screen_center[0], self.screen_center[1], duration=0.2)
            except:
                pass
            return f"Error: {str(e)}"

    def scroll(self, scroll_amount: int, x: Optional[int] = None, y: Optional[int] = None) -> str:
        r"""Scroll the mouse wheel.
        
        Args:
            scroll_amount (int): Amount to scroll. Positive values scroll up, negative values scroll down.
            x (Optional[int]): X-coordinate to scroll at. If None, uses current position.
                (default: :obj:`None`)
            y (Optional[int]): Y-coordinate to scroll at. If None, uses current position.
                (default: :obj:`None`)
            
        Returns:
            str: Success or error message.
        """
        try:
            # Get current mouse position if coordinates are not specified
            if x is None or y is None:
                current_x, current_y = pyautogui.position()
                x = x if x is not None else current_x
                y = y if y is not None else current_y
            
            # Always apply safety boundaries
            safe_x, safe_y = self._get_safe_coordinates(x, y)
            pyautogui.scroll(scroll_amount, x=safe_x, y=safe_y)
            
            # Move mouse back to screen center for added safety
            pyautogui.moveTo(self.screen_center[0], self.screen_center[1])
            logger.info(f"Safety: Moving mouse back to screen center ({self.screen_center[0]}, {self.screen_center[1]})")
            
            return f"Scrolled {scroll_amount} click(s)"
        except Exception as e:
            logger.error(f"Error scrolling: {e}")
            return f"Error: {str(e)}"
    
    def keyboard_type(self, text: str, interval: float = 0.0) -> str:
        r"""Type text on the keyboard.
        
        Args:
            text (str): Text to type.
            interval (float): Seconds to wait between keypresses.
                (default: :obj:`0.0`)
            
        Returns:
            str: Success or error message.
        """
        try:
            # Validate text input
            if not isinstance(text, str):
                return f"Error: Input must be a string, got {type(text).__name__}"
                
            if not text:
                return "Error: Cannot type empty text"
                
            if len(text) > 1000:  # Set a reasonable maximum length limit
                logger.warning(f"Warning: Very long text ({len(text)} characters) may cause performance issues")
                
            # First, move mouse to a safe position to prevent potential issues
            pyautogui.moveTo(self.screen_center[0], self.screen_center[1], duration=0.1)
            
            pyautogui.write(text, interval=interval)
            return f"Typed text: {text[:20]}{'...' if len(text) > 20 else ''}"
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return f"Error: {str(e)}"
    
    def press_key(self, key: str) -> str:
        r"""Press a key on the keyboard.
        
        Args:
            key (str): Key to press.
            
        Returns:
            str: Success or error message.
        """
        try:
            # Basic validation
            if not isinstance(key, str):
                return f"Error: Key must be a string, got {type(key).__name__}"
            
            if not key:
                return "Error: Cannot press empty key"
            
            # Length validation (most valid key names are short)
            if len(key) > 20:
                return f"Error: Key name '{key}' is too long (max 20 characters)"
                
            # Special character validation (key names usually don't contain special characters)
            import re
            if re.search(r'[^\w+\-_]', key) and len(key) > 1:  # 允许单个特殊字符
                logger.warning(f"Warning: Key '{key}' contains unusual characters")
            
            # First, move mouse to a safe position to prevent potential issues
            pyautogui.moveTo(self.screen_center[0], self.screen_center[1], duration=0.1)
            
            pyautogui.press(key)
            return f"Pressed key: {key}"
        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            return f"Error: Invalid key '{key}' or error pressing it. {str(e)}"
    
    def hotkey(self, *keys) -> str:
        r"""Press keys in succession and release in reverse order.
        
        Args:
            *keys: Keys to press.
            
        Returns:
            str: Success or error message.
        """
        try:
            # First, move mouse to a safe position to prevent potential issues
            pyautogui.moveTo(self.screen_center[0], self.screen_center[1], duration=0.1)
            
            pyautogui.hotkey(*keys)
            return f"Pressed hotkey: {'+'.join(keys)}"
        except Exception as e:
            logger.error(f"Error pressing hotkey: {e}")
            return f"Error: {str(e)}"
  
    def open_terminal(self, wait_time: int = 2, force_english_input: bool = False) -> str:
        r"""Open a terminal window.
        
        Args:
            wait_time (int): Seconds to wait for terminal to open.
                (default: :obj:`2`)
            force_english_input (bool): Force English input method.
                (default: :obj:`False`)
            
        Returns:
            str: Success or error message.
        """
        try:
            # Move to safe position first
            pyautogui.moveTo(self.screen_center[0], self.screen_center[1], duration=0.1)
            
            import platform
            
            os_name = platform.system()
            if os_name == 'Darwin':  # macOS
                if force_english_input:
                    subprocess.Popen(['open', '-a', 'Terminal', '--args', 'LANG=en_US.UTF-8'])
                else:
                    subprocess.Popen(['open', '-a', 'Terminal'])
            elif os_name == 'Windows':
                subprocess.Popen(['cmd.exe'])
            elif os_name == 'Linux':
                # Try common terminal emulators
                for terminal in ['gnome-terminal', 'konsole', 'xterm']:
                    try:
                        subprocess.Popen([terminal])
                        break
                    except FileNotFoundError:
                        continue
            
            time.sleep(wait_time)  # Wait for terminal to open
            return f"Terminal opened on {os_name} with {'English' if force_english_input else 'default'} input method"
        except Exception as e:
            logger.error(f"Error opening terminal: {e}")
            return f"Error: {str(e)}"
    
    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects for PyAutoGUI operations.
        
        Returns:
            List[FunctionTool]: List of PyAutoGUI functions.
        """
        return [
            FunctionTool(self.mouse_move),
            FunctionTool(self.mouse_click),
            FunctionTool(self.keyboard_type),
            FunctionTool(self.take_screenshot),
            FunctionTool(self.get_screen_size),
            FunctionTool(self.get_mouse_position),
            FunctionTool(self.press_key),
            FunctionTool(self.hotkey),
            FunctionTool(self.mouse_drag),
            FunctionTool(self.scroll),
            FunctionTool(self.open_terminal), 
        ]