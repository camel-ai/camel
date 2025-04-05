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

import atexit
import os
import platform
import queue
import subprocess
import sys
import threading
import venv
from queue import Queue
from typing import Any, Dict, List, Optional, Tuple

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class TerminalToolkit(BaseToolkit):
    r"""A toolkit for terminal operations across multiple operating systems.

    This toolkit provides a set of functions for terminal operations such as
    searching for files by name or content, executing shell commands, and
    managing terminal sessions.

    Args:
        timeout (Optional[float]): The timeout for terminal operations.
        shell_sessions (Optional[Dict[str, Any]]): A dictionary to store
            shell session information. If None, an empty dictionary will be
            used. (default: :obj:`{}`)
        working_dir (str): The working directory for operations.
            If specified, all execution and write operations will be restricted
            to this directory. Read operations can access paths outside this
            directory.(default: :obj:`"./workspace"`)
        need_terminal (bool): Whether to create a terminal interface.
            (default: :obj:`True`)
        use_shell_mode (bool): Whether to use shell mode for command execution.
            (default: :obj:`True`)
        clone_current_env (bool): Whether to clone the current Python
            environment.(default: :obj:`False`)
        safe_mode (bool): Whether to enable safe mode to restrict operations.
            (default: :obj:`True`)

    Note:
        Most functions are compatible with Unix-based systems (macOS, Linux).
        For Windows compatibility, additional implementation details are
        needed.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        shell_sessions: Optional[Dict[str, Any]] = None,
        working_dir: str = "./workspace",
        need_terminal: bool = True,
        use_shell_mode: bool = True,
        clone_current_env: bool = False,
        safe_mode: bool = True,
    ):
        super().__init__(timeout=timeout)
        self.shell_sessions = shell_sessions or {}
        self.os_type = platform.system()
        self.output_queue: Queue[str] = Queue()
        self.agent_queue: Queue[str] = Queue()
        self.terminal_ready = threading.Event()
        self.gui_thread = None
        self.safe_mode = safe_mode

        self.cloned_env_path = None
        self.use_shell_mode = use_shell_mode

        self.python_executable = sys.executable
        self.is_macos = platform.system() == 'Darwin'

        atexit.register(self.__del__)

        if not os.path.exists(working_dir):
            os.makedirs(working_dir, exist_ok=True)
        self.working_dir = os.path.abspath(working_dir)
        self._update_terminal_output(
            f"Working directory set to: {self.working_dir}\n"
        )
        if self.safe_mode:
            self._update_terminal_output(
                "Safe mode enabled: Write operations can only "
                "be performed within the working directory\n"
            )

        if clone_current_env:
            self.cloned_env_path = os.path.join(self.working_dir, ".venv")
            self._clone_current_environment()
        else:
            self.cloned_env_path = None

        if need_terminal:
            if self.is_macos:
                # macOS uses non-GUI mode
                logger.info("Detected macOS environment, using non-GUI mode")
                self._setup_file_output()
                self.terminal_ready.set()
            else:
                # Other platforms use normal GUI
                self.gui_thread = threading.Thread(
                    target=self._create_terminal, daemon=True
                )
                self.gui_thread.start()
                self.terminal_ready.wait(timeout=5)

    def _setup_file_output(self):
        r"""Set up file output to replace GUI, using a fixed file to simulate
        terminal.
        """

        self.log_file = os.path.join(os.getcwd(), "camel_terminal.txt")

        if os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.truncate(0)
                f.write("CAMEL Terminal Session\n")
                f.write("=" * 50 + "\n")
                f.write(f"Working Directory: {os.getcwd()}\n")
                f.write("=" * 50 + "\n\n")
        else:
            with open(self.log_file, "w") as f:
                f.write("CAMEL Terminal Session\n")
                f.write("=" * 50 + "\n")
                f.write(f"Working Directory: {os.getcwd()}\n")
                f.write("=" * 50 + "\n\n")

        # Inform the user
        logger.info(f"Terminal output redirected to: {self.log_file}")

        def file_update(output: str):
            try:
                # Directly append to the end of the file
                with open(self.log_file, "a") as f:
                    f.write(output)
                    # If the output does not end with a newline, add one
                    if output and not output.endswith('\n'):
                        f.write('\n')
                # Ensure the agent also receives the output
                self.agent_queue.put(output)
            except Exception as e:
                logger.error(f"Failed to write to terminal: {e}")

        # Replace the update method
        self._update_terminal_output = file_update

    def _clone_current_environment(self):
        r"""Create a new Python virtual environment."""
        try:
            if os.path.exists(self.cloned_env_path):
                self._update_terminal_output(
                    f"Using existing environment: {self.cloned_env_path}\n"
                )
                return

            self._update_terminal_output(
                f"Creating new Python environment at:{self.cloned_env_path}\n"
            )

            venv.create(self.cloned_env_path, with_pip=True)
            self._update_terminal_output(
                "New Python environment created successfully!\n"
            )

        except Exception as e:
            self._update_terminal_output(
                f"Failed to create environment: {e!s}\n"
            )
            logger.error(f"Failed to create environment: {e}")

    def _create_terminal(self):
        r"""Create a terminal GUI."""

        try:
            import tkinter as tk
            from tkinter import scrolledtext

            def update_terminal():
                try:
                    while True:
                        output = self.output_queue.get_nowait()
                        if isinstance(output, bytes):
                            output = output.decode('utf-8', errors='replace')
                        self.terminal.insert(tk.END, output)
                        self.terminal.see(tk.END)
                except queue.Empty:
                    if hasattr(self, 'root') and self.root:
                        self.root.after(100, update_terminal)

            self.root = tk.Tk()
            self.root.title(f"{self.os_type} Terminal")

            self.root.geometry("800x600")
            self.root.minsize(400, 300)

            self.terminal = scrolledtext.ScrolledText(
                self.root,
                wrap=tk.WORD,
                bg='black',
                fg='white',
                font=('Consolas', 10),
                insertbackground='white',  # Cursor color
            )
            self.terminal.pack(fill=tk.BOTH, expand=True)

            # Set the handling for closing the window
            def on_closing():
                self.root.quit()
                self.root.destroy()
                self.root = None

            self.root.protocol("WM_DELETE_WINDOW", on_closing)

            # Start updating
            update_terminal()

            # Mark the terminal as ready
            self.terminal_ready.set()

            # Start the main loop
            self.root.mainloop()

        except Exception as e:
            logger.error(f"Failed to create terminal: {e}")
            self.terminal_ready.set()

    def _update_terminal_output(self, output: str):
        r"""Update terminal output and send to agent.

        Args:
            output (str): The output to be sent to the agent
        """
        try:
            # If it is macOS , only write to file
            if self.is_macos:
                if hasattr(self, 'log_file'):
                    with open(self.log_file, "a") as f:
                        f.write(output)
                # Ensure the agent also receives the output
                self.agent_queue.put(output)
                return

            # For other cases, try to update the GUI (if it exists)
            if hasattr(self, 'root') and self.root:
                self.output_queue.put(output)

            # Always send to agent queue
            self.agent_queue.put(output)

        except Exception as e:
            logger.error(f"Failed to update terminal output: {e}")

    def _is_path_within_working_dir(self, path: str) -> bool:
        r"""Check if the path is within the working directory.

        Args:
            path (str): The path to check

        Returns:
            bool: Returns True if the path is within the working directory,
                otherwise returns False
        """
        abs_path = os.path.abspath(path)
        return abs_path.startswith(self.working_dir)

    def _enforce_working_dir_for_execution(self, path: str) -> Optional[str]:
        r"""Enforce working directory restrictions, return error message
        if execution path is not within the working directory.

        Args:
            path (str): The path to be used for executing operations

        Returns:
            Optional[str]: Returns error message if the path is not within
                the working directory, otherwise returns None
        """
        if not self._is_path_within_working_dir(path):
            return (
                f"Operation restriction: Execution path {path} must "
                f"be within working directory {self.working_dir}"
            )
        return None

    def _copy_external_file_to_workdir(
        self, external_file: str
    ) -> Optional[str]:
        r"""Copy external file to working directory.

        Args:
            external_file (str): The path of the external file

        Returns:
            Optional[str]: New path after copying to the working directory,
                returns None on failure
        """
        try:
            import shutil

            filename = os.path.basename(external_file)
            new_path = os.path.join(self.working_dir, filename)
            shutil.copy2(external_file, new_path)
            return new_path
        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            return None

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
        """

        if not os.path.exists(file):
            return f"File not found: {file}"

        if not os.path.isfile(file):
            return f"The path provided is not a file: {file}"

        command = []
        if sudo:
            error_msg = self._enforce_working_dir_for_execution(file)
            if error_msg:
                return error_msg
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
        """
        if not os.path.exists(path):
            return f"Directory not found: {path}"

        if not os.path.isdir(path):
            return f"The path provided is not a directory: {path}"

        command = []
        if self.os_type in ['Darwin', 'Linux']:  # macOS or Linux
            command.extend(["find", path, "-name", glob])
        else:  # Windows
            # For Windows, we use dir command with /s for recursive search
            # and /b for bare format

            pattern = glob
            file_path = os.path.join(path, pattern).replace('/', '\\')
            command.extend(["cmd", "/c", "dir", "/s", "/b", file_path])

        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                shell=False,
            )

            output = result.stdout.strip()
            if self.os_type == 'Windows':
                output = output.replace('\\', '/')
            return output
        except subprocess.SubprocessError as e:
            logger.error(f"Error finding files by name: {e}")
            return f"Error: {e!s}"

    def _sanitize_command(self, command: str, exec_dir: str) -> Tuple:
        r"""Check and modify command to ensure safety.

        Args:
            command (str): The command to check
            exec_dir (str): The directory to execute the command in

        Returns:
            Tuple: (is safe, modified command or error message)
        """
        if not self.safe_mode:
            return True, command

        if not command or command.strip() == "":
            return False, "Empty command"

        # Use shlex for safer command parsing
        import shlex

        try:
            parts = shlex.split(command)
        except ValueError as e:
            # Handle malformed commands (e.g., unbalanced quotes)
            return False, f"Invalid command format: {e}"

        if not parts:
            return False, "Empty command"

        # Get base command
        base_cmd = parts[0].lower()

        # Handle special commands
        if base_cmd in ['cd', 'chdir']:
            # Check if cd command attempts to leave the working directory
            if len(parts) > 1:
                target_dir = parts[1].strip('"\'')
                if (
                    target_dir.startswith('/')
                    or target_dir.startswith('\\')
                    or ':' in target_dir
                ):
                    # Absolute path
                    abs_path = os.path.abspath(target_dir)
                else:
                    # Relative path
                    abs_path = os.path.abspath(
                        os.path.join(exec_dir, target_dir)
                    )

                if not self._is_path_within_working_dir(abs_path):
                    return False, (
                        f"Safety restriction: Cannot change to directory "
                        f"outside of working directory {self.working_dir}"
                    )

        # Check file operation commands
        elif base_cmd in [
            'rm',
            'del',
            'rmdir',
            'rd',
            'deltree',
            'erase',
            'unlink',
            'shred',
            'srm',
            'wipe',
            'remove',
        ]:
            # Check targets of delete commands
            for _, part in enumerate(parts[1:], 1):
                if part.startswith('-') or part.startswith(
                    '/'
                ):  # Skip options
                    continue

                target = part.strip('"\'')
                if (
                    target.startswith('/')
                    or target.startswith('\\')
                    or ':' in target
                ):
                    # Absolute path
                    abs_path = os.path.abspath(target)
                else:
                    # Relative path
                    abs_path = os.path.abspath(os.path.join(exec_dir, target))

                if not self._is_path_within_working_dir(abs_path):
                    return False, (
                        f"Safety restriction: Cannot delete files outside "
                        f"of working directory {self.working_dir}"
                    )

        # Check write/modify commands
        elif base_cmd in [
            'touch',
            'mkdir',
            'md',
            'echo',
            'cat',
            'cp',
            'copy',
            'mv',
            'move',
            'rename',
            'ren',
            'write',
            'output',
        ]:
            # Check for redirection symbols
            full_cmd = command.lower()
            if '>' in full_cmd:
                # Find the file path after redirection
                redirect_parts = command.split('>')
                if len(redirect_parts) > 1:
                    output_file = (
                        redirect_parts[1].strip().split()[0].strip('"\'')
                    )
                    if (
                        output_file.startswith('/')
                        or output_file.startswith('\\')
                        or ':' in output_file
                    ):
                        # Absolute path
                        abs_path = os.path.abspath(output_file)
                    else:
                        # Relative path
                        abs_path = os.path.abspath(
                            os.path.join(exec_dir, output_file)
                        )

                    if not self._is_path_within_working_dir(abs_path):
                        return False, (
                            f"Safety restriction: Cannot write to file "
                            f"outside of working directory {self.working_dir}"
                        )

            # For cp/mv commands, check target paths
            if base_cmd in ['cp', 'copy', 'mv', 'move']:
                # Simple handling, assuming the last parameter is the target
                if len(parts) > 2:
                    target = parts[-1].strip('"\'')
                    if (
                        target.startswith('/')
                        or target.startswith('\\')
                        or ':' in target
                    ):
                        # Absolute path
                        abs_path = os.path.abspath(target)
                    else:
                        # Relative path
                        abs_path = os.path.abspath(
                            os.path.join(exec_dir, target)
                        )

                    if not self._is_path_within_working_dir(abs_path):
                        return False, (
                            f"Safety restriction: Cannot write to file "
                            f"outside of working directory {self.working_dir}"
                        )

        # Check dangerous commands
        elif base_cmd in [
            'sudo',
            'su',
            'chmod',
            'chown',
            'chgrp',
            'passwd',
            'mkfs',
            'fdisk',
            'dd',
            'shutdown',
            'reboot',
            'halt',
            'poweroff',
            'init',
        ]:
            return False, (
                f"Safety restriction: Command '{base_cmd}' may affect system "
                f"security and is prohibited"
            )

        # Check network commands
        elif base_cmd in ['ssh', 'telnet', 'ftp', 'sftp', 'nc', 'netcat']:
            return False, (
                f"Safety restriction: Network command '{base_cmd}' "
                f"is prohibited"
            )

        # Add copy functionality - copy from external to working directory
        elif base_cmd == 'safecopy':
            # Custom command: safecopy <source file> <target file>
            if len(parts) != 3:
                return False, "Usage: safecopy <source file> <target file>"

            source = parts[1].strip('\'"')
            target = parts[2].strip('\'"')

            # Check if source file exists
            if not os.path.exists(source):
                return False, f"Source file does not exist: {source}"

            # Ensure target is within working directory
            if (
                target.startswith('/')
                or target.startswith('\\')
                or ':' in target
            ):
                # Absolute path
                abs_target = os.path.abspath(target)
            else:
                # Relative path
                abs_target = os.path.abspath(os.path.join(exec_dir, target))

            if not self._is_path_within_working_dir(abs_target):
                return False, (
                    f"Safety restriction: Target file must be within "
                    f"working directory {self.working_dir}"
                )

            # Replace with safe copy command
            if self.os_type == 'Windows':
                return True, f"copy \"{source}\" \"{abs_target}\""
            else:
                return True, f"cp \"{source}\" \"{abs_target}\""

        return True, command

    def shell_exec(self, id: str, command: str) -> str:
        r"""Execute commands. This can be used to execute various commands,
        such as writing code, executing code, and running commands.

        Args:
            id (str): Unique identifier of the target shell session.
            command (str): Shell command to execute.

        Returns:
            str: Output of the command execution or error message.
        """
        # Command execution must be within the working directory
        error_msg = self._enforce_working_dir_for_execution(self.working_dir)
        if error_msg:
            return error_msg

        if self.safe_mode:
            is_safe, sanitized_command = self._sanitize_command(
                command, self.working_dir
            )
            if not is_safe:
                return f"Command rejected: {sanitized_command}"
            command = sanitized_command

        # If the session does not exist, create a new session
        if id not in self.shell_sessions:
            self.shell_sessions[id] = {
                "process": None,
                "output": "",
                "running": False,
            }

        try:
            # First, log the command to be executed
            self._update_terminal_output(f"\n$ {command}\n")

            if command.startswith('python') or command.startswith('pip'):
                if self.cloned_env_path:
                    if self.os_type == 'Windows':
                        base_path = os.path.join(
                            self.cloned_env_path, "Scripts"
                        )
                        python_path = os.path.join(base_path, "python.exe")
                        pip_path = os.path.join(base_path, "pip.exe")
                    else:
                        base_path = os.path.join(self.cloned_env_path, "bin")
                        python_path = os.path.join(base_path, "python")
                        pip_path = os.path.join(base_path, "pip")
                else:
                    python_path = self.python_executable
                    pip_path = f'"{python_path}" -m pip'

                if command.startswith('python'):
                    command = command.replace('python', f'"{python_path}"', 1)
                elif command.startswith('pip'):
                    command = command.replace('pip', pip_path, 1)

            if self.is_macos:
                # Type safe version - macOS uses subprocess.run
                process = subprocess.run(
                    command,
                    shell=True,
                    cwd=self.working_dir,
                    capture_output=True,
                    text=True,
                    env=os.environ.copy(),
                )

                # Process the output
                output = process.stdout or ""
                if process.stderr:
                    output += f"\nStderr Output:\n{process.stderr}"

                # Update session information and terminal
                self.shell_sessions[id]["output"] = output
                self._update_terminal_output(output + "\n")

                return output

            else:
                # Non-macOS systems use the Popen method
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    cwd=self.working_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=os.environ.copy(),
                )

                # Store the process and mark it as running
                self.shell_sessions[id]["process"] = proc
                self.shell_sessions[id]["running"] = True

                # Get output
                stdout, stderr = proc.communicate()

                output = stdout or ""
                if stderr:
                    output += f"\nStderr Output:\n{stderr}"

                # Update session information and terminal
                self.shell_sessions[id]["output"] = output
                self._update_terminal_output(output + "\n")

                return output

        except Exception as e:
            error_msg = f"Command execution error: {e!s}"
            logger.error(error_msg)
            self._update_terminal_output(f"\nError: {error_msg}\n")

            # More detailed error information
            import traceback

            detailed_error = traceback.format_exc()
            return (
                f"Error: {error_msg}\n\n"
                f"Detailed information: {detailed_error}"
            )

    def shell_view(self, id: str) -> str:
        r"""View the content of a specified shell session.

        Args:
            id (str): Unique identifier of the target shell session.

        Returns:
            str: Current output content of the shell session.
        """
        if id not in self.shell_sessions:
            return f"Shell session not found: {id}"

        session = self.shell_sessions[id]

        try:
            # Check process status
            if session["process"].poll() is not None:
                session["running"] = False

            # Collect all new output from agent queue
            new_output = ""
            try:
                while True:
                    output = self.agent_queue.get_nowait()
                    new_output += output
                    session["output"] += output
            except queue.Empty:
                pass

            return new_output or session["output"]

        except Exception as e:
            error_msg = f"Error reading terminal output: {e}"
            self._update_terminal_output(f"\nError: {error_msg}\n")
            logger.error(error_msg)
            return f"Error: {e!s}"

    def shell_wait(self, id: str, seconds: Optional[int] = None) -> str:
        r"""Wait for the running process in a specified shell session to
        return.

        Args:
            id (str): Unique identifier of the target shell session.
            seconds (Optional[int], optional): Wait duration in seconds.
                If None, wait indefinitely. Defaults to None.

        Returns:
            str: Final output content after waiting.
        """
        if id not in self.shell_sessions:
            return f"Shell session not found: {id}"

        session = self.shell_sessions[id]
        process = session.get("process")

        if process is None:
            return f"No active process in session '{id}'"

        if not session["running"] or process.poll() is not None:
            return f"Process in session '{id}' is not running"

        try:
            if hasattr(process, 'communicate'):
                # Use communicate with timeout
                stdout, stderr = process.communicate(timeout=seconds)

                if stdout:
                    stdout_str = (
                        stdout.decode('utf-8')
                        if isinstance(stdout, bytes)
                        else stdout
                    )
                    session["output"] += stdout_str
                if stderr:
                    stderr_str = (
                        stderr.decode('utf-8')
                        if isinstance(stderr, bytes)
                        else stderr
                    )
                    if stderr_str:
                        session["output"] += f"\nStderr Output:\n{stderr_str}"

                session["running"] = False
                return (
                    f"Process completed in session '{id}'. "
                    f"Output: {session['output']}"
                )
            else:
                return (
                    f"Process already completed in session '{id}'. "
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
        """
        if id not in self.shell_sessions:
            return f"Shell session not found: {id}"

        session = self.shell_sessions[id]
        process = session.get("process")

        if process is None:
            return f"No active process in session '{id}'"

        if not session["running"] or process.poll() is not None:
            return f"Process in session '{id}' is not running"

        try:
            if not process.stdin or process.stdin.closed:
                return (
                    f"Cannot write to process in session '{id}': "
                    f"stdin is closed"
                )

            if press_enter:
                input = input + "\n"

            # Write bytes to stdin
            process.stdin.write(input.encode('utf-8'))
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
        """
        if id not in self.shell_sessions:
            return f"Shell session not found: {id}"

        session = self.shell_sessions[id]
        process = session.get("process")

        if process is None:
            return f"No active process in session '{id}'"

        if not session["running"] or process.poll() is not None:
            return f"Process in session '{id}' is not running"

        try:
            # Clean up process resources before termination
            if process.stdin and not process.stdin.closed:
                process.stdin.close()

            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(
                    f"Process in session '{id}' did not terminate gracefully"
                    f", forcing kill"
                )
                process.kill()

            session["running"] = False
            return f"Process in session '{id}' has been terminated"
        except Exception as e:
            logger.error(f"Error killing process: {e}")
            return f"Error killing process: {e!s}"

    def __del__(self):
        r"""Clean up resources when the object is being destroyed.
        Terminates all running processes and closes any open file handles.
        """
        # Log that cleanup is starting
        logger.info("TerminalToolkit cleanup initiated")

        # Clean up all processes in shell sessions
        for session_id, session in self.shell_sessions.items():
            process = session.get("process")
            if process is not None and session.get("running", False):
                try:
                    logger.info(
                        f"Terminating process in session '{session_id}'"
                    )

                    # Close process input/output streams if open
                    if (
                        hasattr(process, 'stdin')
                        and process.stdin
                        and not process.stdin.closed
                    ):
                        process.stdin.close()

                    # Terminate the process
                    process.terminate()
                    try:
                        # Give the process a short time to terminate gracefully
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        # Force kill if the process doesn't terminate
                        # gracefully
                        logger.warning(
                            f"Process in session '{session_id}' did not "
                            f"terminate gracefully, forcing kill"
                        )
                        process.kill()

                    # Mark the session as not running
                    session["running"] = False

                except Exception as e:
                    logger.error(
                        f"Error cleaning up process in session "
                        f"'{session_id}': {e}"
                    )

        # Close file output if it exists
        if hasattr(self, 'log_file') and self.is_macos:
            try:
                logger.info(f"Final terminal log saved to: {self.log_file}")
            except Exception as e:
                logger.error(f"Error logging file information: {e}")

        # Clean up GUI resources if they exist
        if hasattr(self, 'root') and self.root:
            try:
                logger.info("Closing terminal GUI")
                self.root.quit()
                self.root.destroy()
            except Exception as e:
                logger.error(f"Error closing terminal GUI: {e}")

        logger.info("TerminalToolkit cleanup completed")

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
