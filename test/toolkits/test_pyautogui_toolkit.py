# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import pytest
from unittest.mock import MagicMock, patch
import warnings
# Import pyautogui for patch
from camel.toolkits import PyAutoGUIToolkit
from camel.toolkits.base import FunctionTool

@pytest.fixture(autouse=True)
def ignore_all_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield

def test_init():
    """Test initialization of PyAutoGUIToolkit."""
    pyautogui_mock = MagicMock()
    pyautogui_mock.size.return_value = (1920, 1080)
    pyautogui_mock.FAILSAFE = True
    
    with patch.dict('sys.modules', {'pyautogui': pyautogui_mock}):
        toolkit = PyAutoGUIToolkit()
    
        # Verify __init__ used the mock correctly
        pyautogui_mock.size.assert_called_once()
        assert toolkit.screen_width == 1920
        assert toolkit.screen_height == 1080
        assert toolkit.screen_center == (960, 540)
        assert toolkit.safe_margin == 0.1
        
@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
def test_mouse_move(mock_pyautogui):
    """Test mouse_move method by patching the global pyautogui namespace"""
    # Configure mock object
    mock_pyautogui.size.return_value = (1920, 1080)
    
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Call the method to be tested
    result = toolkit.mouse_move(500, 500, duration=0.5)
    
    # Verify the mock works as expected
    mock_pyautogui.moveTo.assert_called_once_with(500, 500, duration=0.5)
    assert "Mouse moved to position (500, 500)" in result

@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
def test_mouse_click(mock_pyautogui):
    """Test mouse_click method by patching the global pyautogui namespace"""
    # Configure mock object
    mock_pyautogui.size.return_value = (1920, 1080)
    mock_pyautogui.position.return_value = (100, 100)  # Used for click test without coordinates
    
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Test click with coordinates
    result = toolkit.mouse_click(button='left', clicks=2, x=500, y=500)
    
    # Verify the call is correct
    mock_pyautogui.click.assert_called_once_with(
        x=500, y=500, button='left', clicks=2
    )
    assert "Clicked left button 2 time(s)" in result
    
    # Reset mock object and test click without coordinates
    mock_pyautogui.click.reset_mock()
    result = toolkit.mouse_click()
    
    # Verify the call is correct, using default values
    mock_pyautogui.click.assert_called_once_with(button='left', clicks=1)
    assert "Clicked left button 1 time(s)" in result


@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
def test_keyboard_type(mock_pyautogui):
    """Test keyboard_type method by patching the pyautogui namespace"""
    # Configure mock object
    mock_pyautogui.size.return_value = (1920, 1080)
    
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Test keyboard input
    result = toolkit.keyboard_type("Hello, World!")
    
    # Verify the call is correct (need to include interval=0.0 default parameter)
    mock_pyautogui.write.assert_called_once_with(
        "Hello, World!", interval=0.0
    )
    assert "Typed text: Hello, World!" in result
    
    # Test keyboard input with interval
    mock_pyautogui.write.reset_mock()
    result = toolkit.keyboard_type("Hello, World!", interval=0.1)
    
    # Verify the call is correct
    mock_pyautogui.write.assert_called_once_with("Hello, World!", interval=0.1)
    assert "Typed text: Hello, World!" in result

def test_get_tools():
    """Test that get_tools returns all expected toolkit methods"""
    with patch("pyautogui.size", return_value=(1920, 1080)):
        # Create toolkit instance
        toolkit = PyAutoGUIToolkit()
        
        # Get tools
        tools = toolkit.get_tools()
        
        # Verify tools are returned
        assert tools
        assert all(isinstance(tool, FunctionTool) for tool in tools)
        
        # Get actual tool names
        tool_names = [
            tool.func.__name__ for tool in tools if hasattr(tool, 'func')
        ]
        
        # The actual methods registered in get_tools() based on code review
        expected_methods = [
            'mouse_move', 
            'mouse_drag',
            'mouse_click', 
            'keyboard_type', 
            'take_screenshot',  # Note: this is 'take_screenshot', not 'screenshot'
            'get_screen_size',
            'get_mouse_position',
            'double_click',
            'right_click',
            'middle_click',
            'scroll',
            'press_key',
            'hotkey'
        ]
        
        # Verify all expected methods are in the tools
        for method in expected_methods:
            assert method in tool_names, (
                f"Expected method '{method}' not found in tools"
            )
            
        # Verify tool count matches expected
        assert len(tool_names) == len(expected_methods), (
            f"Expected {len(expected_methods)} tools, but got {len(tool_names)}"
        )

