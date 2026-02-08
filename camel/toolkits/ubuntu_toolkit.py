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
class UbuntuToolkit(BaseToolkit):
    r"""A toolkit for interacting with an Ubuntu system.

    Provides tools for shell command execution, file system operations,
    package management, system monitoring, and networking utilities.
    Designed for use in Ubuntu-based environments (local or containerized).

    Attributes:
        command_timeout (int): Default timeout in seconds for shell commands.
        working_directory (str): Working directory for command execution.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        command_timeout: int = 120,
        working_directory: Optional[str] = None,
    ):
        r"""Initializes the UbuntuToolkit.

        Args:
            timeout (Optional[float]): Timeout for API requests in seconds.
                (default: :obj:`None`)
            command_timeout (int): Default timeout in seconds for shell
                command execution. (default: :obj:`120`)
            working_directory (Optional[str]): Working directory for
                command execution. If None, uses current directory.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        self.command_timeout = command_timeout
        self.working_directory = working_directory or os.getcwd()

    def _run_command(
        self,
        command: List[str],
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
    ) -> str:
        r"""Runs a command and returns its output.

        Args:
            command (List[str]): The command to run as a list of strings.
            timeout (Optional[int]): Timeout for the command in seconds.
                If None, uses the default command_timeout.
                (default: :obj:`None`)
            cwd (Optional[str]): Working directory for the command.
                If None, uses the instance working_directory.
                (default: :obj:`None`)

        Returns:
            str: The stdout output if successful, or an error message.
        """
        effective_timeout = timeout or self.command_timeout
        effective_cwd = cwd or self.working_directory

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                cwd=effective_cwd,
            )
            if result.returncode != 0:
                error_msg = (
                    result.stderr.strip()
                    or f"Command failed with return code "
                    f"{result.returncode}"
                )
                logger.warning(
                    f"Command {command} returned non-zero exit code "
                    f"{result.returncode}: {error_msg}"
                )
                return f"Error (exit code {result.returncode}): {error_msg}"
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error(
                f"Command {command} timed out after {effective_timeout}s"
            )
            return (
                f"Error: Command timed out after {effective_timeout} seconds"
            )
        except FileNotFoundError:
            logger.error(f"Command not found: {command[0]}")
            return f"Error: Command not found: {command[0]}"
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return f"Error: {e}"

    def execute_command(
        self,
        command: str,
        timeout: Optional[int] = None,
    ) -> str:
        r"""Executes a shell command on the Ubuntu system.

        Args:
            command (str): The shell command to execute.
            timeout (Optional[int]): Timeout in seconds for the command.
                If None, uses the default command_timeout.
                (default: :obj:`None`)

        Returns:
            str: The command output or an error message.
        """
        try:
            args = shlex.split(command)
        except ValueError as e:
            return f"Error: Invalid command syntax: {e}"

        if not args:
            return "Error: Empty command"

        return self._run_command(args, timeout=timeout)

    def read_file(self, file_path: str) -> str:
        r"""Reads the content of a file.

        Args:
            file_path (str): Path to the file to read.

        Returns:
            str: The file content or an error message.
        """
        try:
            resolved = os.path.join(self.working_directory, file_path)
            with open(resolved, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File not found: {file_path}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return f"Error: {e}"

    def write_file(self, file_path: str, content: str) -> str:
        r"""Writes content to a file.

        Args:
            file_path (str): Path to the file to write.
            content (str): Content to write to the file.

        Returns:
            str: Success message or an error message.
        """
        try:
            resolved = os.path.join(self.working_directory, file_path)
            os.makedirs(os.path.dirname(resolved) or '.', exist_ok=True)
            with open(resolved, 'w') as f:
                f.write(content)
            return f"Successfully wrote to {file_path}"
        except PermissionError:
            return f"Error: Permission denied: {file_path}"
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return f"Error: {e}"

    def list_directory(self, path: str = ".") -> str:
        r"""Lists files and directories at the given path.

        Args:
            path (str): Directory path to list. (default: :obj:`"."`)

        Returns:
            str: A newline-separated list of directory contents or an
                error message.
        """
        try:
            resolved = os.path.join(self.working_directory, path)
            entries = sorted(os.listdir(resolved))
            if not entries:
                return f"Directory '{path}' is empty"
            return "\n".join(entries)
        except FileNotFoundError:
            return f"Error: Directory not found: {path}"
        except PermissionError:
            return f"Error: Permission denied: {path}"
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return f"Error: {e}"

    def search_files(
        self,
        pattern: str,
        path: str = ".",
    ) -> str:
        r"""Searches for files matching a pattern using the `find` command.

        Args:
            pattern (str): The filename pattern to search for
                (e.g., "*.py", "config.*").
            path (str): The directory to search in. (default: :obj:`"."`)

        Returns:
            str: Newline-separated list of matching file paths or an
                error message.
        """
        resolved = os.path.join(self.working_directory, path)
        return self._run_command(
            ["find", resolved, "-name", pattern, "-type", "f"]
        )

    def install_package(self, package_name: str) -> str:
        r"""Installs a system package using APT.

        Args:
            package_name (str): Name of the package to install.

        Returns:
            str: Installation output or an error message.
        """
        return self._run_command(
            [
                "apt-get",
                "install",
                "-y",
                "--no-install-recommends",
                package_name,
            ],
            timeout=300,
        )

    def get_system_info(self) -> str:
        r"""Retrieves system information including OS version, kernel, CPU,
        memory, and disk usage.

        Returns:
            str: Formatted system information string.
        """
        info_parts = []

        # OS release
        os_info = self._run_command(
            ["cat", "/etc/os-release"]
        )
        info_parts.append(f"OS Info:\n{os_info}")

        # Kernel
        kernel = self._run_command(["uname", "-r"])
        info_parts.append(f"Kernel: {kernel}")

        # CPU info
        cpu_info = self._run_command(
            ["grep", "-c", "^processor", "/proc/cpuinfo"]
        )
        info_parts.append(f"CPU Cores: {cpu_info}")

        # Memory
        mem_info = self._run_command(["free", "-h"])
        info_parts.append(f"Memory:\n{mem_info}")

        # Disk
        disk_info = self._run_command(["df", "-h", "/"])
        info_parts.append(f"Disk:\n{disk_info}")

        return "\n\n".join(info_parts)

    def get_process_list(self) -> str:
        r"""Lists currently running processes.

        Returns:
            str: Process list output or an error message.
        """
        return self._run_command(["ps", "aux", "--sort=-pcpu"])

    def get_network_info(self) -> str:
        r"""Retrieves network interface information.

        Returns:
            str: Network interface information or an error message.
        """
        # Try ip command first, fall back to ifconfig
        result = self._run_command(["ip", "addr", "show"])
        if result.startswith("Error: Command not found"):
            result = self._run_command(["ifconfig"])
        return result

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects for Ubuntu operations.

        Returns:
            List[FunctionTool]: List of Ubuntu system tool functions.
        """
        return [
            FunctionTool(self.execute_command),
            FunctionTool(self.read_file),
            FunctionTool(self.write_file),
            FunctionTool(self.list_directory),
            FunctionTool(self.search_files),
            FunctionTool(self.install_package),
            FunctionTool(self.get_system_info),
            FunctionTool(self.get_process_list),
            FunctionTool(self.get_network_info),
        ]
