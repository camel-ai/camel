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
import select
import shlex
import subprocess
import threading
import time
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)

# Try to import docker, but don't make it a hard requirement
try:
    import docker
    from docker.errors import APIError, NotFound
    from docker.models.containers import Container
except ImportError:
    docker = None
    NotFound = None
    APIError = None
    Container = None


@MCPServer()
class TerminalToolkit(BaseToolkit):
    r"""Toolkit to execute and interact with terminal commands for agents.

    Supports both local execution and an optional Docker backend. For local
    execution, `working_directory` acts as a sandbox boundary. For Docker,
    commands run inside the specified container.

    Args:
        timeout (Optional[float]): Default timeout in seconds for blocking
            commands. (default: :obj:`20.0`)
        shell_sessions (Optional[Dict[str, Any]]): Internal session mapping
            used for non-blocking processes. (default: :obj:`None`)
        working_directory (Optional[str]): Base directory for all operations.
            For local backend, this is the sandbox root. (default: :obj:`None`)
        use_docker_backend (bool): If :obj:`True`, execute commands in a Docker
            container instead of locally. (default: :obj:`False`)
        docker_container_name (Optional[str]): Docker container name or ID
            when using the Docker backend. (default: :obj:`None`)
        session_logs_dir (Optional[str]): Directory to store session logs.
            Defaults to ``<working_directory>/terminal_logs``.
        safe_mode (bool): Whether to restrict or sanitize risky operations in
            local mode. (default: :obj:`True`)
        need_terminal (bool): Whether an interactive terminal is required.
            (default: :obj:`False`)
    """

    def __init__(
        self,
        timeout: Optional[float] = 20.0,
        shell_sessions: Optional[Dict[str, Any]] = None,
        working_directory: Optional[str] = None,
        use_docker_backend: bool = False,
        docker_container_name: Optional[str] = None,
        session_logs_dir: Optional[str] = None,
        safe_mode: bool = True,
        need_terminal: bool = False,
    ):
        self.use_docker_backend = use_docker_backend
        self.timeout = timeout
        self.shell_sessions: Dict[str, Dict[str, Any]] = {}
        self.working_dir = (
            os.path.abspath(working_directory) if working_directory else None
        )
        self.safe_mode = safe_mode
        self.need_terminal = need_terminal

        atexit.register(self.__del__)

        self.log_dir = os.path.abspath(
            session_logs_dir or os.path.join(self.working_dir, "terminal_logs")
        )
        self.blocking_log_file = os.path.join(
            self.log_dir, "blocking_commands.log"
        )

        os.makedirs(self.log_dir, exist_ok=True)

        if self.use_docker_backend:
            if docker is None:
                raise ImportError(
                    "The 'docker' library is required to use the Docker backend. "
                    "Please install it with 'pip install docker'."
                )
            if not docker_container_name:
                raise ValueError(
                    "docker_container_name must be provided when using Docker backend."
                )
            try:
                # APIClient is used for operations that need a timeout, like exec_start
                self.docker_api_client = docker.APIClient(
                    base_url='unix://var/run/docker.sock', timeout=self.timeout
                )
                # The standard client is for higher-level, convenient operations
                self.docker_client = docker.from_env()
                self.container = self.docker_client.containers.get(
                    docker_container_name
                )
                logger.info(
                    f"Successfully attached to Docker container '{docker_container_name}'."
                )
            except NotFound:
                raise RuntimeError(
                    f"Docker container '{docker_container_name}' not found."
                )
            except APIError as e:
                raise RuntimeError(f"Failed to connect to Docker daemon: {e}")

    def _sanitize_command(self, command: str) -> tuple[bool, str]:
        """A simple command sanitizer for the local backend."""
        if self.use_docker_backend:
            return True, command  # No sanitization needed for docker

        parts = shlex.split(command)
        if not parts:
            return False, "Empty command is not allowed."
        base_cmd = parts[0].lower()

        # Block dangerous commands
        dangerous_commands = [
            'sudo',
            'su',
            'rm',
            'mv',
            'chmod',
            'chown',
            'reboot',
            'shutdown',
        ]
        if base_cmd in dangerous_commands:
            # A simple check for `rm -f` or `rm -rf`
            if base_cmd == 'rm' and any(
                arg in command for arg in ['-f', '-rf', '-fr']
            ):
                return (
                    False,
                    f"Command '{base_cmd}' with forceful options is blocked for safety.",
                )
            if base_cmd != 'rm':
                return False, f"Command '{base_cmd}' is blocked for safety."

        # Prevent changing directory outside the workspace
        if base_cmd == 'cd' and len(parts) > 1:
            target_dir = os.path.abspath(
                os.path.join(self.working_dir, parts[1])
            )
            if not target_dir.startswith(self.working_dir):
                return False, "Cannot 'cd' outside of the working directory."

        return True, command

    def _start_output_reader_thread(self, session_id: str):
        """Starts a thread to read stdout from a non-blocking process."""
        session = self.shell_sessions[session_id]

        def reader():
            try:
                if session["backend"] == "local":
                    # For local processes, read line by line from stdout
                    for line in iter(session["process"].stdout.readline, ''):
                        session["output_stream"].put(line)
                        with open(
                            session["log_file"], "a", encoding="utf-8"
                        ) as f:
                            f.write(line)
                    session["process"].stdout.close()
                elif session["backend"] == "docker":
                    # For Docker, read from the raw socket
                    socket = session["process"]._sock
                    while True:
                        # Check if the socket is still open before reading
                        if socket.fileno() == -1:
                            break
                        ready, _, _ = select.select([socket], [], [], 0.1)
                        if ready:
                            data = socket.recv(4096)
                            if not data:
                                break
                            decoded_data = data.decode(
                                'utf-8', errors='ignore'
                            )
                            session["output_stream"].put(decoded_data)
                            with open(
                                session["log_file"], "a", encoding="utf-8"
                            ) as f:
                                f.write(decoded_data)
                        # Check if the process is still running
                        if not self.docker_api_client.exec_inspect(
                            session["exec_id"]
                        )['Running']:
                            break
            except Exception:
                # Thread will exit if process dies or socket closes
                pass
            finally:
                session["running"] = False

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()

    def _collect_output_until_idle(
        self,
        id: str,
        idle_duration: float = 0.5,
        check_interval: float = 0.1,
        max_wait: float = 5.0,
    ) -> str:
        """
        Collects output from a session until it's idle or a max wait time is reached.

        Args:
            id (str): The session ID.
            idle_duration (float): How long the stream must be empty to be considered idle.
            check_interval (float): The time to sleep between checks.
            max_wait (float): The maximum total time to wait for the process to go idle.

        Returns:
            str: The collected output. If max_wait is reached while the process is
                 still outputting, a warning is appended.
        """
        if id not in self.shell_sessions:
            return f"Error: No session found with ID '{id}'."

        output_parts = []
        idle_time = 0
        start_time = time.time()

        while time.time() - start_time < max_wait:
            new_output = self.shell_view(id)

            # Check for terminal state messages from shell_view
            if "--- SESSION TERMINATED ---" in new_output:
                # Append the final output before the termination message
                final_part = new_output.replace(
                    "--- SESSION TERMINATED ---", ""
                ).strip()
                if final_part:
                    output_parts.append(final_part)
                # Session is dead, return what we have plus the message
                return "".join(output_parts) + "\n--- SESSION TERMINATED ---"

            if new_output.startswith("Error: No session found"):
                return new_output

            if new_output:
                output_parts.append(new_output)
                idle_time = 0  # Reset idle timer
            else:
                idle_time += check_interval
                if idle_time >= idle_duration:
                    # Process is idle, success
                    return "".join(output_parts)
            time.sleep(check_interval)

        # If we exit the loop, it means max_wait was reached.
        # Check one last time for any final output.
        final_output = self.shell_view(id)
        if final_output:
            output_parts.append(final_output)

        warning_message = (
            "\n--- WARNING: Process is still actively outputting after max wait time. "
            "Consider using shell_wait() before sending the next command. ---"
        )
        return "".join(output_parts) + warning_message

    def shell_exec(self, id: str, command: str, block: bool = True) -> str:
        r"""Execute a shell command either blocking or non-blocking.

        Args:
            id (str): Session identifier. For non-blocking mode, identifies
                the interactive session.
            command (str): The command to execute.
            block (bool): If :obj:`True`, run synchronously and return full
                output; otherwise start a background session. (default:
                :obj:`True`)

        Returns:
            str: Blocking mode returns combined stdout and stderr. Non-blocking
                mode returns a message with the session ID and initial output.
        """
        is_safe, message = self._sanitize_command(command)
        if not is_safe:
            return f"Error: {message}"
        command = message
        if self.use_docker_backend:
            # For Docker, we always run commands in a shell to support complex commands
            command = f'bash -c "{command}"'

        session_id = id

        if block:
            # --- BLOCKING EXECUTION ---
            log_entry = f"--- Executing blocking command at {time.ctime()} ---\n> {command}\n"
            output = ""
            try:
                if not self.use_docker_backend:
                    # LOCAL BLOCKING
                    result = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        shell=True,
                        timeout=self.timeout,
                        cwd=self.working_dir,
                        encoding="utf-8",
                    )
                    stdout = result.stdout or ""
                    stderr = result.stderr or ""
                    output = stdout + (
                        f"\nSTDERR:\n{stderr}" if stderr else ""
                    )
                else:
                    # DOCKER BLOCKING
                    exec_instance = self.docker_api_client.exec_create(
                        self.container.id, command, workdir=self.working_dir
                    )
                    exec_output = self.docker_api_client.exec_start(
                        exec_instance['Id']
                    )
                    output = exec_output.decode('utf-8', errors='ignore')

                log_entry += f"--- Output ---\n{output}\n"
                return output
            except subprocess.TimeoutExpired:
                error_msg = (
                    f"Error: Command timed out after {self.timeout} seconds."
                )
                log_entry += f"--- Error ---\n{error_msg}\n"
                return error_msg
            except Exception as e:
                if "Read timed out" in str(e):
                    error_msg = f"Error: Command timed out after {self.timeout} seconds."
                else:
                    error_msg = f"Error executing command: {e}"
                log_entry += f"--- Error ---\n{error_msg}\n"
                return error_msg
            finally:
                with open(self.blocking_log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
        else:
            # --- NON-BLOCKING EXECUTION ---
            session_log_file = os.path.join(
                self.log_dir, f"session_{session_id}.log"
            )

            with open(session_log_file, "a", encoding="utf-8") as f:
                f.write(
                    f"--- Starting non-blocking session at {time.ctime()} ---\n> {command}\n"
                )

            self.shell_sessions[session_id] = {
                "id": session_id,
                "process": None,
                "output_stream": Queue(),
                "command_history": [command],
                "running": True,
                "log_file": session_log_file,
                "backend": "docker" if self.use_docker_backend else "local",
            }

            try:
                if not self.use_docker_backend:
                    process = subprocess.Popen(
                        command,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        shell=True,
                        text=True,
                        cwd=self.working_dir,
                        encoding="utf-8",
                    )
                    self.shell_sessions[session_id]["process"] = process
                else:
                    exec_instance = self.docker_api_client.exec_create(
                        self.container.id,
                        command,
                        stdin=True,
                        tty=True,
                        workdir=self.working_dir,
                    )
                    exec_id = exec_instance['Id']
                    exec_socket = self.docker_api_client.exec_start(
                        exec_id, tty=True, stream=True, socket=True
                    )
                    self.shell_sessions[session_id]["process"] = exec_socket
                    self.shell_sessions[session_id]["exec_id"] = exec_id

                self._start_output_reader_thread(session_id)

                # time.sleep(0.1)
                initial_output = self._collect_output_until_idle(session_id)

                return f"Session started with ID: {session_id}\n\n[Initial Output]:\n{initial_output}"

            except Exception as e:
                self.shell_sessions[session_id]["running"] = False
                error_msg = f"Error starting non-blocking command: {e}"
                with open(session_log_file, "a", encoding="utf-8") as f:
                    f.write(f"--- Error ---\n{error_msg}\n")
                return error_msg

    def shell_write_to_process(self, id: str, command: str) -> str:
        r"""Send input to a running non-blocking session and return output.

        A trailing newline is appended automatically to the input.

        Args:
            id (str): The unique non-blocking session ID.
            command (str): Text to write to the process's standard input.

        Returns:
            str: Output produced after the command is processed.
        """
        if (
            id not in self.shell_sessions
            or not self.shell_sessions[id]["running"]
        ):
            return (
                f"Error: No active non-blocking session found with ID '{id}'."
            )

        # Flush any lingering output from previous commands.
        self._collect_output_until_idle(id, idle_duration=0.3, max_wait=2.0)

        session = self.shell_sessions[id]
        session["command_history"].append(command)

        # Log command to the raw log file
        with open(session["log_file"], "a", encoding="utf-8") as f:
            f.write(f"> {command}\n")

        try:
            if session["backend"] == "local":
                process = session["process"]
                process.stdin.write(command + '\n')
                process.stdin.flush()
            else:  # docker
                socket = session["process"]._sock
                socket.sendall((command + '\n').encode('utf-8'))

            # Wait for and collect the new output
            output = self._collect_output_until_idle(id)

            return output

        except Exception as e:
            return f"Error writing to session '{id}': {e}"

    def shell_view(self, id: str) -> str:
        r"""Retrieve any new output from a non-blocking session.

        If the process has terminated, drain the remaining output and append a
        termination message.

        Args:
            id (str): The unique non-blocking session ID.

        Returns:
            str: Newly available output; empty string if none.
        """
        if id not in self.shell_sessions:
            return f"Error: No session found with ID '{id}'."

        session = self.shell_sessions[id]

        # If session is terminated, drain the queue and return with a status message.
        if not session["running"]:
            final_output = []
            try:
                while True:
                    final_output.append(session["output_stream"].get_nowait())
            except Empty:
                pass
            return "".join(final_output) + "\n--- SESSION TERMINATED ---"

        # Otherwise, just drain the queue for a live session.
        output = []
        try:
            while True:
                output.append(session["output_stream"].get_nowait())
        except Empty:
            pass

        return "".join(output)

    def shell_wait(self, id: str, wait_seconds: float = 5.0) -> str:
        r"""Wait for additional output or termination for a session.

        Args:
            id (str): The unique non-blocking session ID.
            wait_seconds (float): Maximum seconds to wait. (default:
                :obj:`5.0`)

        Returns:
            str: All output collected during the wait window.
        """
        if id not in self.shell_sessions:
            return f"Error: No session found with ID '{id}'."

        session = self.shell_sessions[id]
        if not session["running"]:
            return "Session is no longer running. Use shell_view to get final output."

        output_collected = []
        end_time = time.time() + wait_seconds
        while time.time() < end_time and session["running"]:
            new_output = self.shell_view(id)
            if new_output:
                output_collected.append(new_output)
            time.sleep(0.2)

        return "".join(output_collected)

    def shell_kill_process(self, id: str) -> str:
        r"""Terminate a running non-blocking process.

        Args:
            id (str): The unique non-blocking session ID to kill.

        Returns:
            str: Confirmation message upon termination.
        """
        if (
            id not in self.shell_sessions
            or not self.shell_sessions[id]["running"]
        ):
            return (
                f"Error: No active non-blocking session found with ID '{id}'."
            )

        session = self.shell_sessions[id]
        try:
            if session["backend"] == "local":
                session["process"].terminate()
                time.sleep(0.5)
                if session["process"].poll() is None:
                    session["process"].kill()
            else:  # docker
                # Docker exec processes stop when the socket is closed.
                session["process"].close()

            session["running"] = False
            return f"Process in session '{id}' has been terminated."
        except Exception as e:
            return f"Error killing process in session '{id}': {e}"

    def shell_ask_user_for_help(self, id: str, prompt: str) -> str:
        r"""Pause and ask a human for help with an interactive session.

        Displays the latest output and the prompt to the user, waits for
        input, sends it to the session, and returns the resulting output.

        Args:
            id (str): The interactive session ID that requires input.
            prompt (str): Instruction or question to present to the user.

        Returns:
            str: Output from the shell session after user's input executes.
        """
        if id not in self.shell_sessions:
            return f"Error: No session found with ID '{id}'."

        # Get the latest output to show the user the current state
        last_output = self._collect_output_until_idle(id)

        print("\n" + "=" * 60)
        print("🤖 LLM Agent needs your help!")
        print(f"SESSION ID: {id}")
        print(f"PROMPT: {prompt}")
        print("--- LAST OUTPUT ---")
        print(last_output.strip())
        print("-------------------")

        try:
            user_input = input("Your input: ")
        except EOFError:
            user_input = ""

        # This function will now wait and return the output
        return self.shell_write_to_process(id, user_input)

    def __del__(self):
        # Clean up any running non-blocking sessions
        for session_id in list(self.shell_sessions.keys()):
            if self.shell_sessions.get(session_id, {}).get("running", False):
                self.shell_kill_process(session_id)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the
                functions in the toolkit.
        """
        return [
            FunctionTool(self.shell_exec),
            FunctionTool(self.shell_view),
            FunctionTool(self.shell_wait),
            FunctionTool(self.shell_write_to_process),
            FunctionTool(self.shell_kill_process),
            FunctionTool(self.shell_ask_user_for_help),
        ]