@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
@patch("camel.toolkits.pyautogui_toolkit.os")
@patch("camel.toolkits.pyautogui_toolkit.time")
def test_take_screenshot(mock_time, mock_os, mock_pyautogui):
    """Test take_screenshot method by patching the global pyautogui namespace"""
    # Configure mocks
    mock_pyautogui.size.return_value = (1920, 1080)
    mock_time.time.return_value = 12345
    mock_os.path.expanduser.return_value = "/mock/home/camel_screenshots"
    mock_os.path.join.return_value = (
        "/mock/home/camel_screenshots/screenshot_12345.png"
    )
    
    # Create a mock PIL Image
    mock_image = MagicMock()
    mock_pyautogui.screenshot.return_value = mock_image
    
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Test with default parameters (full screen)
    result = toolkit.take_screenshot()
    
    # Verify the directory was created
    mock_os.makedirs.assert_called_once_with(
        "/mock/home/camel_screenshots", exist_ok=True
    )
    
    # Verify screenshot was called once with a region parameter
    mock_pyautogui.screenshot.assert_called_once()
    
    # Verify the image was saved
    mock_image.save.assert_called_once_with(
        "/mock/home/camel_screenshots/screenshot_12345.png"
    )
    
    # Verify the success message
    assert (
        "Screenshot saved to /mock/home/camel_screenshots/screenshot_12345.png"
        in result
    )

    # Reset mocks for second test
    mock_pyautogui.screenshot.reset_mock()
    mock_image.save.reset_mock()
    
    # Test with custom region
    result = toolkit.take_screenshot(left=100, top=100, width=500, height=500)
    
    # Verify screenshot was called once
    mock_pyautogui.screenshot.assert_called_once()
    # Verify region parameter was included in the call
    assert 'region' in mock_pyautogui.screenshot.call_args[1]
    # Get the actual region that was passed
    region = mock_pyautogui.screenshot.call_args[1]['region']
    # Verify that the region coordinates are of the correct type
    assert isinstance(region, tuple)
    assert len(region) == 4
    assert all(isinstance(val, int) for val in region)
    
    # Verify the image was saved
    mock_image.save.assert_called_once_with(
        "/mock/home/camel_screenshots/screenshot_12345.png"
    )

@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
def test_get_screen_size(mock_pyautogui):
    """Test get_screen_size method by patching the global pyautogui namespace"""
    # Configure mock
    mock_pyautogui.size.return_value = (1920, 1080)
    
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Test get_screen_size
    result = toolkit.get_screen_size()
    
    # Verify the function returns the correct values
    assert result == "Screen size: 1920x1080"
    mock_pyautogui.size.assert_called_once()


@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
def test_get_mouse_position(mock_pyautogui):
    """Test get_mouse_position method by patching the global pyautogui namespace"""
    # Configure mock
    mock_pyautogui.position.return_value = (500, 300)
    
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Test get_mouse_position
    result = toolkit.get_mouse_position()
    
    # Verify the function returns the correct values
    assert result == "Mouse position: (500, 300)"
    mock_pyautogui.position.assert_called_once()


@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
def test_press_key(mock_pyautogui):
    """Test press_key method by patching the global pyautogui namespace"""
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Test press_key
    result = toolkit.press_key("enter")
    
    # Verify the call is correct
    mock_pyautogui.press.assert_called_once_with("enter")
    assert "Pressed key: enter" in result


@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
def test_hotkey(mock_pyautogui):
    """Test hotkey method by patching the global pyautogui namespace"""
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Test hotkey with multiple keys
    result = toolkit.hotkey("ctrl", "c")
    
    # Verify the call is correct
    mock_pyautogui.hotkey.assert_called_once_with("ctrl", "c")
    assert "Pressed hotkey: ctrl+c" in result


@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
def test_mouse_drag(mock_pyautogui):
    """Test mouse_drag method by patching the global pyautogui namespace"""
    # Configure mock
    mock_pyautogui.size.return_value = (1920, 1080)
    
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Test mouse_drag
    result = toolkit.mouse_drag(200, 200, 400, 400, duration=0.5)
    
    # Verify the call is correct - duration is divided by 3 in the implementation
    mock_pyautogui.dragTo.assert_called_once_with(
        400, 400, duration=0.5/3, button='left'
    )
    assert "Dragged from" in result


@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
def test_scroll(mock_pyautogui):
    """Test scroll method by patching the global pyautogui namespace"""
    # Configure mock for position() call
    mock_pyautogui.position.return_value = (500, 500)
    
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Test scroll
    result = toolkit.scroll(5)
    
    # Verify the call is correct (should include x and y parameters)
    # The toolkit applies safety boundaries, so we can't know the exact values
    assert mock_pyautogui.scroll.call_count == 1
    call_args = mock_pyautogui.scroll.call_args[0]
    call_kwargs = mock_pyautogui.scroll.call_args[1]
    
    # Check first positional argument is 5
    assert call_args[0] == 5
    # Check x and y parameters are present
    assert 'x' in call_kwargs
    assert 'y' in call_kwargs
    
    assert "Scrolled 5 click" in result


@patch("camel.toolkits.pyautogui_toolkit.subprocess")
@patch("camel.toolkits.pyautogui_toolkit.pyautogui", create=True)
def test_open_terminal(mock_pyautogui, mock_subprocess):
    """Test open_terminal method by patching the global pyautogui namespace"""
    # Configure mock
    mock_pyautogui.size.return_value = (1920, 1080)
    
    # Initialize toolkit
    toolkit = PyAutoGUIToolkit()
    
    # Test open_terminal
    result = toolkit.open_terminal(wait_time=0)  # Use 0 to speed up test
    
    # Verify the correct command was called based on platform
    import platform
    if platform.system() == "Darwin":  # macOS
        mock_subprocess.Popen.assert_called_once_with(
            ["open", "-a", "Terminal"]
        )
    elif platform.system() == "Windows":
        mock_subprocess.Popen.assert_called_once_with("cmd.exe")
    
    assert "Terminal opened" in result