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
from unittest.mock import MagicMock, patch

import pytest

# Try importing PyAutoGUIToolkit, skip tests if it or its dependencies fail
# This commonly happens in headless environments where 'DISPLAY' is not set.
try:
    import pyautogui  # noqa: F401

    from camel.toolkits import PyAutoGUIToolkit

    pyautogui_functional = True
except (ImportError, KeyError, RuntimeError):
    pyautogui_functional = False

# Skip all tests in this module if pyautogui isn't functional
pytestmark = pytest.mark.skipif(
    not pyautogui_functional,
    reason="PyAutoGUI is not installed or not functional in this "
    "environment (e.g., headless)",
)


def test_initialization():
    r"""Test proper initialization of PyAutoGUIToolkit."""
    with patch('pyautogui.size', return_value=(1920, 1080)):
        toolkit = PyAutoGUIToolkit(screenshots_dir="test_screenshots")

        # Check if screen dimensions are properly set
        assert toolkit.screen_width == 1920
        assert toolkit.screen_height == 1080

        # Check if safe boundaries are properly calculated
        assert toolkit.safe_margin == 0.1
        assert toolkit.safe_min_x == 192
        assert toolkit.safe_max_x == 1728
        assert toolkit.safe_min_y == 108
        assert toolkit.safe_max_y == 972

        # Check if screen center is properly calculated
        assert toolkit.screen_center == (960, 540)

        # Check if screenshots directory is properly set
        assert toolkit.screenshots_dir == os.path.expanduser(
            "test_screenshots"
        )


def test_get_safe_coordinates():
    r"""Test that coordinates are properly adjusted to stay within safe
    boundaries.
    """
    with patch('pyautogui.size', return_value=(1000, 800)):
        toolkit = PyAutoGUIToolkit()

        # Test coordinates within safe boundaries
        safe_x, safe_y = toolkit._get_safe_coordinates(500, 400)
        assert safe_x == 500
        assert safe_y == 400

        # Test coordinates outside safe boundaries (too small)
        safe_x, safe_y = toolkit._get_safe_coordinates(50, 40)
        assert safe_x == 100  # Adjusted to safe_min_x
        assert safe_y == 80  # Adjusted to safe_min_y

        # Test coordinates outside safe boundaries (too large)
        safe_x, safe_y = toolkit._get_safe_coordinates(950, 760)
        assert safe_x == 900  # Adjusted to safe_max_x
        assert safe_y == 720  # Adjusted to safe_max_y


def test_mouse_move():
    r"""Test mouse movement functionality."""
    with patch('pyautogui.size', return_value=(1000, 800)):
        with patch('pyautogui.moveTo') as mock_move:
            toolkit = PyAutoGUIToolkit()

            # Test movement with coordinates adjustment
            mock_move.reset_mock()
            result = toolkit.mouse_move(50, 40)
            mock_move.assert_called_once_with(100, 80, duration=0.1)
            assert "Mouse moved to position (100, 80)" in result


def test_mouse_click():
    r"""Test mouse click functionality."""
    with patch('pyautogui.size', return_value=(1000, 800)):
        with patch('pyautogui.click') as mock_click:
            toolkit = PyAutoGUIToolkit()

            # Test click with coordinates adjustment
            mock_click.reset_mock()
            result = toolkit.mouse_click(button="right", clicks=2, x=50, y=40)
            mock_click.assert_called_once_with(
                x=100, y=80, button="right", clicks=2
            )
            assert (
                "Clicked right button 2 time(s) at position (100, 80)"
                in result
            )

            # Test click at current position
            mock_click.reset_mock()
            result = toolkit.mouse_click(button="middle")
            mock_click.assert_called_once_with(button="middle", clicks=1)
            assert (
                "Clicked middle button 1 time(s) at current position" in result
            )


def test_get_mouse_position():
    r"""Test getting mouse position functionality."""
    with patch('pyautogui.size', return_value=(1000, 800)):
        with patch(
            'pyautogui.position', return_value=(500, 400)
        ) as mock_position:
            toolkit = PyAutoGUIToolkit()

            # Test normal operation
            result = toolkit.get_mouse_position()
            mock_position.assert_called_once()
            assert "Mouse position: (500, 400)" in result


def test_take_screenshot():
    r"""Test taking screenshot functionality."""
    with patch('pyautogui.size', return_value=(1000, 800)):
        with patch('os.makedirs') as mock_makedirs:
            with patch('pyautogui.screenshot') as mock_screenshot:
                with patch('time.time', return_value=1234567890):
                    toolkit = PyAutoGUIToolkit(
                        screenshots_dir="test_screenshots"
                    )

                    # Set up mock screenshot
                    mock_screenshot_obj = MagicMock()
                    mock_screenshot.return_value = mock_screenshot_obj

                    # Test normal operation
                    result = toolkit.take_screenshot()

                    # Verify directory creation
                    mock_makedirs.assert_called_once_with(
                        "test_screenshots", exist_ok=True
                    )

                    # Verify screenshot was taken
                    mock_screenshot.assert_called_once()

                    # Verify screenshot was saved
                    mock_screenshot_obj.save.assert_called_once()
                    args = mock_screenshot_obj.save.call_args[0]
                    assert (
                        "test_screenshots/screenshot_1234567890.png" in args[0]
                    )

                    # Verify result message
                    assert "Screenshot saved to" in result


