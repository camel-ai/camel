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

import asyncio
import os
import shutil
import tempfile
import venv
from typing import List, Optional

from camel.interpreters.base import BaseInterpreter
from camel.interpreters.docker_interpreter import DockerInterpreter
from camel.interpreters.e2b_interpreter import E2BInterpreter
from camel.interpreters.interpreter_error import InterpreterError
from camel.interpreters.subprocess_interpreter import SubprocessInterpreter
from camel.logger import get_logger
from camel.verifiers import BaseVerifier

from .models import VerificationOutcome, VerificationResult, VerifierInput

logger = get_logger(__name__)


class PythonVerifier(BaseVerifier):
    r"""The PythonVerifier class verifies Python-based implementations
    by executing them using provided interpreters.

    Features:
    - Uses existing interpreters for code execution
    - Creates a virtual environment for local interpreters
    - Installs required packages based on interpreter type before execution
    - Executes the script and compares output against ground truth if supplied
    - Automatically cleans up local virtual environment after execution

    The verification process ensures that code runs in a controlled
    environment appropriate for the selected interpreter.
    """

    def __init__(
        self,
        interpreter: Optional[BaseInterpreter] = None,
        timeout: Optional[float] = 30.0,
        required_packages: Optional[List[str]] = None,
    ):
        r"""Initializes the PythonVerifier.

        Args:
            interpreter (Optional[BaseInterpreter], optional): The interpreter
                to use for code execution.
                If None, SubprocessInterpreter will be used.
                (default: :obj:`None`)
            timeout (Optional[float], optional): The execution timeout in
                seconds. (default: :obj:`30.0`)
            required_packages (Optional[List[str]], optional): A list of
                packages to install in the environment.
                (default: :obj:`None`)
        """
        super().__init__(interpreter=interpreter, timeout=timeout)
        self.interpreter = interpreter or SubprocessInterpreter(
            require_confirm=False
        )
        self.required_packages = required_packages or []

        # Auto-detect whether to use venv based on interpreter type
        # if not specified
        self.use_venv = not isinstance(
            self.interpreter, (DockerInterpreter, E2BInterpreter)
        )

        self.venv_path: Optional[str] = None

        if os.name == "nt":  # Windows
            self.bin_dir = "Scripts"
        else:  # Unix-like systems
            self.bin_dir = "bin"

    async def _setup(self) -> None:
        r"""Set up execution environment based on interpreter type."""
        if self.use_venv:
            # Set up a virtual environment for local interpreters
            self.venv_path = tempfile.mkdtemp(
                suffix=f"_camel_python_verifier_{self.interpreter.__class__.__name__}"
            )
            venv.create(self.venv_path, with_pip=True)
            logger.info(f"Virtual environment created at {self.venv_path}")

            if self.required_packages:
                await self._install_packages_in_venv()
        else:
            # For Docker/E2B, handle package installation differently
            if self.required_packages:
                if isinstance(self.interpreter, DockerInterpreter):
                    await self._install_packages_in_docker()
                elif isinstance(self.interpreter, E2BInterpreter):
                    await self._install_packages_in_e2b()

    async def _install_packages_in_venv(self) -> None:
        r"""Install required packages in the local virtual environment."""
        if not self.venv_path:
            logger.warning("Cannot install packages: venv not initialized")
            return

        venv_pip = os.path.join(self.venv_path, self.bin_dir, "pip")

        try:
            process = await asyncio.create_subprocess_exec(
                venv_pip,
                "install",
                *self.required_packages,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            _, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(
                    f"Failed to install packages: {stderr.decode().strip()}"
                )
            else:
                logger.info(
                    f"Installed packages: {', '.join(self.required_packages)}"
                )
        except Exception as e:
            logger.error(f"Error installing packages: {e}")

    async def _install_packages_in_docker(self) -> None:
        r"""Install required packages in the Docker container."""
        if not isinstance(self.interpreter, DockerInterpreter):
            logger.warning(
                "Attempted to install packages in Docker, "
                "but interpreter is not a DockerInterpreter. "
                f"Got {type(self.interpreter).__name__} instead."
            )
            return

        try:
            packages = " ".join(self.required_packages)
            pip_install_cmd = f"pip install {packages}"

            # Use the Docker interpreter to run the pip install command
            result = await asyncio.to_thread(
                self.interpreter.run, pip_install_cmd, "bash"
            )

            if "ERROR" in result.upper():
                logger.error(f"Docker package installation failed: {result}")
            else:
                logger.info(
                    f"Installed packages in Docker: {
                        ', '.join(self.required_packages)}"
                )
        except Exception as e:
            logger.error(f"Error installing packages in Docker: {e}")

    async def _install_packages_in_e2b(self) -> None:
        r"""Install required packages in the E2B sandbox."""
        if not isinstance(self.interpreter, E2BInterpreter):
            logger.warning(
                "Attempted to install packages in E2B, "
                "but interpreter is not an E2BInterpreter. "
                f"Got {type(self.interpreter).__name__} instead."
            )
            return

        try:
            packages = " ".join(self.required_packages)
            pip_install_cmd = f"pip install {packages}"

            # Use the E2B interpreter to run the pip install command
            result = await asyncio.to_thread(
                self.interpreter.run, pip_install_cmd, "bash"
            )

            if "ERROR" in result.upper():
                logger.error(f"E2B package installation failed: {result}")
            else:
                logger.info(
                    f"Installed packages in E2B: {', '.join(
                    self.required_packages)}"
                )
        except Exception as e:
            logger.error(f"Error installing packages in E2B: {e}")

    async def _cleanup(self) -> None:
        r"""Clean up resources based on interpreter type."""
        if self.use_venv and self.venv_path:
            if not os.path.exists(self.venv_path):
                logger.warning(
                    f"Virtual environment at {self.venv_path} does not exist"
                )
                self.venv_path = None
                return

            shutil.rmtree(self.venv_path)
            logger.info(f"Virtual environment at {self.venv_path} removed")
            self.venv_path = None

        # TODO: Add cleanup for Docker/E2B if needed

    async def _run_in_venv(self, script: str) -> str:
        r"""Execute Python script in the virtual environment."""
        if not self.venv_path:
            raise RuntimeError("Virtual environment is not set up")

        venv_python = os.path.join(self.venv_path, self.bin_dir, "python")

        if not os.path.exists(venv_python):
            raise RuntimeError(
                "Python binary not found in virtual environment"
            )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(script)
            script_path = f.name

        try:
            process = await asyncio.create_subprocess_exec(
                venv_python,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise RuntimeError(
                    f"Execution failed: {stderr.decode().strip()}"
                )

            return stdout.decode().strip()
        finally:
            # Clean up the temporary script
            if os.path.exists(script_path):
                os.unlink(script_path)

    async def _verify_implementation(
        self, result: VerifierInput
    ) -> VerificationResult:
        r"""Executes the LLM-generated response with the interpreter.

        Args:
            result (VerifierInput): Contains the LLM-generated Python code to
                execute and optional ground truth for comparison.

        Returns:
            VerificationResult: Contains verification status (SUCCESS/FAILURE/
                ERROR), execution output, error messages if any, and execution
                duration.

        Raises:
            asyncio.TimeoutError: If execution exceeds the configured timeout.
            Exception: Any unexpected errors during execution are caught and
                converted to an ERROR verification result.
        """
        script = result.llm_response.strip()

        try:
            execution_coroutine = (
                self._run_in_venv(script)
                if self.use_venv
                else asyncio.to_thread(self.interpreter.run, script, "python")
            )

            # Execute with timeout if specified
            if self._timeout is not None:
                output = await asyncio.wait_for(
                    execution_coroutine, timeout=self._timeout
                )
            else:
                output = await execution_coroutine

            # If ground truth is provided, compare it with the result
            if result.ground_truth is not None:
                normalized_output = " ".join(output.strip().split())
                normalized_truth = " ".join(
                    str(result.ground_truth).strip().split()
                )

                if normalized_output == normalized_truth:
                    return VerificationResult(
                        status=VerificationOutcome.SUCCESS,
                        result=output,
                    )
                else:
                    return VerificationResult(
                        status=VerificationOutcome.FAILURE,
                        error_message="Output doesn't match ground truth",
                        result=output,
                    )
            else:
                return VerificationResult(
                    status=VerificationOutcome.SUCCESS,
                    result=output,
                )

        except asyncio.TimeoutError:
            return VerificationResult(
                status=VerificationOutcome.TIMEOUT,
                result="",
                error_message="Execution timed out.",
            )
        except InterpreterError as e:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message=f"Interpreter error: {e}",
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message=f"Execution error: {e}",
            )
