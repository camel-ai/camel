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
import select
import subprocess
import sys
import threading
import time
from queue import Empty, Queue
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.toolkits.terminal_toolkit.utils import (
    check_nodejs_availability,
    clone_current_environment,
    ensure_uv_available,
    sanitize_command,
    setup_initial_env_with_uv,
    setup_initial_env_with_venv,
)
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


def _to_plain(text: str) -> str:
    r"""Convert ANSI text to plain text using rich if available."""
    try:
        from rich.text import Text as _RichText

        return _RichText.from_ansi(text).plain
    except Exception:
        return text


@MCPServer()
class TerminalToolkit(BaseToolkit):
    r"""A toolkit for LLM agents to execute and interact with terminal commands
    in either a local or a sandboxed Docker environment.

    Args:
    use_docker_backend (bool): If True, all commands are executed in a
        Docker container. Defaults to False.
    docker_container_name (Optional[str]): The name of the Docker
        container to use. Required if use_docker_backend is True.
    working_dir (str): The base directory for all operations.
        For the local backend, this acts as a security sandbox.
    session_logs_dir (Optional[str]): The directory to store session
        logs. Defaults to a 'terminal_logs' subfolder in the
        working_dir.
    timeout (int): The default timeout in seconds for blocking
        commands. Defaults to 60.
    """

    def __init__(
        self,
        timeout: Optional[float] = 20.0,
        working_directory: Optional[str] = None,
        use_docker_backend: bool = False,
        docker_container_name: Optional[str] = None,
        session_logs_dir: Optional[str] = None,
        safe_mode: bool = True,
        allowed_commands: Optional[List[str]] = None,
        clone_current_env: bool = False,
    ):
        self.use_docker_backend = use_docker_backend
        self.timeout = timeout
        self.shell_sessions: Dict[str, Dict[str, Any]] = {}
        # Thread-safe guard for concurrent access to
        # shell_sessions and session state
        self._session_lock = threading.RLock()
        if working_directory:
            self.working_dir = os.path.abspath(working_directory)
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                self.working_dir = os.path.abspath(camel_workdir)
            else:
                self.working_dir = os.path.abspath("./workspace")

        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir, exist_ok=True)
        self.safe_mode = safe_mode

        # Initialize whitelist of allowed commands if provided
        self.allowed_commands = (
            set(allowed_commands) if allowed_commands else None
        )

        # Environment management attributes
        self.clone_current_env = clone_current_env
        self.cloned_env_path: Optional[str] = None
        self.initial_env_path: Optional[str] = None
        self.python_executable = sys.executable

        atexit.register(self.__del__)

        self.log_dir = os.path.abspath(
            session_logs_dir or os.path.join(self.working_dir, "terminal_logs")
        )
        self.blocking_log_file = os.path.join(
            self.log_dir, "blocking_commands.log"
        )
        self.os_type = platform.system()

        os.makedirs(self.log_dir, exist_ok=True)

        # Clean the file in terminal_logs folder
        for file in os.listdir(self.log_dir):
            if file.endswith(".log"):
                os.remove(os.path.join(self.log_dir, file))

        if self.use_docker_backend:
            if docker is None:
                raise ImportError(
                    "The 'docker' library is required to use the "
                    "Docker backend. Please install it with "
                    "'pip install docker'."
                )
            if not docker_container_name:
                raise ValueError(
                    "docker_container_name must be "
                    "provided when using Docker backend."
                )
            try:
                # APIClient is used for operations that need a timeout,
                # like exec_start
                self.docker_api_client = docker.APIClient(
                    base_url='unix://var/run/docker.sock', timeout=self.timeout
                )
                self.docker_client = docker.from_env()
                self.container = self.docker_client.containers.get(
                    docker_container_name
                )
                logger.info(
                    f"Successfully attached to Docker container "
                    f"'{docker_container_name}'."
                )
            except NotFound:
                raise RuntimeError(
                    f"Docker container '{docker_container_name}' not found."
                )
            except APIError as e:
                raise RuntimeError(f"Failed to connect to Docker daemon: {e}")

        # Set up environments (only for local backend)
        if not self.use_docker_backend:
            if self.clone_current_env:
                self._setup_cloned_environment()
            else:
                # Default: set up initial environment with Python 3.10
                self._setup_initial_environment()
        elif self.clone_current_env:
            logger.info(
                "[ENV CLONE] Skipping environment setup for Docker backend "
                "- container is already isolated"
            )

    def _setup_cloned_environment(self):
        r"""Set up a cloned Python environment."""
        self.cloned_env_path = os.path.join(self.working_dir, ".venv")

        def update_callback(msg: str):
            logger.info(f"[ENV CLONE] {msg.strip()}")

        success = clone_current_environment(
            self.cloned_env_path, self.working_dir, update_callback
        )

        if success:
            # Update python executable to use the cloned environment
            if self.os_type == 'Windows':
                self.python_executable = os.path.join(
                    self.cloned_env_path, "Scripts", "python.exe"
                )
            else:
                self.python_executable = os.path.join(
                    self.cloned_env_path, "bin", "python"
                )
        else:
            logger.info(
                "[ENV CLONE] Failed to create cloned environment, "
                "using system Python"
            )

    def _setup_initial_environment(self):
        r"""Set up an initial environment with Python 3.10."""
        self.initial_env_path = os.path.join(self.working_dir, ".initial_env")

        def update_callback(msg: str):
            logger.info(f"[ENV INIT] {msg.strip()}")

        # Try to ensure uv is available first
        success, uv_path = ensure_uv_available(update_callback)

        if success and uv_path:
            success = setup_initial_env_with_uv(
                self.initial_env_path,
                uv_path,
                self.working_dir,
                update_callback,
            )
        else:
            update_callback(
                "Falling back to standard venv for environment setup\n"
            )
            success = setup_initial_env_with_venv(
                self.initial_env_path, self.working_dir, update_callback
            )

        if success:
            # Update python executable to use the initial environment
            if self.os_type == 'Windows':
                self.python_executable = os.path.join(
                    self.initial_env_path, "Scripts", "python.exe"
                )
            else:
                self.python_executable = os.path.join(
                    self.initial_env_path, "bin", "python"
                )

            # Check Node.js availability
            check_nodejs_availability(update_callback)
        else:
            logger.info(
                "[ENV INIT] Failed to create initial environment, "
                "using system Python"
            )

    def _adapt_command_for_environment(self, command: str) -> str:
        r"""Adapt command to use virtual environment if available."""
        # Only adapt for local backend
        if self.use_docker_backend:
            return command

        # Check if we have any virtual environment (cloned or initial)
        env_path = None
        if self.cloned_env_path and os.path.exists(self.cloned_env_path):
            env_path = self.cloned_env_path
        elif self.initial_env_path and os.path.exists(self.initial_env_path):
            env_path = self.initial_env_path

        if not env_path:
            return command

        # Check if command starts with python or pip
        command_lower = command.strip().lower()
        if command_lower.startswith('python'):
            # Replace 'python' with the virtual environment python
            return command.replace('python', f'"{self.python_executable}"', 1)
        elif command_lower.startswith('pip'):
            # Replace 'pip' with python -m pip from virtual environment
            return command.replace(
                'pip', f'"{self.python_executable}" -m pip', 1
            )

        return command

    def _write_to_log(self, log_file: str, content: str) -> None:
        r"""Write content to log file with optional ANSI stripping.

        Args:
            log_file (str): Path to the log file
            content (str): Content to write
        """
        # Convert ANSI escape sequences to plain text
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(_to_plain(content) + "\n")

    def _sanitize_command(self, command: str) -> tuple[bool, str]:
        r"""A comprehensive command sanitizer for both local and
        Docker backends."""
        return sanitize_command(
            command=command,
            use_docker_backend=self.use_docker_backend,
            safe_mode=self.safe_mode,
            working_dir=self.working_dir,
            allowed_commands=self.allowed_commands,
        )

    def _start_output_reader_thread(self, session_id: str):
        r"""Starts a thread to read stdout from a non-blocking process."""
        with self._session_lock:
            session = self.shell_sessions[session_id]

        def reader():
            try:
                if session["backend"] == "local":
                    # For local processes, read line by line from stdout
                    try:
                        for line in iter(
                            session["process"].stdout.readline, ''
                        ):
                            session["output_stream"].put(line)
                            self._write_to_log(session["log_file"], line)
                    finally:
                        session["process"].stdout.close()
                elif session["backend"] == "docker":
                    # For Docker, read from the raw socket
                    socket = session["process"]._sock
                    while True:
                        # Check if the socket is still open before reading
                        if socket.fileno() == -1:
                            break
                        try:
                            ready, _, _ = select.select([socket], [], [], 0.1)
                        except (ValueError, OSError):
                            # Socket may have been closed by another thread
                            break
                        if ready:
                            data = socket.recv(4096)
                            if not data:
                                break
                            decoded_data = data.decode(
                                'utf-8', errors='ignore'
                            )
                            session["output_stream"].put(decoded_data)
                            self._write_to_log(
                                session["log_file"], decoded_data
                            )
                        # Check if the process is still running
                        if not self.docker_api_client.exec_inspect(
                            session["exec_id"]
                        )['Running']:
                            break
            except Exception as e:
                # Log the exception for diagnosis and store it on the session
                logger.exception(f"[SESSION {session_id}] Reader thread error")
                try:
                    with self._session_lock:
                        if session_id in self.shell_sessions:
                            self.shell_sessions[session_id]["error"] = str(e)
                except Exception:
                    # Swallow any secondary errors during cleanup
                    pass
            finally:
                try:
                    with self._session_lock:
                        if session_id in self.shell_sessions:
                            self.shell_sessions[session_id]["running"] = False
                except Exception:
                    pass

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()

    def _collect_output_until_idle(
        self,
        id: str,
        idle_duration: float = 0.5,
        check_interval: float = 0.1,
        max_wait: float = 5.0,
    ) -> str:
        r"""Collects output from a session until it's idle or a max wait time
        is reached.

        Args:
            id (str): The session ID.
            idle_duration (float): How long the stream must be empty to be
                considered idle.(default: 0.5)
            check_interval (float): The time to sleep between checks.
                (default: 0.1)
            max_wait (float): The maximum total time to wait for the process
                to go idle. (default: 5.0)

        Returns:
            str: The collected output. If max_wait is reached while
                 the process is still outputting, a warning is appended.
        """
        with self._session_lock:
            if id not in self.shell_sessions:
                return f"Error: No session found with ID '{id}'."

        output_parts = []
        idle_time = 0.0
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
                idle_time = 0.0  # Reset idle timer
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
            "\n--- WARNING: Process is still actively outputting "
            "after max wait time. Consider using shell_wait() "
            "before sending the next command. ---"
        )
        return "".join(output_parts) + warning_message

    def shell_exec(self, id: str, command: str, block: bool = True) -> str:
        r"""This function executes a shell command. The command can run in
        blocking mode (waits for completion) or non-blocking mode
        (runs in the background). A unique session ID is created for
        each session.

        Args:
            command (str): The command to execute.
            block (bool): If True, the command runs synchronously,
                waiting for it to complete or time out, and returns
                its full output. If False, the command runs
                asynchronously in the background.
            id (Optional[str]): A specific ID for the session. If not provided,
                a unique ID is generated for non-blocking sessions.

        Returns:
            str: If block is True, returns the complete stdout and stderr.
                 If block is False, returns a message containing the new
                 session ID and the initial output from the command after
                 it goes idle.
        """
        if self.safe_mode:
            is_safe, message = self._sanitize_command(command)
            if not is_safe:
                return f"Error: {message}"
            command = message
        else:
            command = command

        if self.use_docker_backend:
            # For Docker, we always run commands in a shell
            # to support complex commands
            command = f'bash -c "{command}"'
        else:
            # For local execution, check if we need to use cloned environment
            command = self._adapt_command_for_environment(command)

        session_id = id

        if block:
            # --- BLOCKING EXECUTION ---
            log_entry = (
                f"--- Executing blocking command at "
                f"{time.ctime()} ---\n> {command}\n"
            )
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
                        self.container.id, command, workdir="/workspace"
                    )
                    exec_output = self.docker_api_client.exec_start(
                        exec_instance['Id']
                    )
                    output = exec_output.decode('utf-8', errors='ignore')

                log_entry += f"--- Output ---\n{output}\n"
                return _to_plain(output)
            except subprocess.TimeoutExpired:
                error_msg = (
                    f"Error: Command timed out after {self.timeout} seconds."
                )
                log_entry += f"--- Error ---\n{error_msg}\n"
                return error_msg
            except Exception as e:
                if "Read timed out" in str(e):
                    error_msg = (
                        f"Error: Command timed out after "
                        f"{self.timeout} seconds."
                    )
                else:
                    error_msg = f"Error executing command: {e}"
                log_entry += f"--- Error ---\n{error_msg}\n"
                return error_msg
            finally:
                self._write_to_log(self.blocking_log_file, log_entry + "\n")
        else:
            # --- NON-BLOCKING EXECUTION ---
            session_log_file = os.path.join(
                self.log_dir, f"session_{session_id}.log"
            )

            self._write_to_log(
                session_log_file,
                f"--- Starting non-blocking session at {time.ctime()} ---\n"
                f"> {command}\n",
            )

            with self._session_lock:
                self.shell_sessions[session_id] = {
                    "id": session_id,
                    "process": None,
                    "output_stream": Queue(),
                    "command_history": [command],
                    "running": True,
                    "log_file": session_log_file,
                    "backend": "docker"
                    if self.use_docker_backend
                    else "local",
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
                    with self._session_lock:
                        self.shell_sessions[session_id]["process"] = process
                else:
                    exec_instance = self.docker_api_client.exec_create(
                        self.container.id,
                        command,
                        stdin=True,
                        tty=True,
                        workdir="/workspace",
                    )
                    exec_id = exec_instance['Id']
                    exec_socket = self.docker_api_client.exec_start(
                        exec_id, tty=True, stream=True, socket=True
                    )
                    with self._session_lock:
                        self.shell_sessions[session_id]["process"] = (
                            exec_socket
                        )
                        self.shell_sessions[session_id]["exec_id"] = exec_id

                self._start_output_reader_thread(session_id)

                # time.sleep(0.1)
                initial_output = self._collect_output_until_idle(session_id)

                return (
                    f"Session started with ID: {session_id}\n\n"
                    f"[Initial Output]:\n{initial_output}"
                )

            except Exception as e:
                with self._session_lock:
                    if session_id in self.shell_sessions:
                        self.shell_sessions[session_id]["running"] = False
                error_msg = f"Error starting non-blocking command: {e}"
                self._write_to_log(
                    session_log_file, f"--- Error ---\n{error_msg}\n"
                )
                return error_msg

    def shell_write_to_process(self, id: str, command: str) -> str:
        r"""This function sends command to a running non-blocking
        process and returns the resulting output after the process
        becomes idle again. A newline \n is automatically appended
        to the input command.

        Args:
            id (str): The unique session ID of the non-blocking process.
            command (str): The text to write to the process's standard input.

        Returns:
            str: The output from the process after the command is sent.
        """
        with self._session_lock:
            if (
                id not in self.shell_sessions
                or not self.shell_sessions[id]["running"]
            ):
                return (
                    f"Error: No active non-blocking "
                    f"session found with ID '{id}'."
                )
            session = self.shell_sessions[id]

        # Flush any lingering output from previous commands.
        self._collect_output_until_idle(id, idle_duration=0.3, max_wait=2.0)

        with self._session_lock:
            session["command_history"].append(command)
            log_file = session["log_file"]
            backend = session["backend"]
            process = session["process"]

        # Log command to the raw log file
        self._write_to_log(log_file, f"> {command}\n")

        try:
            if backend == "local":
                process.stdin.write(command + '\n')
                process.stdin.flush()
            else:  # docker
                socket = process._sock
                socket.sendall((command + '\n').encode('utf-8'))

            # Wait for and collect the new output
            output = self._collect_output_until_idle(id)

            return output

        except Exception as e:
            return f"Error writing to session '{id}': {e}"

    def shell_view(self, id: str) -> str:
        r"""This function retrieves any new output from a non-blocking session
        since the last time this function was called. If the process has
        terminated, it drains the output queue and appends a termination
        message. If the process is still running, it simply returns any
        new output.

        Args:
            id (str): The unique session ID of the non-blocking process.

        Returns:
            str: The new output from the process's stdout and stderr. Returns
                 an empty string if there is no new output.
        """
        with self._session_lock:
            if id not in self.shell_sessions:
                return f"Error: No session found with ID '{id}'."
            session = self.shell_sessions[id]
            is_running = session["running"]

        # If session is terminated, drain the queue and return
        # with a status message.
        if not is_running:
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
        r"""This function waits for a specified duration for a
        non-blocking process to produce more output or terminate.

        Args:
            id (str): The unique session ID of the non-blocking process.
            wait_seconds (float): The maximum number of seconds to wait.

        Returns:
            str: All output collected during the wait period.
        """
        with self._session_lock:
            if id not in self.shell_sessions:
                return f"Error: No session found with ID '{id}'."
            session = self.shell_sessions[id]
            if not session["running"]:
                return (
                    "Session is no longer running. "
                    "Use shell_view to get final output."
                )

        output_collected = []
        end_time = time.time() + wait_seconds
        while time.time() < end_time and session["running"]:
            new_output = self.shell_view(id)
            if new_output:
                output_collected.append(new_output)
            time.sleep(0.2)

        return "".join(output_collected)

    def shell_kill_process(self, id: str) -> str:
        r"""This function forcibly terminates a running non-blocking process.

        Args:
            id (str): The unique session ID of the process to kill.

        Returns:
            str: A confirmation message indicating the process was terminated.
        """
        with self._session_lock:
            if (
                id not in self.shell_sessions
                or not self.shell_sessions[id]["running"]
            ):
                return f"Error: No active session found with ID '{id}'."
            session = self.shell_sessions[id]
        try:
            if session["backend"] == "local":
                session["process"].terminate()
                time.sleep(0.5)
                if session["process"].poll() is None:
                    session["process"].kill()
                # Ensure stdio streams are closed to unblock reader thread
                try:
                    if getattr(session["process"], "stdin", None):
                        session["process"].stdin.close()
                except Exception:
                    pass
                try:
                    if getattr(session["process"], "stdout", None):
                        session["process"].stdout.close()
                except Exception:
                    pass
            else:  # docker
                # Docker exec processes stop when the socket is closed.
                session["process"].close()
            with self._session_lock:
                if id in self.shell_sessions:
                    self.shell_sessions[id]["running"] = False
            return f"Process in session '{id}' has been terminated."
        except Exception as e:
            return f"Error killing process in session '{id}': {e}"

    def shell_ask_user_for_help(self, id: str, prompt: str) -> str:
        r"""This function pauses execution and asks a human for help
        with an interactive session.

        This method can handle different scenarios:
        1. If session exists: Shows session output and allows interaction
        2. If session doesn't exist: Creates a temporary session for help

        Args:
            id (str): The session ID of the interactive process needing help.
                Can be empty string for general help without session context.
            prompt (str): The question or instruction from the LLM to show the
                human user (e.g., "The program is asking for a filename. Please
                enter 'config.json'.").

        Returns:
            str: The output from the shell session after the user's command has
                 been executed, or help information for general queries.
        """
        logger.info("\n" + "=" * 60)
        logger.info("🤖 LLM Agent needs your help!")
        logger.info(f"PROMPT: {prompt}")

        # Case 1: Session doesn't exist - offer to create one
        if id not in self.shell_sessions:
            try:
                user_input = input("Your response: ").strip()
                if not user_input:
                    return "No user response."
                else:
                    logger.info(
                        f"Creating session '{id}' and executing command..."
                    )
                    result = self.shell_exec(id, user_input, block=True)
                    return (
                        f"Session '{id}' created and "
                        f"executed command:\n{result}"
                    )
            except EOFError:
                return f"User input interrupted for session '{id}' creation."

        # Case 2: Session exists - show context and interact
        else:
            # Get the latest output to show the user the current state
            last_output = self._collect_output_until_idle(id)

            logger.info(f"SESSION: '{id}' (active)")
            logger.info("=" * 60)
            logger.info("--- LAST OUTPUT ---")
            logger.info(
                last_output.strip()
                if last_output.strip()
                else "(no recent output)"
            )
            logger.info("-------------------")

            try:
                user_input = input("Your input: ").strip()
                if not user_input:
                    return f"User provided no input for session '{id}'."
                else:
                    # Send input to the existing session
                    return self.shell_write_to_process(id, user_input)
            except EOFError:
                return f"User input interrupted for session '{id}'."

    def __del__(self):
        # Clean up any sessions
        with self._session_lock:
            session_ids = list(self.shell_sessions.keys())
        for session_id in session_ids:
            with self._session_lock:
                is_running = self.shell_sessions.get(session_id, {}).get(
                    "running", False
                )
            if is_running:
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
