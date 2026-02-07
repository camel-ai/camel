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
import platform
import select
import shlex
import subprocess
import sys
import threading
import time
import uuid
from queue import Empty, Full, Queue
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits import manual_timeout
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
except ImportError:
    docker = None
    NotFound = None
    APIError = None


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
        timeout (Optional[float]): The default timeout in seconds for blocking
            commands. Defaults to 20.0.
        working_directory (Optional[str]): The base directory for operations.
            For the local backend, this acts as a security sandbox.
            For the Docker backend, this sets the working directory inside
            the container.
            If not specified, defaults to "./workspace" for local and
            "/workspace" for Docker.
        use_docker_backend (bool): If True, all commands are executed in a
            Docker container. Defaults to False.
        docker_container_name (Optional[str]): The name of the Docker
            container to use. Required if use_docker_backend is True.
        session_logs_dir (Optional[str]): The directory to store session
            logs. Defaults to a 'terminal_logs' subfolder in the
            working directory.
        safe_mode (bool): Whether to apply security checks to commands.
            Defaults to True.
        allowed_commands (Optional[List[str]]): List of allowed commands
            when safe_mode is True. If None, uses default safety rules.
        clone_current_env (bool): Whether to clone the current Python
            environment for local execution. Defaults to False.
        install_dependencies (List): A list of user specified libraries
            to install.
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
        install_dependencies: Optional[List[str]] = None,
    ):
        # auto-detect if running inside a CAMEL runtime container
        # when inside a runtime, use local execution (already sandboxed)
        runtime_env = os.environ.get("CAMEL_RUNTIME", "").lower()
        self._in_runtime = runtime_env == "true"
        if self._in_runtime and use_docker_backend:
            logger.info(
                "Detected CAMEL_RUNTIME environment - disabling Docker "
                "backend since we're already inside a sandboxed container"
            )
            use_docker_backend = False
            docker_container_name = None

        self.use_docker_backend = use_docker_backend
        self.timeout = timeout
        self.shell_sessions: Dict[str, Dict[str, Any]] = {}
        # Thread-safe guard for concurrent access to
        # shell_sessions and session state
        self._session_lock = threading.RLock()
        # Condition variable for efficient waiting on new output
        self._output_condition = threading.Condition(self._session_lock)

        # Initialize docker_workdir with proper type
        self.docker_workdir: Optional[str] = None

        if self.use_docker_backend:
            # For Docker backend, working_directory is path inside container
            if working_directory:
                self.docker_workdir = working_directory
            else:
                self.docker_workdir = "/workspace"
            # For logs and local file operations, use a local workspace
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                self.working_dir = os.path.abspath(camel_workdir)
            else:
                self.working_dir = os.path.abspath("./workspace")
        else:
            # For local backend, working_directory is the local path
            if working_directory:
                self.working_dir = os.path.abspath(working_directory)
            else:
                camel_workdir = os.environ.get("CAMEL_WORKDIR")
                if camel_workdir:
                    self.working_dir = os.path.abspath(camel_workdir)
                else:
                    self.working_dir = os.path.abspath("./workspace")

        # Only create local directory for logs and local backend operations
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
        self.install_dependencies = install_dependencies or []

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
                self.docker_api_client = docker.APIClient(
                    base_url='unix://var/run/docker.sock'
                )
                self.docker_client = docker.from_env()
                try:
                    # Try to get existing container
                    self.container = self.docker_client.containers.get(
                        docker_container_name
                    )
                    logger.info(
                        f"Successfully attached to existing Docker container "
                        f"'{docker_container_name}'."
                    )
                except NotFound:
                    raise RuntimeError(
                        f"Container '{docker_container_name}' not found."
                    )

                # Ensure the working directory exists inside the container
                if self.docker_workdir:
                    try:
                        quoted_dir = shlex.quote(self.docker_workdir)
                        mkdir_cmd = f'sh -lc "mkdir -p -- {quoted_dir}"'
                        _init = self.docker_api_client.exec_create(
                            self.container.id, mkdir_cmd
                        )
                        self.docker_api_client.exec_start(_init['Id'])
                    except Exception as e:
                        logger.warning(
                            f"[Docker] Failed to ensure workdir "
                            f"'{self.docker_workdir}': {e}"
                        )
            except APIError as e:
                raise RuntimeError(f"Failed to connect to Docker daemon: {e}")

        # Set up environments (only for local backend, skip in runtime mode)
        if self._in_runtime:
            logger.info(
                "[ENV] Skipping environment setup - running inside "
                "CAMEL runtime container"
            )
        elif not self.use_docker_backend:
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

        # Install dependencies
        if self.install_dependencies:
            self._install_dependencies()

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

    def _install_dependencies(self):
        r"""Install user specified dependencies in the current environment."""
        if not self.install_dependencies:
            return

        logger.info("Installing dependencies...")

        if self.use_docker_backend:
            pkg_str = " ".join(
                shlex.quote(p) for p in self.install_dependencies
            )
            install_cmd = f'sh -lc "pip install {pkg_str}"'

            try:
                exec_id = self.docker_api_client.exec_create(
                    self.container.id, install_cmd
                )["Id"]
                log = self.docker_api_client.exec_start(exec_id)
                logger.info(f"Package installation output:\n{log}")

                # Check exit code to ensure installation succeeded
                exec_info = self.docker_api_client.exec_inspect(exec_id)
                if exec_info['ExitCode'] != 0:
                    error_msg = (
                        f"Failed to install dependencies in Docker: "
                        f"{log.decode('utf-8', errors='ignore')}"
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                logger.info(
                    "Successfully installed all dependencies in Docker."
                )
            except Exception as e:
                if not isinstance(e, RuntimeError):
                    logger.error(f"Docker dependency installation error: {e}")
                    raise RuntimeError(
                        f"Docker dependency installation error: {e}"
                    ) from e
                raise

        else:
            pip_cmd = [
                self.python_executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                *self.install_dependencies,
            ]

            try:
                subprocess.run(
                    pip_cmd,
                    check=True,
                    cwd=self.working_dir,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes timeout for installation
                )
                logger.info("Successfully installed all dependencies.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install dependencies: {e.stderr}")
                raise RuntimeError(
                    f"Failed to install dependencies: {e.stderr}"
                ) from e
            except subprocess.TimeoutExpired:
                logger.error(
                    "Dependency installation timed out after 5 minutes"
                )
                raise RuntimeError(
                    "Dependency installation timed out after 5 minutes"
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

    def _get_venv_path(self) -> Optional[str]:
        r"""Get the virtual environment path if available."""
        if self.cloned_env_path and os.path.exists(self.cloned_env_path):
            return self.cloned_env_path
        elif self.initial_env_path and os.path.exists(self.initial_env_path):
            return self.initial_env_path
        return None

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
            def safe_put(data: str) -> None:
                """Put data to queue, dropping if full to prevent blocking."""
                try:
                    session["output_stream"].put_nowait(data)
                except Full:
                    # Queue is full, log warning and continue
                    # Data is still written to log file, so not lost
                    logger.warning(
                        f"[SESSION {session_id}] Output queue full, "
                        f"dropping data (still logged to file)"
                    )
                    return
                # Notify waiters that new output is available
                # Done outside try-except to avoid catching unrelated
                # exceptions
                with self._output_condition:
                    self._output_condition.notify_all()

            try:
                if session["backend"] == "local":
                    # For local processes, read line by line from stdout
                    try:
                        for line in iter(
                            session["process"].stdout.readline, ''
                        ):
                            self._write_to_log(session["log_file"], line)
                            safe_put(line)
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
                            self._write_to_log(
                                session["log_file"], decoded_data
                            )
                            safe_put(decoded_data)
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
                except Exception as cleanup_error:
                    logger.warning(
                        f"[SESSION {session_id}] Failed to store error state: "
                        f"{cleanup_error}"
                    )
            finally:
                try:
                    with self._output_condition:
                        if session_id in self.shell_sessions:
                            self.shell_sessions[session_id]["running"] = False
                        # Notify waiters that session has terminated
                        self._output_condition.notify_all()
                except Exception:
                    pass

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()

    def _collect_output_until_idle(
        self,
        id: str,
        idle_duration: float = 0.5,
        max_wait: float = 5.0,
    ) -> str:
        r"""Collects output from a session until it's idle or a max wait time
        is reached.

        Args:
            id (str): The session ID.
            idle_duration (float): How long the stream must be empty to be
                considered idle.(default: 0.5)
            max_wait (float): The maximum total time to wait for the process
                to go idle. (default: 5.0)

        Returns:
            str: The collected output. If max_wait is reached while
                 the process is still outputting, a warning is appended.
        """
        with self._session_lock:
            if id not in self.shell_sessions:
                return f"Error: No session found with ID '{id}'."

        output_parts: List[str] = []
        last_output_time = time.time()
        start_time = last_output_time

        while True:
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                break

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

            # Check if this is actual output or just the idle message
            if new_output and not new_output.startswith("[No new output]"):
                output_parts.append(new_output)
                last_output_time = time.time()  # Reset idle timer
            else:
                # No new output, check if we've been idle long enough
                idle_time = time.time() - last_output_time
                if idle_time >= idle_duration:
                    # Process is idle, success
                    return "".join(output_parts)

            # Calculate remaining time for idle and max_wait
            time_until_idle = idle_duration - (time.time() - last_output_time)
            time_until_max = max_wait - (time.time() - start_time)
            # Wait for the shorter of: idle timeout, max timeout, or a
            # reasonable check interval
            wait_time = max(0.0, min(time_until_idle, time_until_max))

            if wait_time > 0:
                # Use condition variable to wait efficiently
                # Wake up when new output arrives or timeout expires
                with self._output_condition:
                    self._output_condition.wait(timeout=wait_time)

        # If we exit the loop, it means max_wait was reached.
        # Check one last time for any final output.
        final_output = self.shell_view(id)
        if final_output and not final_output.startswith("[No new output]"):
            output_parts.append(final_output)

        warning_message = (
            "\n--- WARNING: Process is still actively outputting "
            "after max wait time. Consider waiting before "
            "sending the next command. ---"
        )
        return "".join(output_parts) + warning_message

    def shell_exec(
        self,
        id: str,
        command: str,
        block: bool = True,
        timeout: float = 20.0,
    ) -> str:
        r"""Executes a shell command in blocking or non-blocking mode.

        Args:
            id (str): A unique identifier for the command's session. This ID is
                used to interact with non-blocking processes.
            command (str): The shell command to execute.
            block (bool, optional): Determines the execution mode. Defaults to
                True. If `True` (blocking mode), the function waits for the
                command to complete and returns the full output. Use this for
                most commands. If `False` (non-blocking mode), the function
                starts the command in the background. Use this only for
                interactive sessions or long-running tasks, or servers.
            timeout (float, optional): The maximum time in seconds to
                wait for the command to complete in blocking mode. If the
                command does not complete within the timeout, it will be
                converted to a tracked background session (process keeps
                running without restart). You can then use `shell_view(id)`
                to check output, or `shell_kill_process(id)` to terminate it.
                This parameter is ignored in non-blocking mode.
                (default: :obj:`20`)

        Returns:
            str: The output of the command execution, which varies by mode.
                In blocking mode, returns the complete standard output and
                standard error from the command.
                In non-blocking mode, returns a confirmation message with the
                session `id`. To interact with the background process, use
                other functions: `shell_view(id)` to see output,
                `shell_write_to_process(id, "input")` to send input, and
                `shell_kill_process(id)` to terminate.
        """
        if self.safe_mode:
            is_safe, message = self._sanitize_command(command)
            if not is_safe:
                return f"Error: {message}"
            command = message

        if self.use_docker_backend:
            # For Docker, we always run commands in a shell
            # to support complex commands.
            # Use shlex.quote to properly escape the command string.
            command = f'bash -c {shlex.quote(command)}'
        else:
            # For local execution, activate virtual environment if available
            env_path = self._get_venv_path()
            if env_path:
                if self.os_type == 'Windows':
                    activate = os.path.join(
                        env_path, "Scripts", "activate.bat"
                    )
                    command = f'call "{activate}" && {command}'
                else:
                    activate = os.path.join(env_path, "bin", "activate")
                    command = f'. "{activate}" && {command}'

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
                    env_vars = os.environ.copy()
                    env_vars["PYTHONUNBUFFERED"] = "1"
                    proc = subprocess.Popen(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.PIPE,
                        shell=True,
                        text=True,
                        cwd=self.working_dir,
                        encoding="utf-8",
                        env=env_vars,
                    )
                    try:
                        stdout, _ = proc.communicate(timeout=timeout)
                        output = stdout or ""
                    except subprocess.TimeoutExpired as e:
                        if e.stdout:
                            partial_output = (
                                e.stdout.decode("utf-8", errors="ignore")
                                if isinstance(e.stdout, bytes)
                                else e.stdout
                            )
                        else:
                            partial_output = ""

                        session_log_file = os.path.join(
                            self.log_dir, f"session_{session_id}.log"
                        )
                        self._write_to_log(
                            session_log_file,
                            f"--- Blocking command timed out, converted to "
                            f"session at {time.ctime()} ---\n> {command}\n",
                        )

                        # Pre-populate output queue with partial output
                        output_queue: Queue = Queue(maxsize=10000)
                        if partial_output:
                            output_queue.put(partial_output)

                        with self._session_lock:
                            self.shell_sessions[session_id] = {
                                "id": session_id,
                                "process": proc,
                                "output_stream": output_queue,
                                "command_history": [command],
                                "running": True,
                                "log_file": session_log_file,
                                "backend": "local",
                                "timeout_converted": True,
                            }

                        # Start reader thread to capture ongoing output
                        self._start_output_reader_thread(session_id)

                        self._write_to_log(
                            self.blocking_log_file, log_entry + "\n"
                        )
                        return (
                            f"Command did not complete within {timeout} "
                            f"seconds. Process continues in background as "
                            f"session '{session_id}'.\n\n"
                            f"You can use:\n"
                            f"  - shell_view('{session_id}') - get output\n"
                            f"  - shell_kill_process('{session_id}') - "
                            f"terminate"
                        )
                else:
                    # DOCKER BLOCKING with timeout
                    assert (
                        self.docker_workdir is not None
                    )  # Docker backend always has workdir
                    exec_instance = self.docker_api_client.exec_create(
                        self.container.id, command, workdir=self.docker_workdir
                    )
                    exec_id = exec_instance['Id']

                    # Use thread to implement timeout for docker exec
                    result_container: Dict[str, Any] = {}

                    def run_exec():
                        try:
                            result_container['output'] = (
                                self.docker_api_client.exec_start(exec_id)
                            )
                        except Exception as e:
                            result_container['error'] = e

                    exec_thread = threading.Thread(target=run_exec)
                    exec_thread.start()
                    exec_thread.join(timeout=timeout)

                    if exec_thread.is_alive():
                        # Timeout occurred - convert to tracked session
                        # so agent can monitor or kill the process.
                        # The exec_thread continues running in background and
                        # will eventually write output to result_container.
                        session_log_file = os.path.join(
                            self.log_dir, f"session_{session_id}.log"
                        )
                        self._write_to_log(
                            session_log_file,
                            f"--- Blocking command timed out, converted to "
                            f"session at {time.ctime()} ---\n> {command}\n",
                        )

                        with self._session_lock:
                            self.shell_sessions[session_id] = {
                                "id": session_id,
                                "process": None,  # No socket for blocking exec
                                "exec_id": exec_id,
                                "exec_thread": exec_thread,  # Thread reference
                                "result_container": result_container,  # Shared
                                "output_stream": Queue(maxsize=10000),
                                "command_history": [command],
                                "running": True,
                                "log_file": session_log_file,
                                "backend": "docker",
                                "timeout_converted": True,  # Mark as converted
                            }

                        self._write_to_log(
                            self.blocking_log_file, log_entry + "\n"
                        )
                        return (
                            f"Command did not complete within {timeout} "
                            f"seconds. Process continues in background as "
                            f"session '{session_id}'.\n\n"
                            f"You can use:\n"
                            f"  - shell_view('{session_id}') - get output\n"
                            f"  - shell_kill_process('{session_id}') - "
                            f"terminate"
                        )

                    if 'error' in result_container:
                        raise result_container['error']

                    output = result_container['output'].decode(
                        'utf-8', errors='ignore'
                    )

                log_entry += f"--- Output ---\n{output}\n"
                if output.strip():
                    return _to_plain(output)
                else:
                    return "Command executed successfully (no output)."
            except Exception as e:
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

            # PYTHONUNBUFFERED=1 for real-time output
            # Without this, Python subprocesses buffer output (4KB buffer)
            # and shell_view() won't see output until buffer fills or process
            # exits
            env_vars = os.environ.copy()
            env_vars["PYTHONUNBUFFERED"] = "1"
            docker_env = {"PYTHONUNBUFFERED": "1"}

            # Check and create session atomically to prevent race condition
            with self._session_lock:
                if session_id in self.shell_sessions:
                    existing_session = self.shell_sessions[session_id]
                    if existing_session.get("running", False):
                        return (
                            f"Error: Session '{session_id}' already exists "
                            f"and is running. Use a different ID or kill "
                            f"the existing session first."
                        )

                # Create session entry while holding the lock
                self.shell_sessions[session_id] = {
                    "id": session_id,
                    "process": None,
                    # Limit queue size to prevent memory exhaustion
                    # (~100MB with 10k items of ~10KB each)
                    "output_stream": Queue(maxsize=10000),
                    "command_history": [command],
                    "running": True,
                    "log_file": session_log_file,
                    "backend": "docker"
                    if self.use_docker_backend
                    else "local",
                }

            self._write_to_log(
                session_log_file,
                f"--- Starting non-blocking session at {time.ctime()} ---\n"
                f"> {command}\n",
            )

            process = None
            exec_socket = None
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
                        env=env_vars,
                    )
                    with self._session_lock:
                        self.shell_sessions[session_id]["process"] = process
                else:
                    assert (
                        self.docker_workdir is not None
                    )  # Docker backend always has workdir
                    exec_instance = self.docker_api_client.exec_create(
                        self.container.id,
                        command,
                        stdin=True,
                        tty=True,
                        workdir=self.docker_workdir,
                        environment=docker_env,
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

                # Return immediately with session ID and instructions
                return (
                    f"Session '{session_id}' started.\n\n"
                    f"You could use:\n"
                    f"  - shell_view('{session_id}') - get output\n"
                    f"  - shell_write_to_process('{session_id}', '<input>')"
                    f" - send input\n"
                    f"  - shell_kill_process('{session_id}') - terminate"
                )

            except Exception as e:
                # Clean up resources on failure
                if process is not None:
                    try:
                        process.terminate()
                    except Exception:
                        pass
                if exec_socket is not None:
                    try:
                        exec_socket.close()
                    except Exception:
                        pass

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

            if output.strip():
                return output
            else:
                return (
                    f"Input sent to session '{id}' successfully (no output)."
                )

        except Exception as e:
            return f"Error writing to session '{id}': {e}"

    def shell_view(self, id: str) -> str:
        r"""Retrieves new output from a non-blocking session.

        This function returns only NEW output since the last call. It does NOT
        wait or block - it returns immediately with whatever is available.

        Args:
            id (str): The unique session ID of the non-blocking process.

        Returns:
            str: New output if available, or a status message.
        """
        with self._session_lock:
            if id not in self.shell_sessions:
                return f"Error: No session found with ID '{id}'."
            session = self.shell_sessions[id]
            is_running = session["running"]

        # If session is terminated, drain the queue and return
        if not is_running:
            final_output = []
            try:
                while True:
                    final_output.append(session["output_stream"].get_nowait())
            except Empty:
                pass

            if final_output:
                return "".join(final_output) + "\n\n--- SESSION TERMINATED ---"
            else:
                return "--- SESSION TERMINATED (no new output) ---"

        # For running session, check for new output
        output = []
        try:
            while True:
                output.append(session["output_stream"].get_nowait())
        except Empty:
            pass

        if output:
            return "".join(output)
        else:
            # For timeout-converted Docker sessions, check thread and output
            if (
                session.get("timeout_converted")
                and session.get("backend") == "docker"
            ):
                exec_thread = session.get("exec_thread")
                result_container = session.get("result_container", {})

                # Check if the background thread has completed
                if exec_thread and not exec_thread.is_alive():
                    # Thread finished - get output from result_container
                    with self._session_lock:
                        if id in self.shell_sessions:
                            self.shell_sessions[id]["running"] = False

                    if 'output' in result_container:
                        completed_output = result_container['output'].decode(
                            'utf-8', errors='ignore'
                        )
                        # Write to log file
                        self._write_to_log(
                            session["log_file"], completed_output
                        )
                        return (
                            f"{_to_plain(completed_output)}\n\n"
                            f"--- SESSION COMPLETED ---"
                        )
                    elif 'error' in result_container:
                        return (
                            f"--- SESSION FAILED ---\n"
                            f"Error: {result_container['error']}"
                        )
                    else:
                        return "--- SESSION COMPLETED (no output) ---"
                else:
                    # Thread still running
                    return (
                        "[Process still running]\n"
                        "Command is executing in background. "
                        "Check again later for output.\n"
                        "Use shell_kill_process() to terminate if needed."
                    )

            # No new output - guide the agent
            return (
                "[No new output]\n"
                "Session is running but idle. Actions could take:\n"
                "  - For interactive sessions: Send input "
                "with shell_write_to_process()\n"
                "  - For long tasks: Check again later (don't poll "
                "too frequently)"
            )

    @manual_timeout
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
                # Check if this is a timeout-converted session (no socket)
                if session.get("timeout_converted") and session.get("exec_id"):
                    # Kill the process using Docker exec PID
                    exec_id = session["exec_id"]
                    try:
                        exec_info = self.docker_api_client.exec_inspect(
                            exec_id
                        )
                        pid = exec_info.get('Pid')
                        if pid and exec_info.get('Running', False):
                            # Kill the process inside the container
                            kill_cmd = f'kill -9 {pid}'
                            kill_exec = self.docker_api_client.exec_create(
                                self.container.id, kill_cmd
                            )
                            self.docker_api_client.exec_start(kill_exec['Id'])
                    except Exception as kill_err:
                        logger.warning(
                            f"[SESSION {id}] Failed to kill Docker exec "
                            f"process: {kill_err}"
                        )
                elif session["process"] is not None:
                    # Normal non-blocking session with socket
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
        # Use print for user-facing messages since this is an interactive
        # function that requires terminal input via input()
        print("\n" + "=" * 60)
        print("LLM Agent needs your help!")
        print(f"PROMPT: {prompt}")

        # Case 1: Session doesn't exist - offer to create one
        if id not in self.shell_sessions:
            try:
                user_input = input("Your response: ").strip()
                if not user_input:
                    return "No user response."
                else:
                    print(f"Creating session '{id}' and executing command...")
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
            last_output_display = (
                last_output.strip() if last_output.strip() else "(no output)"
            )

            print(f"SESSION: '{id}' (active)")
            print("=" * 60)
            print("--- LAST OUTPUT ---")
            print(last_output_display)
            print("-------------------")

            try:
                user_input = input("Your input: ").strip()
                if not user_input:
                    return f"User provided no input for session '{id}'."
                else:
                    # Send input to the existing session
                    return self.shell_write_to_process(id, user_input)
            except EOFError:
                return f"User input interrupted for session '{id}'."

    def shell_write_content_to_file(self, content: str, file_path: str) -> str:
        r"""Writes the specified content to a file at the given path.

        Args:
            content (str): The content to write to the file.
            file_path (str): The path to the file where the content should
                be written. Can be absolute or relative to working_dir.

        Returns:
            str: A confirmation message indicating success or an error message.
        """
        # For local backend, resolve relative paths to working_dir
        if not self.use_docker_backend and self.working_dir:
            if not os.path.isabs(file_path):
                file_path = os.path.normpath(
                    os.path.join(self.working_dir, file_path)
                )
            else:
                file_path = os.path.normpath(file_path)
            file_path = os.path.abspath(file_path)

            # Safe mode path containment check for local backend
            if self.safe_mode:
                working_dir_normalized = os.path.normpath(
                    os.path.abspath(self.working_dir)
                )
                # Use os.path.commonpath for secure path containment check
                try:
                    common = os.path.commonpath(
                        [file_path, working_dir_normalized]
                    )
                    if common != working_dir_normalized:
                        return (
                            "Error: Cannot write to a file outside of the "
                            "working directory in safe mode."
                        )
                except ValueError:
                    # Paths are on different drives (Windows) or invalid
                    return (
                        "Error: Cannot write to a file outside of the "
                        "working directory in safe mode."
                    )

        log_entry = (
            f"--- Writing content to file at {time.ctime()} ---\n"
            f"> {file_path}\n"
        )
        if self.use_docker_backend:
            temp_host_path = None
            try:
                # Ensure parent directory exists in container
                parent_dir = os.path.dirname(file_path)
                if parent_dir:
                    quoted_dir = shlex.quote(parent_dir)
                    mkdir_cmd = f'sh -lc "mkdir -p {quoted_dir}"'
                    mkdir_exec = self.docker_api_client.exec_create(
                        self.container.id, mkdir_cmd
                    )
                    self.docker_api_client.exec_start(mkdir_exec['Id'])

                # Write content to a temporary file on the host inside log_dir
                temp_file_name = f"temp_{uuid.uuid4().hex}.txt"
                temp_host_path = os.path.join(self.log_dir, temp_file_name)
                with open(temp_host_path, "w", encoding="utf-8") as f:
                    f.write(content)
                # Copy the temporary file into the Docker container
                dest_path_in_container = file_path
                container_dest = (
                    f"{self.container.name}:{dest_path_in_container}"
                )
                subprocess.run(
                    ['docker', 'cp', temp_host_path, container_dest],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                log_entry += f"\n-------- \n{content}\n--------\n"
                with open(self.blocking_log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
                return (
                    f"Content successfully written to '{file_path}' "
                    f"in Docker container."
                )
            except subprocess.CalledProcessError as e:
                log_entry += f"--- Error ---\n{e.stderr}\n"
                with open(self.blocking_log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
                return (
                    f"Error writing to file '{file_path}' "
                    f"in Docker container: {e.stderr}"
                )
            except Exception as e:
                log_entry += f"--- Error ---\n{e}\n"
                with open(self.blocking_log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
                return (
                    f"Error writing to file '{file_path}' "
                    f"in Docker container: {e}"
                )
            finally:
                # Clean up the temporary file
                if temp_host_path and os.path.exists(temp_host_path):
                    try:
                        os.remove(temp_host_path)
                    except OSError:
                        pass

        else:
            try:
                # Ensure parent directory exists
                parent_dir = os.path.dirname(file_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                log_entry += f"\n-------- \n{content}\n--------\n"
                with open(self.blocking_log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
                return f"Content successfully written to '{file_path}'."
            except Exception as e:
                log_entry += f"--- Error ---\n{e}\n"
                with open(self.blocking_log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
                return f"Error writing to file '{file_path}': {e}"

    def __enter__(self):
        r"""Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        r"""Context manager exit - clean up all sessions."""
        self.cleanup()
        return False

    @manual_timeout
    def cleanup(self):
        r"""Clean up all active sessions."""
        with self._session_lock:
            session_ids = list(self.shell_sessions.keys())
        for session_id in session_ids:
            with self._session_lock:
                is_running = self.shell_sessions.get(session_id, {}).get(
                    "running", False
                )
            if is_running:
                try:
                    self.shell_kill_process(session_id)
                except Exception as e:
                    logger.warning(
                        f"Failed to kill session '{session_id}' "
                        f"during cleanup: {e}"
                    )

    @manual_timeout
    def __del__(self):
        r"""Fallback cleanup in destructor."""
        try:
            self.cleanup()
        except Exception:
            pass

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
            FunctionTool(self.shell_write_content_to_file),
            FunctionTool(self.shell_write_to_process),
            FunctionTool(self.shell_kill_process),
            FunctionTool(self.shell_ask_user_for_help),
        ]
