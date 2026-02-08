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

import os
import shlex
import subprocess
from typing import List, Optional

from camel.logger import get_logger
from camel.toolkits import BaseToolkit, FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class AndroidToolkit(BaseToolkit):
    r"""A toolkit for interacting with Android devices via ADB.

    Provides tools for app management, input simulation, screenshot
    capture, UI hierarchy inspection, and device control through the
    Android Debug Bridge (ADB).

    Attributes:
        adb_path (str): Path to the ADB executable.
        device_serial (Optional[str]): Serial number of the target device.
        command_timeout (int): Default timeout for ADB commands.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        adb_path: str = "adb",
        device_serial: Optional[str] = None,
        command_timeout: int = 30,
        screenshots_dir: str = "screenshots",
    ):
        r"""Initializes the AndroidToolkit.

        Args:
            timeout (Optional[float]): Timeout for API requests in seconds.
                (default: :obj:`None`)
            adb_path (str): Path to the ADB executable.
                (default: :obj:`"adb"`)
            device_serial (Optional[str]): Serial number of the target
                Android device. If None, ADB uses the default connected
                device. (default: :obj:`None`)
            command_timeout (int): Default timeout in seconds for ADB
                commands. (default: :obj:`30`)
            screenshots_dir (str): Directory to save screenshots.
                (default: :obj:`"screenshots"`)
        """
        super().__init__(timeout=timeout)
        self.adb_path = adb_path
        self.device_serial = device_serial
        self.command_timeout = command_timeout
        self.screenshots_dir = os.path.expanduser(screenshots_dir)

    def _build_adb_command(self, args: List[str]) -> List[str]:
        r"""Builds an ADB command with optional device serial.

        Args:
            args (List[str]): ADB sub-command arguments.

        Returns:
            List[str]: Full ADB command as a list of strings.
        """
        cmd = [self.adb_path]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        return cmd

    def _run_adb(
        self,
        args: List[str],
        timeout: Optional[int] = None,
    ) -> str:
        r"""Runs an ADB command and returns its output.

        Args:
            args (List[str]): ADB sub-command arguments.
            timeout (Optional[int]): Timeout for the command in seconds.
                If None, uses the default command_timeout.
                (default: :obj:`None`)

        Returns:
            str: The stdout output if successful, or an error message.
        """
        effective_timeout = timeout or self.command_timeout
        cmd = self._build_adb_command(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
            if result.returncode != 0:
                error_msg = (
                    result.stderr.strip()
                    or f"ADB command failed with return code "
                    f"{result.returncode}"
                )
                logger.warning(
                    f"ADB command {cmd} returned non-zero exit code "
                    f"{result.returncode}: {error_msg}"
                )
                return f"Error (exit code {result.returncode}): {error_msg}"
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(
                f"ADB command {cmd} timed out after {effective_timeout}s"
            )
            return (
                f"Error: ADB command timed out after "
                f"{effective_timeout} seconds"
            )
        except FileNotFoundError:
            logger.error(f"ADB executable not found: {self.adb_path}")
            return (
                f"Error: ADB executable not found at '{self.adb_path}'. "
                f"Please install the Android SDK Platform Tools."
            )
        except Exception as e:
            logger.error(f"Error executing ADB command: {e}")
            return f"Error: {e}"

    def execute_adb_command(self, command: str) -> str:
        r"""Executes a raw ADB command.

        Args:
            command (str): The ADB sub-command to execute
                (e.g., "devices", "shell ls").

        Returns:
            str: The command output or an error message.
        """
        try:
            args = shlex.split(command)
        except ValueError as e:
            return f"Error: Invalid command syntax: {e}"

        if not args:
            return "Error: Empty command"

        return self._run_adb(args)

    def get_device_info(self) -> str:
        r"""Retrieves information about the connected Android device.

        Returns:
            str: Formatted device information including model, Android
                version, SDK version, and screen resolution.
        """
        info_parts = []

        model = self._run_adb(
            ["shell", "getprop", "ro.product.model"]
        )
        info_parts.append(f"Model: {model}")

        android_version = self._run_adb(
            ["shell", "getprop", "ro.build.version.release"]
        )
        info_parts.append(f"Android Version: {android_version}")

        sdk_version = self._run_adb(
            ["shell", "getprop", "ro.build.version.sdk"]
        )
        info_parts.append(f"SDK Version: {sdk_version}")

        resolution = self._run_adb(["shell", "wm", "size"])
        info_parts.append(f"Screen: {resolution}")

        return "\n".join(info_parts)

    def install_app(self, apk_path: str) -> str:
        r"""Installs an APK on the Android device.

        Args:
            apk_path (str): Path to the APK file on the host machine.

        Returns:
            str: Installation result or an error message.
        """
        if not os.path.isfile(apk_path):
            return f"Error: APK file not found: {apk_path}"
        return self._run_adb(["install", "-r", apk_path], timeout=120)

    def uninstall_app(self, package_name: str) -> str:
        r"""Uninstalls an app from the Android device.

        Args:
            package_name (str): The package name to uninstall
                (e.g., "com.example.app").

        Returns:
            str: Uninstall result or an error message.
        """
        return self._run_adb(["uninstall", package_name])

    def list_installed_apps(self) -> str:
        r"""Lists all installed packages on the device.

        Returns:
            str: Newline-separated list of installed package names.
        """
        return self._run_adb(["shell", "pm", "list", "packages"])

    def launch_app(self, package_name: str, activity: str = "") -> str:
        r"""Launches an app on the Android device.

        Args:
            package_name (str): The package name of the app
                (e.g., "com.android.settings").
            activity (str): The activity to launch. If empty, launches
                the default (main) activity. (default: :obj:`""`)

        Returns:
            str: Launch result or an error message.
        """
        if activity:
            component = f"{package_name}/{activity}"
            return self._run_adb(
                ["shell", "am", "start", "-n", component]
            )
        return self._run_adb(
            [
                "shell",
                "monkey",
                "-p",
                package_name,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ]
        )

    def tap(self, x: int, y: int) -> str:
        r"""Simulates a tap at the given screen coordinates.

        Args:
            x (int): X-coordinate of the tap.
            y (int): Y-coordinate of the tap.

        Returns:
            str: Success message or an error message.
        """
        result = self._run_adb(
            ["shell", "input", "tap", str(x), str(y)]
        )
        if result.startswith("Error"):
            return result
        return f"Tapped at ({x}, {y})"

    def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 300,
    ) -> str:
        r"""Simulates a swipe gesture on the screen.

        Args:
            start_x (int): Starting X-coordinate.
            start_y (int): Starting Y-coordinate.
            end_x (int): Ending X-coordinate.
            end_y (int): Ending Y-coordinate.
            duration_ms (int): Duration of the swipe in milliseconds.
                (default: :obj:`300`)

        Returns:
            str: Success message or an error message.
        """
        result = self._run_adb(
            [
                "shell",
                "input",
                "swipe",
                str(start_x),
                str(start_y),
                str(end_x),
                str(end_y),
                str(duration_ms),
            ]
        )
        if result.startswith("Error"):
            return result
        return (
            f"Swiped from ({start_x}, {start_y}) to "
            f"({end_x}, {end_y}) over {duration_ms}ms"
        )

    def long_press(self, x: int, y: int, duration_ms: int = 1000) -> str:
        r"""Simulates a long press at the given screen coordinates.

        Args:
            x (int): X-coordinate of the press.
            y (int): Y-coordinate of the press.
            duration_ms (int): Duration of the press in milliseconds.
                (default: :obj:`1000`)

        Returns:
            str: Success message or an error message.
        """
        result = self._run_adb(
            [
                "shell",
                "input",
                "swipe",
                str(x),
                str(y),
                str(x),
                str(y),
                str(duration_ms),
            ]
        )
        if result.startswith("Error"):
            return result
        return f"Long pressed at ({x}, {y}) for {duration_ms}ms"

    def input_text(self, text: str) -> str:
        r"""Types text on the Android device.

        Args:
            text (str): The text to type. Spaces are replaced with
                ``%s`` for ADB compatibility.

        Returns:
            str: Success message or an error message.
        """
        if not text:
            return "Error: Empty text provided"
        # ADB input text requires spaces to be escaped
        escaped_text = text.replace(" ", "%s")
        result = self._run_adb(
            ["shell", "input", "text", escaped_text]
        )
        if result.startswith("Error"):
            return result
        return (
            f"Typed text: {text[:20]}{'...' if len(text) > 20 else ''}"
        )

    def press_key(self, keycode: str) -> str:
        r"""Sends a key event to the Android device.

        Args:
            keycode (str): Android keycode name or number
                (e.g., "KEYCODE_HOME", "3", "KEYCODE_BACK").

        Returns:
            str: Success message or an error message.
        """
        result = self._run_adb(
            ["shell", "input", "keyevent", keycode]
        )
        if result.startswith("Error"):
            return result
        return f"Pressed key: {keycode}"

    def take_screenshot(self, filename: str = "screenshot.png") -> str:
        r"""Takes a screenshot of the device screen and pulls it to the
        host machine.

        Args:
            filename (str): Name of the screenshot file.
                (default: :obj:`"screenshot.png"`)

        Returns:
            str: Path to the saved screenshot or an error message.
        """
        os.makedirs(self.screenshots_dir, exist_ok=True)
        device_path = f"/sdcard/{filename}"
        local_path = os.path.join(self.screenshots_dir, filename)

        # Capture screenshot on device
        cap_result = self._run_adb(
            ["shell", "screencap", "-p", device_path]
        )
        if cap_result.startswith("Error"):
            return cap_result

        # Pull to host
        pull_result = self._run_adb(["pull", device_path, local_path])
        if pull_result.startswith("Error"):
            return pull_result

        # Clean up on device
        self._run_adb(["shell", "rm", device_path])

        return f"Screenshot saved to {local_path}"

    def get_ui_hierarchy(self) -> str:
        r"""Dumps the current UI hierarchy as XML.

        Uses ``uiautomator dump`` to capture the view hierarchy of the
        current screen, which can be used for element identification
        and interaction.

        Returns:
            str: XML representation of the UI hierarchy or an error
                message.
        """
        device_path = "/sdcard/ui_dump.xml"

        # Dump UI hierarchy
        dump_result = self._run_adb(
            ["shell", "uiautomator", "dump", device_path]
        )
        if dump_result.startswith("Error"):
            return dump_result

        # Read the dump
        content = self._run_adb(["shell", "cat", device_path])

        # Clean up
        self._run_adb(["shell", "rm", device_path])

        return content

    def get_current_activity(self) -> str:
        r"""Gets the currently focused activity on the device.

        Returns:
            str: Information about the current activity or an error message.
        """
        return self._run_adb(
            [
                "shell",
                "dumpsys",
                "activity",
                "activities",
            ]
        )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects for Android operations.

        Returns:
            List[FunctionTool]: List of Android device tool functions.
        """
        return [
            FunctionTool(self.execute_adb_command),
            FunctionTool(self.get_device_info),
            FunctionTool(self.install_app),
            FunctionTool(self.uninstall_app),
            FunctionTool(self.list_installed_apps),
            FunctionTool(self.launch_app),
            FunctionTool(self.tap),
            FunctionTool(self.swipe),
            FunctionTool(self.long_press),
            FunctionTool(self.input_text),
            FunctionTool(self.press_key),
            FunctionTool(self.take_screenshot),
            FunctionTool(self.get_ui_hierarchy),
            FunctionTool(self.get_current_activity),
        ]