def test_mouse_drag():
    r"""Test mouse drag functionality."""
    with patch('pyautogui.size', return_value=(1000, 800)):
        with patch('pyautogui.moveTo') as mock_move:
            with patch('pyautogui.dragTo') as mock_drag:
                toolkit = PyAutoGUIToolkit()

                # Test normal drag operation
                result = toolkit.mouse_drag(200, 200, 600, 600, button="left")

                # Verify drag operation
                mock_drag.assert_called_once_with(
                    600, 600, duration=0.1, button="left"
                )

                # Verify move to center after drag
                mock_move.assert_any_call(500, 400, duration=0.1)

                # Verify result message
                assert "Dragged from (200, 200) to (600, 600)" in result

                # Test drag with coordinate adjustment
                mock_move.reset_mock()
                mock_drag.reset_mock()

                result = toolkit.mouse_drag(50, 50, 950, 750)

                # Verify coordinates were adjusted to safe boundaries
                mock_move.assert_any_call(100, 80, duration=0.1)
                mock_drag.assert_called_once_with(
                    900, 720, duration=0.1, button="left"
                )

                # Verify result message with adjusted coordinates
                assert "Dragged from (100, 80) to (900, 720)" in result

                # Verify recovery attempt
                mock_move.assert_any_call(500, 400, duration=0.1)


def test_scroll():
    r"""Test scroll functionality."""
    with patch('pyautogui.size', return_value=(1000, 800)):
        with patch(
            'pyautogui.position', return_value=(500, 400)
        ) as mock_position:
            with patch('pyautogui.scroll') as mock_scroll:
                with patch('pyautogui.moveTo') as mock_move:
                    toolkit = PyAutoGUIToolkit()

                    # Test scroll with coordinates
                    result = toolkit.scroll(10, x=300, y=300)

                    # Verify scroll operation
                    mock_scroll.assert_called_once_with(10, x=300, y=300)

                    # Verify move to center after scroll
                    mock_move.assert_called_once_with(500, 400)

                    # Verify result message
                    assert "Scrolled 10 clicks at position 300, 300" in result

                    # Test scroll at current position
                    mock_position.reset_mock()
                    mock_scroll.reset_mock()
                    mock_move.reset_mock()

                    result = toolkit.scroll(-5)

                    # Verify position was checked
                    mock_position.assert_called_once()

                    # Verify scroll operation at current position
                    mock_scroll.assert_called_once_with(-5, x=500, y=400)

                    # Verify result message
                    assert "Scrolled -5 clicks at position 500, 400" in result


def test_keyboard_type():
    r"""Test keyboard typing functionality."""
    with patch('pyautogui.size', return_value=(1000, 800)):
        with patch('pyautogui.moveTo') as mock_move:
            with patch('pyautogui.write') as mock_write:
                toolkit = PyAutoGUIToolkit()

                # Test normal typing
                result = toolkit.keyboard_type("Hello, world!", interval=0.1)

                # Verify move to center before typing
                mock_move.assert_called_once_with(500, 400, duration=0.1)

                # Verify typing operation
                mock_write.assert_called_once_with(
                    "Hello, world!", interval=0.1
                )

                # Verify result message
                assert "Typed text: Hello, world!" in result

                # Test empty text
                mock_move.reset_mock()
                mock_write.reset_mock()

                result = toolkit.keyboard_type("")

                # Verify no typing operation for empty text
                mock_write.assert_not_called()

                # Verify error message
                assert "Error: Empty text provided" in result

                # Test very long text
                mock_move.reset_mock()
                mock_write.reset_mock()

                long_text = "a" * 1001
                result = toolkit.keyboard_type(long_text)

                # Verify typing operation still performed
                mock_write.assert_called_once_with(long_text, interval=0.0)

                # Verify result message truncated
                assert "Typed text: " + "a" * 20 + "..." in result


def test_press_key():
    r"""Test key press functionality."""
    with patch('pyautogui.size', return_value=(1000, 800)):
        with patch('pyautogui.moveTo') as mock_move:
            with patch('pyautogui.press') as mock_press:
                toolkit = PyAutoGUIToolkit()

                # Test single key press
                result = toolkit.press_key("enter")

                # Verify move to center before key press
                mock_move.assert_called_once_with(500, 400, duration=0.1)

                # Verify key press operation
                mock_press.assert_called_once_with(["enter"])

                # Verify result message
                assert "Pressed key: ['enter']" in result

                # Test multiple key press
                mock_move.reset_mock()
                mock_press.reset_mock()

                result = toolkit.press_key(["tab", "enter"])

                # Verify key press operation
                mock_press.assert_called_once_with(["tab", "enter"])

                # Verify result message
                assert "Pressed key: ['tab', 'enter']" in result


def test_hotkey():
    r"""Test hotkey functionality."""
    with patch('pyautogui.size', return_value=(1000, 800)):
        with patch('pyautogui.moveTo') as mock_move:
            with patch('pyautogui.hotkey') as mock_hotkey:
                toolkit = PyAutoGUIToolkit()

                # Test hotkey with multiple arguments
                result = toolkit.hotkey(["ctrl", "c"])

                # Verify move to center before hotkey
                mock_move.assert_called_once_with(500, 400, duration=0.1)

                # Verify hotkey operation
                mock_hotkey.assert_called_once_with("ctrl", "c")

                # Verify result message
                assert "Pressed hotkey: ctrl+c" in result

                # Test hotkey with list argument
                mock_move.reset_mock()
                mock_hotkey.reset_mock()

                result = toolkit.hotkey(["ctrl", "alt", "del"])

                # Verify hotkey operation
                mock_hotkey.assert_called_once_with("ctrl", "alt", "del")

                # Verify result message
                assert "Pressed hotkey: ctrl+alt+del" in result
