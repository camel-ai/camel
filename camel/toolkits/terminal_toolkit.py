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
        self._file_initialized = False
        self.cloned_env_path = None
        self.use_shell_mode = use_shell_mode
        self._human_takeover_active = False

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

        # Inform the user
        logger.info(f"Terminal output will be redirected to: {self.log_file}")

        def file_update(output: str):
            import sys

            try:
                # For macOS/Linux file-based mode, also write to stdout
                # to provide real-time feedback in the user's terminal.
                sys.stdout.write(output)
                sys.stdout.flush()

                # Initialize file on first write
                if not self._file_initialized:
                    with open(self.log_file, "w") as f:
                        f.write("CAMEL Terminal Session\n")
                        f.write("=" * 50 + "\n")
                        f.write(f"Working Directory: {os.getcwd()}\n")
                        f.write("=" * 50 + "\n\n")
                    self._file_initialized = True

                # Directly append to the end of the file
                with open(self.log_file, "a") as f:
                    f.write(output)
                # Ensure the agent also receives the output
                self.agent_queue.put(output)
            except Exception as e:
                logger.error(f"Failed to write to terminal: {e}")

        # Replace the update method
        self._update_terminal_output = file_update

    def _clone_current_environment(self):
        r"""Create a new Python virtual environment."""
        try:
            if self.cloned_env_path is None:
                self._update_terminal_output(
                    "Error: No environment path specified\n"
                )
                return

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
        r"""Create a terminal GUI. If GUI creation fails, fallback
        to file output."""

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
            logger.warning(
                f"Failed to create GUI terminal: {e}, "
                f"falling back to file output mode"
            )
            # Fallback to file output mode when GUI creation fails
            self._setup_file_output()
            self.terminal_ready.set()

    def _update_terminal_output(self, output: str):
        r"""Update terminal output and send to agent.

        Args:
            output (str): The output to be sent to the agent
        """
        try:
            # If it is macOS or if we have a log_file (fallback mode),
            # write to file
            if self.is_macos or hasattr(self, 'log_file'):
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
        r"""Search for text within a file's content using a regular expression.

        This function is useful for finding specific patterns or lines of text
        within a given file. It uses `grep` on Unix-like systems and `findstr`
        on Windows.

        Args:
            file (str): The absolute path of the file to search within.
            regex (str): The regular expression pattern to match.
            sudo (bool, optional): Whether to use sudo privileges for the
                search. Defaults to False. Note: Using sudo requires the
                process to have appropriate permissions.
                (default: :obj:`False`)

        Returns:
            str: The matching content found in the file. If no matches are
                found, an empty string is returned. Returns an error message
                if the file does not exist or another error occurs.
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
        r"""Find files by name in a specified directory using a glob pattern.

        This function recursively searches for files matching a given name or
        pattern within a directory. It uses `find` on Unix-like systems and
        `dir` on Windows.

        Args:
            path (str): The absolute path of the directory to search in.
            glob (str): The filename pattern to search for, using glob syntax
                (e.g., "*.py", "data*").

        Returns:
            str: A newline-separated string containing the paths of the files
                that match the pattern. Returns an error message if the
                directory does not exist or another error occurs.
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

    def shell_exec(
        self, id: str, command: str, interactive: bool = False
    ) -> str:
        r"""Executes a shell command in a specified session.

        This function creates and manages shell sessions to execute commands,
        simulating a real terminal. It can run commands in both non-interactive
        (capturing output) and interactive modes. Each session is identified by
        a unique ID. If a session with the given ID does not exist, it will be
        created.

        Args:
            id (str): A unique identifier for the shell session. This is used
                to manage multiple concurrent shell processes.
            command (str): The shell command to be executed.
            interactive (bool, optional): If `True`, the command runs in
                interactive mode, connecting it to the terminal's standard
                input. This is useful for commands that require user input,
                like `ssh`. Defaults to `False`. Interactive mode is only
                supported on macOS and Linux. (default: :obj:`False`)

        Returns:
            str: The standard output and standard error from the command. If an
                error occurs during execution, a descriptive error message is
                returned.

        Note:
            When `interactive` is set to `True`, this function may block if the
            command requires input. In safe mode, some commands that are
            considered dangerous are restricted.
        """
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

        if id not in self.shell_sessions:
            self.shell_sessions[id] = {
                "process": None,
                "output": "",
                "running": False,
            }

        try:
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

            if not interactive:
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

                self.shell_sessions[id]["process"] = proc
                self.shell_sessions[id]["running"] = True
                stdout, stderr = proc.communicate()
                output = stdout or ""
                if stderr:
                    output += f"\nStderr Output:\n{stderr}"
                self.shell_sessions[id]["output"] = output
                self._update_terminal_output(output + "\n")
                return output

            # Interactive mode with real-time streaming via PTY
            if self.os_type not in ['Darwin', 'Linux']:
                return (
                    "Interactive mode is not supported on "
                    f"{self.os_type} due to PTY limitations."
                )

            import pty
            import select
            import sys
            import termios
            import tty

            # Fork a new process with a PTY
            pid, master_fd = pty.fork()

            if pid == 0:  # Child process
                # Execute the command in the child process
                try:
                    import shlex

                    parts = shlex.split(command)
                    if not parts:
                        logger.error("Error: Empty command")
                        os._exit(1)

                    os.chdir(self.working_dir)
                    os.execvp(parts[0], parts)
                except (ValueError, IndexError, OSError) as e:
                    logger.error(f"Command execution error: {e}")
                    os._exit(127)
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    os._exit(1)

            # Parent process
            self.shell_sessions[id]["process_id"] = pid
            self.shell_sessions[id]["running"] = True
            output_lines: List[str] = []
            original_settings = termios.tcgetattr(sys.stdin)

            try:
                tty.setraw(sys.stdin.fileno())

                while True:
                    # Check if the child process has exited
                    try:
                        wait_pid, status = os.waitpid(pid, os.WNOHANG)
                        if wait_pid == pid:
                            self.shell_sessions[id]["running"] = False
                            break
                    except OSError:
                        # Process already reaped
                        self.shell_sessions[id]["running"] = False
                        break

                    # Use select to wait for I/O on stdin or master PTY
                    r, _, _ = select.select(
                        [sys.stdin, master_fd], [], [], 0.1
                    )

                    if master_fd in r:
                        try:
                            data = os.read(master_fd, 1024)
                            if not data:
                                break
                            decoded_data = data.decode(
                                'utf-8', errors='replace'
                            )
                            # Echo to user's terminal and log
                            self._update_terminal_output(decoded_data)
                            output_lines.append(decoded_data)
                        except OSError:
                            break  # PTY has been closed

                    if sys.stdin in r:
                        try:
                            user_input = os.read(sys.stdin.fileno(), 1024)
                            if not user_input:
                                break
                            os.write(master_fd, user_input)
                        except OSError:
                            break

            finally:
                if original_settings is not None:
                    termios.tcsetattr(
                        sys.stdin, termios.TCSADRAIN, original_settings
                    )
                if master_fd:
                    os.close(master_fd)

            final_output = "".join(output_lines)
            self.shell_sessions[id]["output"] = final_output
            return final_output

        except Exception as e:
            error_msg = f"Command execution error: {e!s}"
            logger.error(error_msg)
            self._update_terminal_output(f"\nError: {error_msg}\n")
            import traceback

            detailed_error = traceback.format_exc()
            return (
                f"Error: {error_msg}\n\n"
                f"Detailed information: {detailed_error}"
            )

    def shell_view(self, id: str) -> str:
        r"""View the full output history of a specified shell session.

        Retrieves the accumulated output (both stdout and stderr) generated by
        commands in the specified session since its creation. This is useful
        for checking the complete history of a session, especially after a
        command has finished execution.

        Args:
            id (str): The unique identifier of the shell session to view.

        Returns:
            str: The complete output history of the shell session. Returns an
                error message if the session is not found.
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
        r"""Wait for a command to finish in a specified shell session.

        Blocks execution and waits for the running process in a shell session
        to complete. This is useful for ensuring a long-running command has
        finished before proceeding.

        Args:
            id (str): The unique identifier of the target shell session.
            seconds (Optional[int], optional): The maximum time to wait, in
                seconds. If `None`, it waits indefinitely.
                (default: :obj:`None`)

        Returns:
            str: A message indicating that the process has completed, including
                the final output. If the process times out, it returns a
                timeout message.
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

        Sends a string of text to the standard input of a running process.
        This is useful for interacting with commands that require input. This
        function cannot be used with a command that was started in
        interactive mode.

        Args:
            id (str): The unique identifier of the target shell session.
            input (str): The text to write to the process's stdin.
            press_enter (bool): If `True`, a newline character (`\n`) is
                appended to the input, simulating pressing the Enter key.

        Returns:
            str: A status message indicating whether the input was sent, or an
                error message if the operation fails.
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

        Forcibly stops a command that is currently running in a shell session.
        This is useful for ending processes that are stuck, running too long,
        or need to be cancelled.

        Args:
            id (str): The unique identifier of the shell session containing the
                process to be terminated.

        Returns:
            str: A status message indicating that the process has been
                terminated, or an error message if the operation fails.
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

    def ask_user_for_help(self, id: str) -> str:
        r"""Pause the agent and ask a human for help with a command.

        This function should be used when the agent is stuck and requires
        manual intervention, such as solving a CAPTCHA or debugging a complex
        issue. It pauses the agent's execution and allows a human to take
        control of a specified shell session. The human can execute one
        command to resolve the issue, and then control is returned to the
        agent.

        Args:
            id (str): The identifier of the shell session for the human to
                interact with. If the session does not exist, it will be
                created.

        Returns:
            str: A status message indicating that the human has finished,
                including the number of commands executed. If the takeover
                times out or fails, an error message is returned.
        """
        # Input validation
        if not id or not isinstance(id, str):
            return "Error: Invalid session ID provided"

        # Prevent concurrent human takeovers
        if (
            hasattr(self, '_human_takeover_active')
            and self._human_takeover_active
        ):
            return "Error: Human takeover already in progress"

        try:
            self._human_takeover_active = True

            # Ensure the session exists so that the human can reuse it
            if id not in self.shell_sessions:
                self.shell_sessions[id] = {
                    "process": None,
                    "output": "",
                    "running": False,
                }

            command_count = 0
            error_occurred = False

            # Create clear banner message for user
            takeover_banner = (
                f"\n{'='*60}\n"
                f"🤖 CAMEL Agent needs human help! Session: {id}\n"
                f"📂 Working directory: {self.working_dir}\n"
                f"{'='*60}\n"
                f"💡 Type commands or '/exit' to return control to agent.\n"
                f"{'='*60}\n"
            )

            # Print once to console for immediate visibility
            print(takeover_banner, flush=True)
            # Log for terminal output tracking
            self._update_terminal_output(takeover_banner)

            # Helper flag + event for coordination
            done_event = threading.Event()

            def _human_loop() -> None:
                r"""Blocking loop that forwards human input to shell_exec."""
                nonlocal command_count, error_occurred
                try:
                    while True:
                        try:
                            # Clear, descriptive prompt for user input
                            user_cmd = input(f"🧑‍💻 [{id}]> ")
                            if (
                                user_cmd.strip()
                            ):  # Only count non-empty commands
                                command_count += 1
                        except EOFError:
                            # e.g. Ctrl_D / stdin closed, treat as exit.
                            break
                        except (KeyboardInterrupt, Exception) as e:
                            logger.warning(
                                f"Input error during human takeover: {e}"
                            )
                            error_occurred = True
                            break

                        if user_cmd.strip() in {"/exit", "exit", "quit"}:
                            break

                        try:
                            exec_result = self.shell_exec(id, user_cmd)
                            # Show the result immediately to the user
                            if exec_result.strip():
                                print(exec_result)
                            logger.info(
                                f"Human command executed: {user_cmd[:50]}..."
                            )
                            # Auto-exit after successful command
                            break
                        except Exception as e:
                            error_msg = f"Error executing command: {e}"
                            logger.error(f"Error executing human command: {e}")
                            print(error_msg)  # Show error to user immediately
                            self._update_terminal_output(f"{error_msg}\n")
                            error_occurred = True

                except Exception as e:
                    logger.error(f"Unexpected error in human loop: {e}")
                    error_occurred = True
                finally:
                    # Notify completion clearly
                    finish_msg = (
                        f"\n{'='*60}\n"
                        f"✅ Human assistance completed! "
                        f"Commands: {command_count}\n"
                        f"🤖 Returning control to CAMEL agent...\n"
                        f"{'='*60}\n"
                    )
                    print(finish_msg, flush=True)
                    self._update_terminal_output(finish_msg)
                    done_event.set()

            # Start interactive thread (non-daemon for proper cleanup)
            thread = threading.Thread(target=_human_loop, daemon=False)
            thread.start()

            # Block until human signals completion with timeout
            if done_event.wait(timeout=600):  # 10 minutes timeout
                thread.join(timeout=10)  # Give thread time to cleanup

                # Generate detailed status message
                status = "completed successfully"
                if error_occurred:
                    status = "completed with some errors"

                result_msg = (
                    f"Human assistance {status} for session '{id}'. "
                    f"Total commands executed: {command_count}. "
                    f"Working directory: {self.working_dir}"
                )
                logger.info(result_msg)
                return result_msg
            else:
                timeout_msg = (
                    f"Human takeover for session '{id}' timed out after 10 "
                    "minutes"
                )
                logger.warning(timeout_msg)
                return timeout_msg

        except Exception as e:
            error_msg = f"Error during human takeover for session '{id}': {e}"
            logger.error(error_msg)
            # Notify user of the error clearly
            error_banner = (
                f"\n{'='*60}\n"
                f"❌ Error in human takeover! Session: {id}\n"
                f"❗ {e}\n"
                f"{'='*60}\n"
            )
            print(error_banner, flush=True)
            return error_msg
        finally:
            # Always reset the flag
            self._human_takeover_active = False

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
            FunctionTool(self.ask_user_for_help),
        ]
