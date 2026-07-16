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
import time
import uuid
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Set

from camel.interpreters.base import BaseInterpreter
from camel.interpreters.interpreter_error import InterpreterError
from camel.logger import get_logger
from camel.utils import api_keys_required, dependencies_required

if TYPE_CHECKING:
    from islo.types import ExecResultResponse

logger = get_logger(__name__)


class IsloInterpreter(BaseInterpreter):
    r"""Islo Code Interpreter implementation.

    This interpreter executes code in an isolated cloud sandbox provided
    by islo.dev (https://docs.islo.dev), using the official `islo`
    Python SDK. The sandbox is created lazily on the first execution and
    can optionally be deleted when the interpreter is cleaned up.

    Args:
        require_confirm (bool, optional): If True, prompt user before
            running code strings for security. (default: :obj:`True`)
        api_key (Optional[str], optional): API key for the Islo service.
            If not provided, the ISLO_API_KEY environment variable
            will be used. (default: :obj:`None`)
        sandbox_name (Optional[str], optional): Name of an existing
            sandbox to attach to. If not provided, a new sandbox with a
            generated name is created on first use.
            (default: :obj:`None`)
        image (str, optional): Container image used when creating a new
            sandbox.
            (default: :obj:`"ghcr.io/islo-labs/islo-runner:latest"`)
        workdir (Optional[str], optional): Working directory for command
            execution inside the sandbox. (default: :obj:`None`)
        user (Optional[str], optional): User to run commands as inside
            the sandbox. If not provided, uses the image default.
            (default: :obj:`None`)
        vcpus (Optional[int], optional): Number of vCPUs for a newly
            created sandbox. (default: :obj:`None`)
        memory_mb (Optional[int], optional): Memory in MB for a newly
            created sandbox. (default: :obj:`None`)
        disk_gb (Optional[int], optional): Disk size in GB for a newly
            created sandbox. (default: :obj:`None`)
        exec_timeout (int, optional): Timeout in seconds for a single
            code or command execution. (default: :obj:`60`)
        poll_interval (float, optional): Interval in seconds between
            polls while waiting for sandbox startup or execution results.
            (default: :obj:`1.0`)
        startup_timeout (int, optional): Timeout in seconds to wait for
            the sandbox to reach the running state.
            (default: :obj:`120`)
        delete_on_exit (Optional[bool], optional): Whether to delete the
            sandbox on cleanup. If :obj:`None`, defaults to
            :obj:`True` when the interpreter created the sandbox and
            :obj:`False` when attached to an existing one via
            `sandbox_name`. (default: :obj:`None`)

    Environment Variables:
        ISLO_API_KEY: The API key for authenticating with the Islo
            service.
    """

    _CODE_TYPE_MAPPING: ClassVar[Dict[str, List[str]]] = {
        "python": ["python3", "-c"],
        "py3": ["python3", "-c"],
        "python3": ["python3", "-c"],
        "py": ["python3", "-c"],
        "bash": ["bash", "-c"],
        "shell": ["bash", "-c"],
        "sh": ["bash", "-c"],
        "javascript": ["node", "-e"],
        "js": ["node", "-e"],
        "node": ["node", "-e"],
    }

    _TERMINAL_EXEC_STATUSES: ClassVar[Set[str]] = {
        "completed",
        "failed",
        "timeout",
    }

    # Extra seconds allowed for polling beyond `exec_timeout`, to give
    # the service time to report a server-side timeout.
    _EXEC_GRACE_SECS: ClassVar[int] = 30

    @dependencies_required('islo')
    @api_keys_required(
        [
            ("api_key", "ISLO_API_KEY"),
        ]
    )
    def __init__(
        self,
        require_confirm: bool = True,
        api_key: Optional[str] = None,
        sandbox_name: Optional[str] = None,
        image: str = "ghcr.io/islo-labs/islo-runner:latest",
        workdir: Optional[str] = None,
        user: Optional[str] = None,
        vcpus: Optional[int] = None,
        memory_mb: Optional[int] = None,
        disk_gb: Optional[int] = None,
        exec_timeout: int = 60,
        poll_interval: float = 1.0,
        startup_timeout: int = 120,
        delete_on_exit: Optional[bool] = None,
    ) -> None:
        from islo import Islo

        self.require_confirm = require_confirm
        self.sandbox_name = sandbox_name
        self.image = image
        self.workdir = workdir
        self.user = user
        self.vcpus = vcpus
        self.memory_mb = memory_mb
        self.disk_gb = disk_gb
        self.exec_timeout = exec_timeout
        self.poll_interval = poll_interval
        self.startup_timeout = startup_timeout

        # The interpreter owns the sandbox when it has to create it.
        self._owns_sandbox = sandbox_name is None
        self.delete_on_exit = (
            self._owns_sandbox if delete_on_exit is None else delete_on_exit
        )
        # The sandbox is created lazily on first execution.
        self._sandbox_created = False

        # `api_key=None` falls back to the ISLO_API_KEY env var.
        self._client = Islo(api_key=api_key)

        logger.info("Initialized IsloInterpreter")

    def run(
        self,
        code: str,
        code_type: str = "python",
    ) -> str:
        r"""Executes the given code in the Islo sandbox.

        Args:
            code (str): The code string to execute.
            code_type (str): The type of code to execute (e.g., 'python',
                'bash', 'javascript'). (default: obj:`python`)

        Returns:
            str: The string representation of the output of the executed
                code.

        Raises:
            InterpreterError: If the `code_type` is not supported or if
                any runtime error occurs during the execution of the code.
        """
        if code_type not in self._CODE_TYPE_MAPPING:
            raise InterpreterError(
                f"Unsupported code type {code_type}. "
                f"`{self.__class__.__name__}` only supports "
                f"{', '.join(list(self._CODE_TYPE_MAPPING.keys()))}."
            )
        # Print code for security checking
        if self.require_confirm:
            logger.info(
                f"The following {code_type} code will run on your "
                f"Islo sandbox: {code}"
            )
            while True:
                choice = input("Running code? [Y/n]:").lower()
                if choice in ["y", "yes", "ye"]:
                    break
                elif choice not in ["no", "n"]:
                    continue
                raise InterpreterError(
                    "Execution halted: User opted not to run the code. "
                    "This choice stops the current operation and any "
                    "further code execution."
                )

        self._ensure_sandbox()
        command = [*self._CODE_TYPE_MAPPING[code_type], code]
        result = self._exec_blocking(command)
        return self._format_output(result)

    def supported_code_types(self) -> List[str]:
        r"""Provides supported code types by the interpreter."""
        return list(self._CODE_TYPE_MAPPING.keys())

    def update_action_space(self, action_space: Dict[str, Any]) -> None:
        r"""Updates action space for *python* interpreter"""
        raise RuntimeError("Islo doesn't support `action_space`.")

    def execute_command(self, command: str) -> str:
        r"""Execute a command can be used to resolve the dependency of the
        code.

        Args:
            command (str): The command to execute.

        Returns:
            str: The output of the command.
        """
        self._ensure_sandbox()
        result = self._exec_blocking(["bash", "-c", command])
        return self._format_output(result)

    def cleanup(self) -> None:
        r"""Deletes the sandbox if the interpreter is responsible for it.

        The sandbox is deleted only when it has been created (or
        attached) and `delete_on_exit` is :obj:`True`.
        """
        if not self._sandbox_created or not self.delete_on_exit:
            return
        try:
            self._client.sandboxes.delete_sandbox(
                sandbox_name=self.sandbox_name
            )
            self._sandbox_created = False
            logger.info(f"Deleted Islo sandbox: {self.sandbox_name}")
        except Exception as e:
            logger.warning(
                f"Failed to delete Islo sandbox `{self.sandbox_name}`: {e}"
            )

    def __del__(self) -> None:
        r"""Destructor for the IsloInterpreter class.

        This method ensures that the Islo sandbox is deleted when the
        interpreter is garbage collected, if the interpreter owns it.
        """
        try:
            if hasattr(self, '_sandbox_created'):
                self.cleanup()
        except Exception as e:
            logger.warning(f"Error during sandbox cleanup: {e}")

    def _ensure_sandbox(self) -> None:
        r"""Creates or attaches to the sandbox and waits until it runs.

        Raises:
            InterpreterError: If the sandbox fails to reach the
                running state within `startup_timeout` seconds, or
                if any SDK error occurs.
        """
        if self._sandbox_created:
            return

        name = self.sandbox_name or f"camel-islo-{uuid.uuid4().hex[:8]}"
        created_here = False
        try:
            if self._owns_sandbox:
                create_kwargs: Dict[str, Any] = {
                    "name": name,
                    "image": self.image,
                }
                if self.vcpus is not None:
                    create_kwargs["vcpus"] = self.vcpus
                if self.memory_mb is not None:
                    create_kwargs["memory_mb"] = self.memory_mb
                if self.disk_gb is not None:
                    create_kwargs["disk_gb"] = self.disk_gb
                if self.workdir is not None:
                    create_kwargs["workdir"] = self.workdir
                self._client.sandboxes.create_sandbox(**create_kwargs)
                created_here = True
                logger.info(f"Created Islo sandbox: {name}")
            self._wait_for_running(name)
        except Exception as e:
            if created_here:
                # The just-created cloud sandbox is billed and would
                # otherwise be orphaned: best-effort delete it before
                # propagating the startup failure.
                try:
                    self._client.sandboxes.delete_sandbox(sandbox_name=name)
                    logger.info(
                        f"Deleted Islo sandbox `{name}` after startup "
                        f"failure"
                    )
                except Exception as delete_error:
                    logger.warning(
                        f"Failed to delete Islo sandbox `{name}` after "
                        f"startup failure: {delete_error}"
                    )
            if isinstance(e, InterpreterError):
                raise
            raise InterpreterError(
                f"Failed to start Islo sandbox `{name}`: {e}"
            )
        self.sandbox_name = name
        self._sandbox_created = True

    def _wait_for_running(self, name: str) -> None:
        r"""Polls the sandbox until it reaches the running state.

        Args:
            name (str): The name of the sandbox to wait for.

        Raises:
            InterpreterError: If the sandbox enters a terminal state or
                does not become running within `startup_timeout`
                seconds.
        """
        deadline = time.monotonic() + self.startup_timeout
        resume_requested = False
        while True:
            sandbox = self._client.sandboxes.get_sandbox(sandbox_name=name)
            status = sandbox.status
            if status == "running":
                return
            if status == "paused" and not resume_requested:
                logger.info(f"Resuming paused Islo sandbox: {name}")
                self._client.sandboxes.resume_sandbox(sandbox_name=name)
                resume_requested = True
            elif status in ("failed", "deleted"):
                raise InterpreterError(
                    f"Islo sandbox `{name}` is in terminal state "
                    f"`{status}` and cannot execute code."
                )
            if time.monotonic() > deadline:
                raise InterpreterError(
                    f"Islo sandbox `{name}` did not reach the `running` "
                    f"state within {self.startup_timeout} seconds "
                    f"(last status: `{status}`)."
                )
            time.sleep(self.poll_interval)

    def _exec_blocking(self, command: List[str]) -> 'ExecResultResponse':
        r"""Starts a command in the sandbox and polls for its result.

        The Islo exec API is asynchronous: `exec_in_sandbox` returns an
        exec ID, and the result is polled via `get_exec_result` until
        the execution reaches a terminal status.

        Args:
            command (List[str]): The command (argv) to execute.

        Returns:
            ExecResultResponse: The terminal execution result.

        Raises:
            InterpreterError: If the SDK raises an error or the result
                does not become available in time.
        """
        exec_kwargs: Dict[str, Any] = {}
        if self.workdir is not None:
            exec_kwargs["workdir"] = self.workdir
        if self.user is not None:
            exec_kwargs["user"] = self.user
        try:
            started = self._client.sandboxes.exec_in_sandbox(
                sandbox_name=self.sandbox_name,
                command=command,
                timeout_secs=self.exec_timeout,
                **exec_kwargs,
            )
            deadline = (
                time.monotonic() + self.exec_timeout + self._EXEC_GRACE_SECS
            )
            while True:
                result = self._client.sandboxes.get_exec_result(
                    sandbox_name=self.sandbox_name,
                    exec_id=started.exec_id,
                )
                if result.status in self._TERMINAL_EXEC_STATUSES:
                    return result
                if time.monotonic() > deadline:
                    raise InterpreterError(
                        f"Execution in Islo sandbox "
                        f"`{self.sandbox_name}` did not finish within "
                        f"{self.exec_timeout} seconds."
                    )
                time.sleep(self.poll_interval)
        except InterpreterError:
            raise
        except Exception as e:
            raise InterpreterError(
                f"Error executing code in Islo sandbox "
                f"`{self.sandbox_name}`: {e}"
            )

    def _format_output(self, result: 'ExecResultResponse') -> str:
        r"""Formats a terminal execution result into a string.

        Args:
            result (ExecResultResponse): The terminal execution result.

        Returns:
            str: The formatted output.

        Raises:
            InterpreterError: If the execution timed out server-side.
        """
        if result.status == "timeout":
            raise InterpreterError(
                f"Execution in Islo sandbox `{self.sandbox_name}` timed "
                f"out after {self.exec_timeout} seconds."
            )

        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            output_parts.append(f"[stderr] {result.stderr}")
        if result.exit_code not in (0, None):
            output_parts.append(f"Exit code: {result.exit_code}")
        if result.status == "failed" and result.exit_code in (0, None):
            # A failed execution may carry no stderr and no exit code
            # (e.g. the process could not be started). Never report it
            # as a success.
            output_parts.append(
                "Execution failed in the Islo sandbox "
                f"(status: failed, exit code: {result.exit_code})."
            )
        if result.truncated:
            output_parts.append("[output truncated]")

        if output_parts:
            return "\n".join(output_parts)

        return "Code executed successfully (no output)."
