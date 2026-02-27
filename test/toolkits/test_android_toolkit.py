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

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits.android_toolkit import AndroidToolkit


@pytest.fixture
def toolkit(tmp_path):
    return AndroidToolkit(screenshots_dir=str(tmp_path / "screenshots"))


def test_initialization_defaults():
    toolkit = AndroidToolkit()
    assert toolkit.adb_path == "adb"
    assert toolkit.device_serial is None
    assert toolkit.command_timeout == 30


def test_initialization_custom():
    toolkit = AndroidToolkit(
        adb_path="/usr/local/bin/adb",
        device_serial="emulator-5554",
        command_timeout=60,
        timeout=10.0,
    )
    assert toolkit.adb_path == "/usr/local/bin/adb"
    assert toolkit.device_serial == "emulator-5554"
    assert toolkit.command_timeout == 60


def test_build_adb_command_no_serial(toolkit):
    cmd = toolkit._build_adb_command(["devices"])
    assert cmd == ["adb", "devices"]


def test_build_adb_command_with_serial():
    toolkit = AndroidToolkit(device_serial="emulator-5554")
    cmd = toolkit._build_adb_command(["shell", "ls"])
    assert cmd == ["adb", "-s", "emulator-5554", "shell", "ls"]


def test_get_tools(toolkit):
    tools = toolkit.get_tools()
    assert len(tools) == 14
    tool_names = [t.get_function_name() for t in tools]
    assert "execute_adb_command" in tool_names
    assert "get_device_info" in tool_names
    assert "install_app" in tool_names
    assert "uninstall_app" in tool_names
    assert "list_installed_apps" in tool_names
    assert "launch_app" in tool_names
    assert "tap" in tool_names
    assert "swipe" in tool_names
    assert "long_press" in tool_names
    assert "input_text" in tool_names
    assert "press_key" in tool_names
    assert "take_screenshot" in tool_names
    assert "get_ui_hierarchy" in tool_names
    assert "get_current_activity" in tool_names


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_execute_adb_command(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="List of devices attached\nemulator-5554\tdevice",
        stderr="",
    )
    result = toolkit.execute_adb_command("devices")
    assert "emulator-5554" in result


def test_execute_adb_command_empty(toolkit):
    result = toolkit.execute_adb_command("")
    assert "Error" in result


def test_execute_adb_command_invalid_syntax(toolkit):
    result = toolkit.execute_adb_command("shell 'unterminated")
    assert "Error" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_execute_adb_command_timeout(mock_run, toolkit):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=30)
    result = toolkit.execute_adb_command("shell sleep 999")
    assert "timed out" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_execute_adb_not_found(mock_run, toolkit):
    mock_run.side_effect = FileNotFoundError()
    result = toolkit.execute_adb_command("devices")
    assert "not found" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_get_device_info(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="Pixel 6", stderr=""
    )
    result = toolkit.get_device_info()
    assert "Model:" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_install_app_file_not_found(mock_run, toolkit):
    result = toolkit.install_app("/nonexistent/path/app.apk")
    assert "Error" in result
    assert "not found" in result
    mock_run.assert_not_called()


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_install_app_success(mock_run, toolkit, tmp_path):
    apk_file = tmp_path / "test.apk"
    apk_file.touch()
    mock_run.return_value = MagicMock(
        returncode=0, stdout="Success", stderr=""
    )
    result = toolkit.install_app(str(apk_file))
    assert "Success" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_uninstall_app(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="Success", stderr=""
    )
    result = toolkit.uninstall_app("com.example.app")
    assert "Success" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_list_installed_apps(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="package:com.android.settings\npackage:com.android.browser",
        stderr="",
    )
    result = toolkit.list_installed_apps()
    assert "com.android.settings" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_launch_app_default_activity(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="Events injected: 1", stderr=""
    )
    result = toolkit.launch_app("com.android.settings")
    assert "Events injected" in result
    call_args = mock_run.call_args[0][0]
    assert "monkey" in call_args


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_launch_app_specific_activity(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="Starting: Intent", stderr=""
    )
    toolkit.launch_app(
        "com.android.settings", ".Settings"
    )
    call_args = mock_run.call_args[0][0]
    assert "am" in call_args
    assert "start" in call_args


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_tap(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr=""
    )
    result = toolkit.tap(100, 200)
    assert "Tapped at (100, 200)" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_swipe(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr=""
    )
    result = toolkit.swipe(100, 200, 300, 400, 500)
    assert "Swiped from (100, 200) to (300, 400)" in result
    assert "500ms" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_long_press(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr=""
    )
    result = toolkit.long_press(100, 200, 2000)
    assert "Long pressed at (100, 200)" in result
    assert "2000ms" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_input_text(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr=""
    )
    result = toolkit.input_text("hello world")
    assert "Typed text:" in result


def test_input_text_empty(toolkit):
    result = toolkit.input_text("")
    assert "Error" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_press_key(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr=""
    )
    result = toolkit.press_key("KEYCODE_HOME")
    assert "Pressed key: KEYCODE_HOME" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_take_screenshot(mock_run, toolkit, tmp_path):
    mock_run.return_value = MagicMock(
        returncode=0, stdout="", stderr=""
    )
    result = toolkit.take_screenshot("test_shot.png")
    assert "Screenshot saved to" in result
    assert "test_shot.png" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_take_screenshot_capture_error(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=1, stdout="", stderr="screencap failed"
    )
    result = toolkit.take_screenshot()
    assert "Error" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_get_ui_hierarchy(mock_run, toolkit):
    mock_run.side_effect = [
        MagicMock(
            returncode=0,
            stdout="UI hierarchy dumped",
            stderr="",
        ),
        MagicMock(
            returncode=0,
            stdout='<hierarchy rotation="0"><node text="Home"/></hierarchy>',
            stderr="",
        ),
        MagicMock(returncode=0, stdout="", stderr=""),
    ]
    result = toolkit.get_ui_hierarchy()
    assert "hierarchy" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_get_current_activity(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="TASK com.android.launcher3 id=1",
        stderr="",
    )
    result = toolkit.get_current_activity()
    assert "com.android.launcher3" in result


@patch("camel.toolkits.android_toolkit.subprocess.run")
def test_adb_nonzero_exit(mock_run, toolkit):
    mock_run.return_value = MagicMock(
        returncode=1, stdout="", stderr="device not found"
    )
    result = toolkit.execute_adb_command("shell ls")
    assert "Error" in result
    assert "device not found" in result
