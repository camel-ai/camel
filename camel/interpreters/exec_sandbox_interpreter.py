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
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from camel.interpreters.base import BaseInterpreter
from camel.interpreters.interpreter_error import InterpreterError
from camel.logger import get_logger

if TYPE_CHECKING:
    from exec_sandbox import Scheduler, Session
    from exec_sandbox.models import Language

logger = get_logger(__name__)


@dataclass(frozen=True)
class ExecSandboxConfig:
    r"""Configuration for ExecSandboxInterpreter.

    All fields map to exec-sandbox ``SchedulerConfig`` parameters.
    Fields left as ``None`` use the SDK defaults.

    Attributes:
        warm_pool_size: Pre-booted VMs per language.
            0 disables warm pool. (default: :obj:`None`)
        default_memory_mb: Default guest VM memory in MB.
            Minimum 128. (default: :obj:`None`)
        default_timeout_seconds: Default execution timeout in seconds.
            Range 1-300. (default: :obj:`None`)
        images_dir: Directory containing VM images (qcow2, kernels).
            If None, auto-detects. (default: :obj:`None`)
        s3_bucket: S3 bucket for snapshot backup.
            None disables S3. (default: :obj:`None`)
        s3_region: AWS region for S3 bucket.
            (default: :obj:`None`)
        s3_prefix: Prefix for S3 keys.
            (default: :obj:`None`)
        enable_package_validation: Validate packages against
            allowlist. (default: :obj:`None`)
        auto_download_assets: Automatically download VM images
            from GitHub Releases. (default: :obj:`None`)
    """

    warm_pool_size: Optional[int] = field(default=None)
    default_memory_mb: Optional[int] = field(default=None)
    default_timeout_seconds: Optional[int] = field(default=None)
    images_dir: Optional[str] = field(default=None)
    s3_bucket: Optional[str] = field(default=None)
    s3_region: Optional[str] = field(default=None)
    s3_prefix: Optional[str] = field(default=None)
    enable_package_validation: Optional[bool] = field(default=None)
    auto_download_assets: Optional[bool] = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        r"""Convert to a dict with only non-None values.

        Returns:
            dict[str, Any]: Fields that were explicitly set.
        """
        return {k: v for k, v in asdict(self).items() if v is not None}


