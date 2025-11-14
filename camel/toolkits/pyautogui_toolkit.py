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
from typing import List, Literal, Optional, Tuple, Union

from camel.logger import get_logger
from camel.toolkits import BaseToolkit, FunctionTool
from camel.utils import MCPServer, dependencies_required

# Set up logging
logger = get_logger(__name__)

DURATION = 0.1


@MCPServer()
class PyAutoGUIToolkit(BaseToolkit):
    r"""A toolkit for automating GUI interactions using PyAutoGUI."""

    @dependencies_required('pyautogui')
    def __init__(
        self,
        timeout: Optional[float] = None,
        screenshots_dir: str = "tmp",
    ):
        r"""Initializes the PyAutoGUIToolkit with optional timeout.

        Args:
            timeout (Optional[float]): Timeout for API requests in seconds.
                (default: :obj:`None`)
            screenshots_dir (str): Directory to save screenshots.
                (default: :obj:`"tmp"`)
        """
        import pyautogui

        super().__init__(timeout=timeout)
        # Configure PyAutoGUI for safety
        self.pyautogui = pyautogui

        self.pyautogui.FAILSAFE = True  # Move mouse to upper-left to abort

        # Get screen size for safety boundaries
        self.screen_width, self.screen_height = self.pyautogui.size()
        # Define safe boundaries (10% margin from edges)
        self.safe_margin = 0.1
        self.safe_min_x = int(self.screen_width * self.safe_margin)
        self.safe_max_x = int(self.screen_width * (1 - self.safe_margin))
        self.safe_min_y = int(self.screen_height * self.safe_margin)
        self.safe_max_y = int(self.screen_height * (1 - self.safe_margin))
        self.screen_center = (self.screen_width // 2, self.screen_height // 2)
        self.screenshots_dir = os.path.expanduser(screenshots_dir)

    def _get_safe_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        r"""Ensure coordinates are within safe boundaries to prevent triggering
        failsafe.

        Args:
            x (int): Original x-coordinate
            y (int): Original y-coordinate

        Returns:
            Tuple[int, int]: Safe coordinates
        """
        # Clamp coordinates to safe boundaries
        safe_x = max(self.safe_min_x, min(x, self.safe_max_x))
        safe_y = max(self.safe_min_y, min(y, self.safe_max_y))

        if safe_x != x or safe_y != y:
            logger.info(
                f"Safety: Adjusted coordinates from ({x}, {y}) to "
                f"({safe_x}, {safe_y})"
            )

        return safe_x, safe_y

    def mouse_move(self, x: int, y: int) -> str:
        r"""Move mouse pointer to specified coordinates.

        Args:
            x (int): X-coordinate to move to.
            y (int): Y-coordinate to move to.

        Returns:
            str: Success or error message.
        """
        try:
            # Apply safety boundaries
            safe_x, safe_y = self._get_safe_coordinates(x, y)
            self.pyautogui.moveTo(safe_x, safe_y, duration=DURATION)
            return f"Mouse moved to position ({safe_x}, {safe_y})"
        except Exception as e:
            logger.error(f"Error moving mouse: {e}")
            return f"Error: {e}"

    def mouse_click(
        self,
        button: Literal["left", "middle", "right"] = "left",
        clicks: int = 1,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> str:
        r"""Performs a mouse click at the specified coordinates or current
        position.

        Args:
            button (Literal["left", "middle", "right"]): The mouse button to
                click.
                - "left": Typically used for selecting items, activating
                    buttons, or placing the cursor.
                - "middle": Often used for opening links in a new tab or
                    specific application functions.
                - "right": Usually opens a context menu providing options
                    related to the clicked item or area.
                (default: :obj:`"left"`)
            clicks (int): The number of times to click the button.
                - 1: A single click, the most common action.
                - 2: A double-click, often used to open files/folders or
                    select words.
                (default: :obj:`1`)
            x (Optional[int]): The x-coordinate on the screen to move the mouse
                to before clicking. If None, clicks at the current mouse
                position. (default: :obj:`None`)
            y (Optional[int]): The y-coordinate on the screen to move the mouse
                to before clicking. If None, clicks at the current mouse
                position. (default: :obj:`None`)

        Returns:
            str: A message indicating the action performed, e.g.,
                "Clicked left button 1 time(s) at coordinates (100, 150)."
                or "Clicked right button 2 time(s) at current position."
        """
        try:
            # Apply safety boundaries if coordinates are specified
            position_info = "at current position"
            if x is not None and y is not None:
                safe_x, safe_y = self._get_safe_coordinates(x, y)
                self.pyautogui.click(
                    x=safe_x, y=safe_y, button=button, clicks=clicks
                )
                position_info = f"at position ({safe_x}, {safe_y})"
            else:
                self.pyautogui.click(button=button, clicks=clicks)

            return f"Clicked {button} button {clicks} time(s) {position_info}"
        except Exception as e:
            logger.error(f"Error clicking mouse: {e}")
            return f"Error: {e}"

    def get_mouse_position(self) -> str:
        r"""Get current mouse position.

        Returns:
            str: Current mouse X and Y coordinates.
        """
        try:
            x, y = self.pyautogui.position()
            return f"Mouse position: ({x}, {y})"
        except Exception as e:
            logger.error(f"Error getting mouse position: {e}")
            return f"Error: {e}"

    def take_screenshot(self) -> str:
        r"""Take a screenshot.

        Returns:
            str: Path to the saved screenshot or error message.
        """
        try:
            # Create directory for screenshots if it doesn't exist
            os.makedirs(self.screenshots_dir, exist_ok=True)

            # Take screenshot
            screenshot = self.pyautogui.screenshot()

            # Save screenshot to file
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(self.screenshots_dir, filename)
            screenshot.save(filepath)

            return f"Screenshot saved to {filepath}"
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return f"Error: {e}"

    def mouse_drag(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        button: Literal["left", "middle", "right"] = "left",
    ) -> str:
        r"""Drag mouse from start position to end position.

        Args:
            start_x (int): Starting x-coordinate.
            start_y (int): Starting y-coordinate.
            end_x (int): Ending x-coordinate.
            end_y (int): Ending y-coordinate.
            button (Literal["left", "middle", "right"]): Mouse button to use
                ('left', 'middle', 'right'). (default: :obj:`'left'`)

        Returns:
            str: Success or error message.
        """
        try:
            # Apply safety boundaries to both start and end positions
            safe_start_x, safe_start_y = self._get_safe_coordinates(
                start_x, start_y
            )
            safe_end_x, safe_end_y = self._get_safe_coordinates(end_x, end_y)

            # Break operation into smaller steps for safety
            # First move to start position
            self.pyautogui.moveTo(
                safe_start_x, safe_start_y, duration=DURATION
            )
            # Then perform drag
            self.pyautogui.dragTo(
                safe_end_x, safe_end_y, duration=DURATION, button=button
            )
            # Finally, move to a safe position (screen center) afterwards
            self.pyautogui.moveTo(
                self.screen_center[0],
                self.screen_center[1],
                duration=DURATION,
            )

            return (
                f"Dragged from ({safe_start_x}, {safe_start_y}) "
                f"to ({safe_end_x}, {safe_end_y})"
            )
        except Exception as e:
            logger.error(f"Error dragging mouse: {e}")
            # Try to move to safe position even after error
            try:
                self.pyautogui.moveTo(
                    self.screen_center[0],
                    self.screen_center[1],
                    duration=DURATION,
                )
            except Exception as recovery_error:
                logger.error(
                    f"Failed to move to safe position: {recovery_error}"
                )
            return f"Error: {e}"

    def scroll(
        self,
        scroll_amount: int,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> str:
        r"""Scroll the mouse wheel.

        Args:
            scroll_amount (int): Amount to scroll. Positive values scroll up,
                negative values scroll down.
            x (Optional[int]): X-coordinate to scroll at. If None, uses current
                position. (default: :obj:`None`)
            y (Optional[int]): Y-coordinate to scroll at. If None, uses current
                position. (default: :obj:`None`)

        Returns:
            str: Success or error message.
        """
        try:
            # Get current mouse position if coordinates are not specified
            if x is None or y is None:
                current_x, current_y = self.pyautogui.position()
                x = x if x is not None else current_x
                y = y if y is not None else current_y

            # Always apply safety boundaries
            safe_x, safe_y = self._get_safe_coordinates(x, y)
            self.pyautogui.scroll(scroll_amount, x=safe_x, y=safe_y)

            # Move mouse back to screen center for added safety
            self.pyautogui.moveTo(self.screen_center[0], self.screen_center[1])
            logger.info(
                f"Safety: Moving mouse back to screen center "
                f"({self.screen_center[0]}, {self.screen_center[1]})"
            )

            return (
                f"Scrolled {scroll_amount} clicks at position "
                f"{safe_x}, {safe_y}"
            )
        except Exception as e:
            logger.error(f"Error scrolling: {e}")
            return f"Error: {e}"

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
            if not text:
                return "Error: Empty text provided"

            if len(text) > 1000:  # Set a reasonable maximum length limit
                warn_msg = (
                    f"Warning: Very long text ({len(text)} characters) may "
                    f"cause performance issues"
                )
                logger.warning(warn_msg)

            # First, move mouse to a safe position to prevent potential issues
            self.pyautogui.moveTo(
                self.screen_center[0], self.screen_center[1], duration=DURATION
            )

            self.pyautogui.write(text, interval=interval)
            return f"Typed text: {text[:20]}{'...' if len(text) > 20 else ''}"
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return f"Error: {e}"

    def press_key(self, key: Union[str, List[str]]) -> str:
        r"""Press a key on the keyboard.

        Args:
            key (Union[str, List[str]]): The key to be pressed. Can also be a
                list of such strings. Valid key names include:
                - Basic characters: a-z, 0-9, and symbols like !, @, #, etc.
                - Special keys: enter, esc, space, tab, backspace, delete
                - Function keys: f1-f24
                - Navigation: up, down, left, right, home, end, pageup,
                    pagedown
                - Modifiers: shift, ctrl, alt, command, option, win
                - Media keys: volumeup, volumedown, volumemute, playpause

        Returns:
            str: Success or error message.
        """
        if isinstance(key, str):
            key = [key]
        try:
            for k in key:
                # Length validation (most valid key names are short)
                if len(k) > 20:
                    logger.warning(
                        f"Warning: Key name '{k}' is too long "
                        "(max 20 characters)"
                    )

                # Special character validation
                # (key names usually don't contain special characters)
                import re

                if re.search(r'[^\w+\-_]', k) and len(k) > 1:
                    logger.warning(
                        f"Warning: Key '{k}' contains unusual characters"
                    )

            # First, move mouse to a safe position to prevent potential issues
            self.pyautogui.moveTo(
                self.screen_center[0], self.screen_center[1], duration=DURATION
            )

            self.pyautogui.press(key)
            return f"Pressed key: {key}"
        except Exception as e:
            logger.error(f"Error pressing key: {e}")
            return f"Error: Invalid key '{key}' or error pressing it. {e}"

    def hotkey(self, keys: List[str]) -> str:
        r"""Press keys in succession and release in reverse order.

        Args:
            keys (List[str]): The series of keys to press, in order. This can
                be either:
                - Multiple string arguments, e.g., hotkey('ctrl', 'c')
                - A single list of strings, e.g., hotkey(['ctrl', 'c'])

        Returns:
            str: Success or error message.
        """
        try:
            # First, move mouse to a safe position to prevent potential issues
            self.pyautogui.moveTo(
                self.screen_center[0], self.screen_center[1], duration=DURATION
            )

            self.pyautogui.hotkey(*keys)
            return f"Pressed hotkey: {'+'.join(keys)}"
        except Exception as e:
            logger.error(f"Error pressing hotkey: {e}")
            return f"Error: {e}"

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
            FunctionTool(self.get_mouse_position),
            FunctionTool(self.press_key),
            FunctionTool(self.hotkey),
            FunctionTool(self.mouse_drag),
            FunctionTool(self.scroll),
        ]
