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
import subprocess
from typing import Any, Dict, List, Optional
import platform
import threading
import queue
from queue import Queue
import sys
import venv
import errno

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

logger = get_logger(__name__)


class TerminalToolkit(BaseToolkit):
    r"""A toolkit for terminal operations across multiple operating systems.

    This toolkit provides a set of functions for terminal operations such as
    searching for files by name or content, executing shell commands, and
    managing terminal sessions.

    Args:
        timeout (Optional[float]): The timeout for terminal operations.
        shell_sessions (Optional[Dict[str, Any]]): A dictionary to store
            shell session information. If None, an empty dictionary will be
            used.
        working_dir (Optional[str]): The working directory for operations.
            If specified, all execution and write operations will be restricted 
            to this directory. Read operations can access paths outside this directory.
            Default is None (no restriction).
        use_shell_mode (bool): Whether to use shell mode.
        clone_current_env (bool): Whether to clone the current environment.
        safe_mode (bool): Whether to enable safe mode.

    Note:
        Most functions are compatible with Unix-based systems (macOS, Linux).
        For Windows compatibility, additional implementation details are
        needed.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        shell_sessions: Optional[Dict[str, Any]] = None,
        working_dir: Optional[str] = None,
        need_terminal: bool = True,
        use_shell_mode: bool = True,  
        clone_current_env: bool = False, 
        safe_mode: bool = True,  
    ):
        super().__init__(timeout=timeout)
        self.shell_sessions = shell_sessions or {}
        self.os_type = platform.system()
        self.output_queue = Queue()
        self.agent_queue = Queue()
        self.terminal_ready = threading.Event()
        self.gui_thread = None
        self.safe_mode = safe_mode
        

        self.python_executable = sys.executable
        self.virtual_env = os.environ.get('VIRTUAL_ENV')
        self.use_shell_mode = use_shell_mode
        

        self.working_dir = None
        if working_dir is not None:
            if not os.path.exists(working_dir):
                os.makedirs(working_dir, exist_ok=True)
            self.working_dir = os.path.abspath(working_dir)
            self._update_terminal_output(f"Working directory set to: {self.working_dir}\n")
            if self.safe_mode:
                self._update_terminal_output("Safe mode enabled: Write operations can only be performed within the working directory\n")
            

            if clone_current_env:
                self.cloned_env_path = os.path.join(self.working_dir, ".venv")
                self._clone_current_environment()
            else:
                self.cloned_env_path = None


        if need_terminal:
            self.gui_thread = threading.Thread(target=self._create_terminal, daemon=True)
            self.gui_thread.start()

            self.terminal_ready.wait(timeout=5)

        self.safe_mode = safe_mode

    def _clone_current_environment(self):
        """Clone the current Python environment to the working directory"""
        try:
            if os.path.exists(self.cloned_env_path):
                self._update_terminal_output(f"Using existing environment: {self.cloned_env_path}\n")
                return
                
            self._update_terminal_output(f"Cloning current Python environment to: {self.cloned_env_path}...\n")
            

            venv.create(self.cloned_env_path, with_pip=True)
            

            if self.os_type == 'Windows':
                pip_path = os.path.join(self.cloned_env_path, "Scripts", "pip.exe")
                python_path = os.path.join(self.cloned_env_path, "Scripts", "python.exe")
            else:
                pip_path = os.path.join(self.cloned_env_path, "bin", "pip")
                python_path = os.path.join(self.cloned_env_path, "bin", "python")
            

            result = subprocess.run(
                [self.python_executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                packages = result.stdout.strip()
                if packages:

                    req_file = os.path.join(self.working_dir, "requirements.txt")
                    with open(req_file, "w") as f:
                        f.write(packages)

                    self._update_terminal_output("Installing dependencies, this may take a few minutes...\n")
                    install_result = subprocess.run(
                        [pip_path, "install", "-r", req_file],
                        capture_output=True,
                        text=True
                    )
                    
                    if install_result.returncode == 0:
                        self._update_terminal_output("Environment cloning completed!\n")
                    else:
                        self._update_terminal_output(f"Error installing packages: {install_result.stderr}\n")
                else:
                    self._update_terminal_output("No packages installed in the current environment, created an empty environment\n")
            else:
                self._update_terminal_output(f"Failed to get the package list of the current environment: {result.stderr}\n")
                
        except Exception as e:
            self._update_terminal_output(f"Failed to clone environment: {str(e)}\n")
            logger.error(f"Failed to clone environment: {e}")

    def _create_terminal(self):
        """Create terminal interface"""
        try:
            import tkinter as tk
            from tkinter import ttk, scrolledtext
            
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
                insertbackground='white'  # Cursor color
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
        """Update terminal output and send to agent"""
        try:
            if hasattr(self, 'root') and self.root:
                self.output_queue.put(output)
                # Also send to agent
                self.agent_queue.put(output)
        except Exception as e:
            logger.error(f"Failed to update terminal output: {e}")

    def _is_path_within_working_dir(self, path: str) -> bool:
        """Check if the path is within the working directory.
        
        Args:
            path (str): The path to check
            
        Returns:
            bool: Returns True if the path is within the working directory or if the working directory is not set, otherwise returns False
        """
        if self.working_dir is None:
            return True
            
        abs_path = os.path.abspath(path)
        return abs_path.startswith(self.working_dir)
    
    def _enforce_working_dir_for_execution(self, path: str) -> Optional[str]:
        """Enforce working directory restrictions, return error message if execution path is not within the working directory.
        
        Args:
            path (str): The path to be used for executing operations
            
        Returns:
            Optional[str]: Returns error message if the path is not within the working directory, otherwise returns None
        """
        if not self._is_path_within_working_dir(path):
            return f"Operation restriction: Execution path {path} must be within working directory {self.working_dir}"
        return None

    def _copy_external_file_to_workdir(self, external_file: str) -> Optional[str]:
        """Copy external file to working directory.
        
        Args:
            external_file (str): The path of the external file
            
        Returns:
            Optional[str]: New path after copying to the working directory, returns None on failure
        """
        if not self.working_dir:
            return None
        
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
        # This is a read operation, allowing access to files outside the working directory
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
        # This is a read operation, allowing access to directories outside the working directory
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
            command.extend(["dir", "/s", "/b", os.path.join(path, pattern)])

        try:
            result = subprocess.run(
                command, check=False, capture_output=True, text=True,shell=True
            )
            return result.stdout.strip()
        except subprocess.SubprocessError as e:
            logger.error(f"Error finding files by name: {e}")
            return f"Error: {e!s}"

    def _sanitize_command(self, command: str, exec_dir: str) -> tuple:
        """
        Check and modify command to ensure safety
        
        Returns: (is safe, modified command or error message)
        """
        if not self.safe_mode:
            return True, command
            
        # Split command for analysis
        parts = []
        current = ""
        in_quotes = False
        quote_char = None
        
        # Parse command, handling quotes
        for char in command:
            if char in ['"', "'"]:
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
                    quote_char = None
                current += char
            elif char.isspace() and not in_quotes:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
                
        if current:
            parts.append(current)
            
        if not parts:
            return False, "Empty command"
            
        # Get base command
        base_cmd = parts[0].lower()
        
        # Handle special commands
        if base_cmd in ['cd', 'chdir']:
            # Check if cd command attempts to leave the working directory
            if len(parts) > 1:
                target_dir = parts[1].strip('"\'')
                if target_dir.startswith('/') or target_dir.startswith('\\') or ':' in target_dir:
                    # Absolute path
                    abs_path = os.path.abspath(target_dir)
                else:
                    # Relative path
                    abs_path = os.path.abspath(os.path.join(exec_dir, target_dir))
                    
                if not self._is_path_within_working_dir(abs_path):
                    return False, f"Safety restriction: Cannot change to directory outside of working directory {self.working_dir}"
            
        # Check file operation commands
        elif base_cmd in ['rm', 'del', 'rmdir', 'rd', 'deltree', 'erase', 'unlink', 
                         'shred', 'srm', 'wipe', 'remove']:
            # Check targets of delete commands
            for i, part in enumerate(parts[1:], 1):
                if part.startswith('-') or part.startswith('/'):  # Skip options
                    continue
                    
                target = part.strip('"\'')
                if target.startswith('/') or target.startswith('\\') or ':' in target:
                    # Absolute path
                    abs_path = os.path.abspath(target)
                else:
                    # Relative path
                    abs_path = os.path.abspath(os.path.join(exec_dir, target))
                    
                if not self._is_path_within_working_dir(abs_path):
                    return False, f"Safety restriction: Cannot delete files outside of working directory {self.working_dir}"
                    
        # Check write/modify commands
        elif base_cmd in ['touch', 'mkdir', 'md', 'echo', 'cat', 'cp', 'copy', 'mv', 'move',
                         'rename', 'ren', 'write', 'output']:
            # Check for redirection symbols
            full_cmd = command.lower()
            if '>' in full_cmd:
                # Find the file path after redirection
                redirect_parts = command.split('>')
                if len(redirect_parts) > 1:
                    output_file = redirect_parts[1].strip().split()[0].strip('"\'')
                    if output_file.startswith('/') or output_file.startswith('\\') or ':' in output_file:
                        # Absolute path
                        abs_path = os.path.abspath(output_file)
                    else:
                        # Relative path
                        abs_path = os.path.abspath(os.path.join(exec_dir, output_file))
                        
                    if not self._is_path_within_working_dir(abs_path):
                        return False, f"Safety restriction: Cannot write to files outside of working directory {self.working_dir}"
            
            # For cp/mv commands, check target paths
            if base_cmd in ['cp', 'copy', 'mv', 'move']:
                # Simple handling, assuming the last parameter is the target
                if len(parts) > 2:
                    target = parts[-1].strip('"\'')
                    if target.startswith('/') or target.startswith('\\') or ':' in target:
                        # Absolute path
                        abs_path = os.path.abspath(target)
                    else:
                        # Relative path
                        abs_path = os.path.abspath(os.path.join(exec_dir, target))
                        
                    if not self._is_path_within_working_dir(abs_path):
                        return False, f"Safety restriction: Cannot write to files outside of working directory {self.working_dir}"
                        
        # Check dangerous commands
        elif base_cmd in ['sudo', 'su', 'chmod', 'chown', 'chgrp', 'passwd', 'mkfs', 'fdisk',
                         'dd', 'shutdown', 'reboot', 'halt', 'poweroff', 'init']:
            return False, f"Safety restriction: Command '{base_cmd}' may affect system security and is prohibited"
            
        # Check network commands
        elif base_cmd in ['ssh', 'telnet', 'ftp', 'sftp', 'nc', 'netcat']:
            return False, f"Safety restriction: Network command '{base_cmd}' is prohibited"
            
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
            if target.startswith('/') or target.startswith('\\') or ':' in target:
                # Absolute path
                abs_target = os.path.abspath(target)
            else:
                # Relative path
                abs_target = os.path.abspath(os.path.join(exec_dir, target))
                
            if not self._is_path_within_working_dir(abs_target):
                return False, f"Safety restriction: Target file must be within working directory {self.working_dir}"
                
            # Replace with safe copy command
            if self.os_type == 'Windows':
                return True, f"copy \"{source}\" \"{abs_target}\""
            else:
                return True, f"cp \"{source}\" \"{abs_target}\""
                
        return True, command

    def shell_exec(self, id: str, exec_dir: str, command: str) -> str:
        r"""Execute commands in a specified shell session.

        Args:
            id (str): Unique identifier of the target shell session.
            exec_dir (str): Working directory for command execution (must use
                absolute path).
            command (str): Shell command to execute.

        Returns:
            str: Output of the command execution or error message.
        """
        # Command execution must be within the working directory
        if self.working_dir:
            error_msg = self._enforce_working_dir_for_execution(exec_dir)
            if error_msg:
                return error_msg
                
        if not os.path.isabs(exec_dir):
            return f"exec_dir must be an absolute path: {exec_dir}"

        if not os.path.exists(exec_dir):
            return f"Directory not found: {exec_dir}"

        # Check and modify command to ensure safety
        is_safe, sanitized_command = self._sanitize_command(command, exec_dir)
        if not is_safe:
            return sanitized_command  # Return error message
            
        # Use modified safe command
        command = sanitized_command

        # If the session doesn't exist, create a new one
        if id not in self.shell_sessions:
            self.shell_sessions[id] = {
                "process": None,
                "output": "",
                "running": False,
            }

        try:
            # Display command in terminal
            self._update_terminal_output(f"\n$ {command}\n")
            
            # Set environment variables
            env = os.environ.copy()
            
            # If using cloned environment
            if self.cloned_env_path and os.path.exists(self.cloned_env_path):
                if self.os_type == 'Windows':
                    python_exe = os.path.join(self.cloned_env_path, "Scripts", "python.exe")
                    env['PATH'] = f"{os.path.join(self.cloned_env_path, 'Scripts')};{env['PATH']}"
                else:
                    python_exe = os.path.join(self.cloned_env_path, "bin", "python")
                    env['PATH'] = f"{os.path.join(self.cloned_env_path, 'bin')}:{env['PATH']}"
                
                env['VIRTUAL_ENV'] = self.cloned_env_path
            else:
                python_exe = self.python_executable
                if self.virtual_env:
                    env['VIRTUAL_ENV'] = self.virtual_env
                    if self.os_type == 'Windows':
                        env['PATH'] = f"{os.path.join(self.virtual_env, 'Scripts')};{env['PATH']}"
                    else:
                        env['PATH'] = f"{os.path.join(self.virtual_env, 'bin')}:{env['PATH']}"
            
            # Handle Python commands
            if command.startswith('python ') and not self.use_shell_mode:
                command = command.replace('python ', f'"{python_exe}" ')
            
            if self.os_type in ['Darwin', 'Linux']:
                # Unix system implementation
                import pty
                import fcntl
                
                # Create pseudo terminal
                master_fd, slave_fd = pty.openpty()
                # Set to non-blocking mode
                flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
                fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
                
                # Determine the shell command to execute
                if self.use_shell_mode:
                    # In shell mode, execute command directly
                    shell_cmd = command
                else:
                    # In Python mode, check if Python interpreter needs to be replaced
                    if command.startswith('python '):
                        shell_cmd = command.replace('python ', f'"{python_exe}" ')
                    else:
                        shell_cmd = command
                
                process = subprocess.Popen(
                    shell_cmd,
                    shell=True,
                    cwd=exec_dir,
                    stdin=slave_fd,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    env=env,
                    preexec_fn=os.setsid
                )
                
                os.close(slave_fd)  # Close child process end
                
                # Create read output thread
                def _read_output():
                    """Read output from master_fd"""
                    try:
                        while True:
                            try:
                                data = os.read(master_fd, 1024)
                                if data:
                                    output = data.decode('utf-8', errors='replace')
                                    self._update_terminal_output(output)
                            except OSError as e:
                                if e.errno != errno.EAGAIN:  # Ignore errors during non-blocking read
                                    raise
                                time.sleep(0.1)
                            if process.poll() is not None:  # Process ended
                                break
                    except Exception as e:
                        logger.error(f"Error reading output: {e}")
                    finally:
                        os.close(master_fd)
                
                # Start read output thread
                threading.Thread(target=_read_output, daemon=True).start()
                
                self.shell_sessions[id] = {
                    "process": process,
                    "master_fd": master_fd,
                    "output": "",
                    "running": True,
                    "command": command
                }
                
            else:  # Windows
                # Determine the shell command to execute
                if self.use_shell_mode:
                    # In shell mode, execute command using cmd.exe
                    shell_cmd = command
                    shell = True
                else:
                    # In Python mode, check if Python interpreter needs to be replaced
                    if command.startswith('python '):
                        shell_cmd = command.replace('python ', f'"{python_exe}" ')
                    else:
                        shell_cmd = command
                    shell = True
                
                # Create process
                process = subprocess.Popen(
                    shell_cmd,
                    shell=shell,
                    cwd=exec_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env
                )
                
                # Check for ModuleNotFoundError
                error_output = process.stderr.readline() if process.stderr else ""
                if error_output and "ModuleNotFoundError: No module named" in error_output:
                    # Extract missing module name
                    import re
                    module_match = re.search(r"No module named '(\w+)'", error_output)
                    if module_match:
                        missing_module = module_match.group(1)
                        install_msg = f"\nDetected missing module: {missing_module}, installing automatically...\n"
                        self._update_terminal_output(install_msg)
                        
                        # Determine pip path
                        if self.cloned_env_path:
                            if self.os_type == 'Windows':
                                pip_cmd = os.path.join(self.cloned_env_path, "Scripts", "pip.exe")
                            else:
                                pip_cmd = os.path.join(self.cloned_env_path, "bin", "pip")
                        else:
                            pip_cmd = os.path.join(os.path.dirname(python_exe), 'pip')
                            if self.os_type == 'Windows':
                                pip_cmd += '.exe'
                        
                        # Install missing module
                        pip_process = subprocess.run(
                            f'"{pip_cmd}" install {missing_module}',
                            shell=True,
                            capture_output=True,
                            text=True,
                            env=env
                        )
                        
                        if pip_process.returncode == 0:
                            success_msg = f"Successfully installed {missing_module}\n"
                            self._update_terminal_output(success_msg)
                            # Re-run original command
                            process = subprocess.Popen(
                                shell_cmd,
                                shell=shell,
                                cwd=exec_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdin=subprocess.PIPE,
                                text=True,
                                bufsize=1,
                                universal_newlines=True,
                                env=env
                            )
                        else:
                            error_msg = f"Failed to install {missing_module}: {pip_process.stderr}\n"
                            self._update_terminal_output(error_msg)
                            return error_msg
                    else:
                        # If not a module missing error, output original error message
                        self._update_terminal_output(error_output)
                
                def _read_output(pipe, prefix=""):
                    try:
                        for line in iter(pipe.readline, ''):
                            self._update_terminal_output(prefix + line)
                    except Exception as e:
                        logger.error(f"Error reading output: {e}")
                    finally:
                        pipe.close()
                
                # Start read output thread
                threading.Thread(
                    target=_read_output,
                    args=(process.stdout,),
                    daemon=True
                ).start()
                
                threading.Thread(
                    target=_read_output,
                    args=(process.stderr, "Error: "),
                    daemon=True
                ).start()
                
                self.shell_sessions[id] = {
                    "process": process,
                    "output": "",
                    "running": True,
                    "command": command
                }
            
            # Wait for a while to collect initial output
            import time
            time.sleep(0.5)
            
            # Collect all output from agent queue
            collected_output = ""
            try:
                while True:
                    output = self.agent_queue.get_nowait()
                    collected_output += output
            except queue.Empty:
                pass
            
            # Return session information and initial output
            env_info = "Cloned environment" if self.cloned_env_path else "Current environment"
            mode_info = "Shell mode" if self.use_shell_mode else "Python mode"
            return collected_output or f"Terminal session '{id}' started in {env_info}, {mode_info}."
            
        except Exception as e:
            error_msg = f"Error creating terminal session: {e}"
            self._update_terminal_output(f"\nError: {error_msg}\n")
            logger.error(error_msg)
            return f"Error: {e!s}"

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

        if not session["running"]:
            return f"Process in session '{id}' is not running"

        try:
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
                session["output"] += f"\nErrors:\n{stderr_str}"

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