class ExecSandboxInterpreter(BaseInterpreter):
    r"""exec-sandbox Code Interpreter implementation.

    This interpreter provides secure code execution using exec-sandbox,
    a self-hosted platform that runs code in ephemeral QEMU microVMs with
    hardware-level isolation (KVM/HVF). It supports Python, JavaScript,
    and shell command execution.

    Sessions are persistent per language — variables, imports, and functions
    defined in one ``run()`` call are available in subsequent calls with the
    same language. Each language gets its own isolated VM.

    Args:
        require_confirm (bool, optional): If True, prompt user before running
            code strings for security. (default: :obj:`True`)
        timeout (int, optional): Default timeout for code execution in seconds.
            (default: :obj:`30`)
        config (Optional[ExecSandboxConfig]): Typed configuration for
            the exec-sandbox Scheduler. If None, uses SDK defaults.
            (default: :obj:`None`)

    Note:
        Requires the exec-sandbox package:
        ``pip install 'camel-ai[exec-sandbox]'``.
    """

    _CODE_TYPE_MAPPING: ClassVar[dict[str, Language]] = {
        # Python code
        "python": "python",
        "py": "python",
        "py3": "python",
        "python3": "python",
        # JavaScript/Node.js code
        "javascript": "javascript",
        "js": "javascript",
        "node": "javascript",
        "typescript": "javascript",
        "ts": "javascript",
        # Shell commands
        "bash": "raw",
        "shell": "raw",
        "sh": "raw",
    }

    def __init__(
        self,
        require_confirm: bool = True,
        timeout: int = 30,
        config: Optional[ExecSandboxConfig] = None,
    ) -> None:
        try:
            from exec_sandbox import Scheduler, SchedulerConfig
        except ImportError:
            raise InterpreterError(
                "exec-sandbox package is required. "
                "Install with: pip install 'camel-ai[exec-sandbox]'"
            )

        self.require_confirm = require_confirm
        self.timeout = timeout

        # Build SchedulerConfig from typed config dataclass
        config_dict = config.to_dict() if config else {}
        self._scheduler_config = SchedulerConfig(**config_dict)
        self._Scheduler = Scheduler

        # Lazy-initialized on first call, reused across runs
        self._scheduler: Optional[Scheduler] = None
        # One persistent session per language (state survives across calls)
        self._sessions: dict[str, Session] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        logger.info("Initialized ExecSandboxInterpreter")

    def run(
        self,
        code: str,
        code_type: str = "python",
    ) -> str:
        r"""Executes the given code in an exec-sandbox microVM.

        State persists across calls with the same language — variables,
        imports, and functions defined in one call are available in the next.

        Args:
            code (str): The code string to execute.
            code_type (str): The type of code to execute. Supported types:
                'python', 'py', 'py3', 'python3', 'javascript', 'js',
                'node', 'typescript', 'ts', 'bash', 'shell', 'sh'.
                (default: :obj:`python`)

        Returns:
            str: The string representation of the output of the executed code.

        Raises:
            InterpreterError: If the `code_type` is not supported or if any
                runtime error occurs during the execution of the code.
        """
        code_type_lower = code_type.lower()
        if code_type_lower not in self._CODE_TYPE_MAPPING:
            raise InterpreterError(
                f"Unsupported code type {code_type}. "
                f"`{self.__class__.__name__}` only supports "
                f"{', '.join(list(self._CODE_TYPE_MAPPING.keys()))}."
            )

        if self.require_confirm:
            logger.info(
                f"The following {code_type} code will run on "
                f"exec-sandbox: {code}"
            )
            self._confirm_execution("code")

        language = self._CODE_TYPE_MAPPING[code_type_lower]
        return self._run_sync(code, language)

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        r"""Get or create a dedicated event loop for the scheduler."""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    async def _ensure_scheduler(self) -> Scheduler:
        r"""Lazy-init the Scheduler on first use.

        Returns:
            The started Scheduler instance, reused across calls.
        """
        if self._scheduler is None:
            self._scheduler = self._Scheduler(self._scheduler_config)
            await self._scheduler.__aenter__()
            logger.info("Scheduler started (lazy init)")
        return self._scheduler

    async def _ensure_session(self, language: Language) -> Session:
        r"""Get or create a persistent session for the given language.

        Each language gets its own VM session. State (variables, imports,
        functions) persists across exec() calls within the same session.

        Args:
            language (Language): The exec-sandbox language enum value.

        Returns:
            The Session for this language, reused across calls.
        """
        if language not in self._sessions or self._sessions[language].closed:
            scheduler = await self._ensure_scheduler()
            session = await scheduler.session(language=language)
            await session.__aenter__()
            self._sessions[language] = session
            logger.info(f"Session started for language={language}")
        return self._sessions[language]

    def _run_sync(self, code: str, language: Language) -> str:
        r"""Run code synchronously via the persistent event loop.

        Args:
            code (str): The code to execute.
            language (Language): The exec-sandbox language enum value.

        Returns:
            str: The output of the executed code.

        Raises:
            InterpreterError: If execution fails.
        """
        loop = self._get_loop()
        try:
            return loop.run_until_complete(self._run_async(code, language))
        except Exception as e:
            raise InterpreterError(
                f"Error executing code in exec-sandbox: {e}"
            ) from e

    async def _run_async(self, code: str, language: Language) -> str:
        r"""Asynchronously executes code in a persistent session.

        Args:
            code (str): The code to execute.
            language (Language): The exec-sandbox language enum value.

        Returns:
            str: The output of the executed code.
        """
        session = await self._ensure_session(language)
        result = await session.exec(
            code=code,
            timeout_seconds=self.timeout,
        )
        return self._format_output(
            result.stdout,
            result.stderr,
            result.exit_code,
        )

    def close(self) -> None:
        r"""Shut down all sessions, the Scheduler, and close the event loop.

        Safe to call multiple times.
        """
        loop = self._get_loop()

        # Close all sessions
        for language, session in list(self._sessions.items()):
            try:
                loop.run_until_complete(session.__aexit__(None, None, None))
            except Exception:
                logger.debug(
                    f"Error closing session for {language}", exc_info=True
                )
        self._sessions.clear()

        # Close the scheduler
        if self._scheduler is not None:
            try:
                loop.run_until_complete(
                    self._scheduler.__aexit__(None, None, None)
                )
            except Exception:
                logger.debug("Error during Scheduler shutdown", exc_info=True)
            self._scheduler = None

        if self._loop is not None and not self._loop.is_closed():
            self._loop.close()
            self._loop = None
        logger.debug("ExecSandboxInterpreter closed")

    def __del__(self) -> None:
        r"""Destructor — best-effort scheduler cleanup."""
        try:
            self.close()
        except Exception:
            pass

    @staticmethod
    def _format_output(stdout: str, stderr: str, exit_code: int) -> str:
        r"""Format execution output combining stdout, stderr, and exit code.

        Args:
            stdout (str): Standard output from execution.
            stderr (str): Standard error from execution.
            exit_code (int): Process exit code.

        Returns:
            str: Formatted output string.
        """
        result_parts = []
        if stdout and stdout.strip():
            result_parts.append(stdout.strip())
        if stderr and stderr.strip():
            result_parts.append(f"STDERR: {stderr.strip()}")
        if exit_code != 0:
            result_parts.append(f"Exit code: {exit_code}")

        return (
            "\n".join(result_parts)
            if result_parts
            else "Code executed successfully (no output)"
        )

    def _confirm_execution(self, execution_type: str) -> None:
        r"""Prompt user for confirmation before executing code or commands.

        Args:
            execution_type (str): Type of execution ('code' or 'command').

        Raises:
            InterpreterError: If user declines to run the code/command.
        """
        while True:
            choice = input(f"Running {execution_type}? [Y/n]:").lower()
            if choice in ["y", "yes", "ye"]:
                break
            elif choice not in ["no", "n"]:
                continue
            raise InterpreterError(
                f"Execution halted: User opted not to run the "
                f"{execution_type}. "
                f"This choice stops the current operation and any "
                f"further {execution_type} execution."
            )

    def supported_code_types(self) -> list[str]:
        r"""Provides supported code types by the interpreter."""
        return list(self._CODE_TYPE_MAPPING.keys())

    def update_action_space(self, action_space: dict[str, Any]) -> None:
        r"""Updates action space for interpreter.

        Args:
            action_space: Action space dictionary (unused in exec-sandbox).

        Note:
            exec-sandbox doesn't support action space updates. Each
            language gets its own persistent VM session.
        """
        _ = action_space
        logger.warning(
            "exec-sandbox doesn't support action space updates. "
            "Each language gets its own persistent VM session."
        )

    def execute_command(self, command: str) -> str | tuple[str, str]:
        r"""Execute a shell command in an exec-sandbox microVM.

        Args:
            command (str): The shell command to execute.

        Returns:
            str | tuple[str, str]: The output of the command.
        """
        if self.require_confirm:
            logger.info(
                f"The following shell command will run on "
                f"exec-sandbox: {command}"
            )
            self._confirm_execution("command")

        return self._run_sync(command, "raw")
