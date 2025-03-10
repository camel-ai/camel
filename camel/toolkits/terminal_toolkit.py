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
import platform
import subprocess
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

logger = get_logger(__name__)


class TerminalToolkit(BaseToolkit):
    r"""A toolkit for terminal operations across multiple operating systems.

    This toolkit provides a set of functions for terminal operations such as
    searching for files by name or content, executing shell commands, and
    managing terminal sessions.

    Note:
        Most functions are compatible with Unix-based systems (macOS, Linux).
        For Windows compatibility, additional implementation details are
        needed.

    Args:
        timeout (Optional[float]): The timeout for terminal operations.
        shell_sessions (Optional[Dict[str, Any]]): A dictionary to store
            shell session information. If None, an empty dictionary will be
            used.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        shell_sessions: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(timeout=timeout)
        self.shell_sessions = shell_sessions or {}
        self.os_type = (
            platform.system()
        )  # 'Windows', 'Darwin' (macOS), 'Linux'

    def file_find_in_content(
        self, file: str, regex: str, sudo: bool = False
    ) -> str:
        r"""Search for matching text within file content.

        Args:
            file (str): Absolute path of the file to search within.
            regex (str): Regular expression pattern to match.
            sudo (bool, optional): Whether to use sudo privileges. Defaults to
                False. Note: Using sudo requires the process to have
                appropriate permissions.

        Returns:
            str: Matching content found in the file.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            PermissionError: If there are insufficient permissions to read the
                file.
        """
        if not os.path.exists(file):
            raise FileNotFoundError(f"File not found: {file}")

        if not os.path.isfile(file):
            raise ValueError(f"The path provided is not a file: {file}")

        command = []
        if sudo:
            command.extend(["sudo"])

        if self.os_type in ['Darwin', 'Linux']:  # macOS or Linux
            command.extend(["grep", "-E", regex, file])
        else:  # Windows
            # For Windows, we could use PowerShell or findstr
            command.extend(["findstr", "/R", regex, file])

        try:
            result = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            return result.stdout.strip()
        except subprocess.SubprocessError as e:
            logger.error(f"Error searching in file content: {e}")
            return f"Error: {e!s}"

    def file_find_by_name(self, path: str, glob: str) -> str:
        r"""Find files by name pattern in specified directory.

        Args:
            path (str): Absolute path of directory to search.
            glob (str): Filename pattern using glob syntax wildcards.

        Returns:
            str: List of files matching the pattern.

        Raises:
            FileNotFoundError: If the specified directory does not exist.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Directory not found: {path}")

        if not os.path.isdir(path):
            raise ValueError(f"The path provided is not a directory: {path}")

        command = []
        if self.os_type in ['Darwin', 'Linux']:  # macOS or Linux
            command.extend(["find", path, "-name", glob])
        else:  # Windows
            # For Windows, we use dir command with /s for recursive search
            # and /b for bare format
            # Convert glob pattern to something Windows can understand
            pattern = glob.replace("*", "*").replace("?", "?")
            command.extend(["dir", "/s", "/b", os.path.join(path, pattern)])

        try:
            result = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            return result.stdout.strip()
        except subprocess.SubprocessError as e:
            logger.error(f"Error finding files by name: {e}")
            return f"Error: {e!s}"

    def shell_exec(self, id: str, exec_dir: str, command: str) -> str:
        r"""Execute commands in a specified shell session.

        Args:
            id (str): Unique identifier of the target shell session.
            exec_dir (str): Working directory for command execution (must use
                absolute path).
            command (str): Shell command to execute.

        Returns:
            str: Output of the command execution or error message.

        Raises:
            ValueError: If the exec_dir is not an absolute path or doesn't
                exist.
        """
        if not os.path.isabs(exec_dir):
            raise ValueError(f"exec_dir must be an absolute path: {exec_dir}")

        if not os.path.exists(exec_dir):
            raise FileNotFoundError(f"Directory not found: {exec_dir}")

        # If the session doesn't exist, create a new one
        if id not in self.shell_sessions:
            self.shell_sessions[id] = {
                "process": None,
                "output": "",
                "running": False,
            }

        try:
            # Execute the command in the specified directory
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=exec_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Store the process and mark as running
            self.shell_sessions[id]["process"] = process
            self.shell_sessions[id]["running"] = True
            self.shell_sessions[id]["output"] = ""

            # Get initial output (non-blocking)
            stdout, stderr = "", ""
            try:
                stdout, stderr = process.communicate(timeout=0.1)
            except subprocess.TimeoutExpired:
                # Process is still running, which is fine
                pass

            output = stdout
            if stderr:
                output += f"\nErrors:\n{stderr}"

            self.shell_sessions[id]["output"] = output
            return (
                f"Command started in session '{id}'. Initial output: {output}"
            )

        except subprocess.SubprocessError as e:
            self.shell_sessions[id]["running"] = False
            error_msg = f"Error executing command: {e}"
            self.shell_sessions[id]["output"] = error_msg
            logger.error(error_msg)
            return error_msg

    def shell_view(self, id: str) -> str:
        r"""View the content of a specified shell session.

        Args:
            id (str): Unique identifier of the target shell session.

        Returns:
            str: Current output content of the shell session.

        Raises:
            ValueError: If the specified shell session does not exist.
        """
        if id not in self.shell_sessions:
            raise ValueError(f"Shell session not found: {id}")

        session = self.shell_sessions[id]
        process = session.get("process")

        if process is None:
            return f"No active process in session '{id}'"

        # Try to get any new output
        if session["running"] and process.poll() is None:
            try:
                stdout, stderr = process.communicate(timeout=0.1)
                if stdout:
                    session["output"] += stdout
                if stderr:
                    session["output"] += f"\nErrors:\n{stderr}"
            except subprocess.TimeoutExpired:
                # Process is still running, which is fine
                pass
            except Exception as e:
                logger.error(f"Error getting process output: {e}")

        # Check if the process has completed
        if process.poll() is not None and session["running"]:
            stdout, stderr = process.communicate()
            if stdout:
                session["output"] += stdout
            if stderr:
                session["output"] += f"\nErrors:\n{stderr}"
            session["running"] = False

        return session["output"]

    def shell_wait(self, id: str, seconds: Optional[int] = None) -> str:
        r"""Wait for the running process in a specified shell session to
        return.

        Args:
            id (str): Unique identifier of the target shell session.
            seconds (Optional[int], optional): Wait duration in seconds.
                If None, wait indefinitely. Defaults to None.

        Returns:
            str: Final output content after waiting.

        Raises:
            ValueError: If the specified shell session does not exist.
        """
        if id not in self.shell_sessions:
            raise ValueError(f"Shell session not found: {id}")

        session = self.shell_sessions[id]
        process = session.get("process")

        if process is None:
            return f"No active process in session '{id}'"

        if not session["running"]:
            return f"Process in session '{id}' is not running"

        try:
            stdout, stderr = process.communicate(timeout=seconds)

            if stdout:
                session["output"] += stdout
            if stderr:
                session["output"] += f"\nErrors:\n{stderr}"

            session["running"] = False
            return (
                f"Process completed in session '{id}'. "
                f"Output: {session['output']}"
            )

        except subprocess.TimeoutExpired:
            return (
                f"Process in session '{id}' is still running "
                f"after {seconds} seconds"
            )
        except Exception as e:
            logger.error(f"Error waiting for process: {e}")
            return f"Error waiting for process: {e!s}"

    def shell_write_to_process(
        self, id: str, input: str, press_enter: bool
    ) -> str:
        r"""Write input to a running process in a specified shell session.

        Args:
            id (str): Unique identifier of the target shell session.
            input (str): Input content to write to the process.
            press_enter (bool): Whether to press Enter key after input.

        Returns:
            str: Status message indicating whether the input was sent.

        Raises:
            ValueError: If the specified shell session does not exist or is
                not running.
        """
        if id not in self.shell_sessions:
            raise ValueError(f"Shell session not found: {id}")

        session = self.shell_sessions[id]
        process = session.get("process")

        if process is None:
            return f"No active process in session '{id}'"

        if not session["running"] or process.poll() is not None:
            return f"Process in session '{id}' is not running"

        try:
            if press_enter:
                input = input + "\n"

            process.stdin.write(input)
            process.stdin.flush()

            return f"Input sent to process in session '{id}'"
        except Exception as e:
            logger.error(f"Error writing to process: {e}")
            return f"Error writing to process: {e!s}"

    def shell_kill_process(self, id: str) -> str:
        r"""Terminate a running process in a specified shell session.

        Args:
            id (str): Unique identifier of the target shell session.

        Returns:
            str: Status message indicating whether the process was terminated.

        Raises:
            ValueError: If the specified shell session does not exist.
        """
        if id not in self.shell_sessions:
            raise ValueError(f"Shell session not found: {id}")

        session = self.shell_sessions[id]
        process = session.get("process")

        if process is None:
            return f"No active process in session '{id}'"

        if not session["running"] or process.poll() is not None:
            return f"Process in session '{id}' is not running"

        try:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

            session["running"] = False
            return f"Process in session '{id}' has been terminated"
        except Exception as e:
            logger.error(f"Error killing process: {e}")
            return f"Error killing process: {e!s}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the
                functions in the toolkit.
        """
        return [
            FunctionTool(self.file_find_in_content),
            FunctionTool(self.file_find_by_name),
            FunctionTool(self.shell_exec),
            FunctionTool(self.shell_view),
            FunctionTool(self.shell_wait),
            FunctionTool(self.shell_write_to_process),
            FunctionTool(self.shell_kill_process),
        ]
