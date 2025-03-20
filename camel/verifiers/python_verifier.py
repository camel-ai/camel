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
import copy
import json
import os
import shutil
import sys
import tempfile
import uuid
import venv
from typing import Any, Dict, List, Optional, cast

from camel.interpreters import (
    BaseInterpreter,
    DockerInterpreter,
    E2BInterpreter,
    InternalPythonInterpreter,
    InterpreterError,
    JupyterKernelInterpreter,
    SubprocessInterpreter,
)
from camel.logger import get_logger
from camel.verifiers.base import BaseVerifier
from camel.verifiers.models import (
    VerificationOutcome,
    VerificationResult,
    VerifierInput,
)

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
    - Automatically restores interpreter state after execution
    """

    def __init__(
        self,
        interpreter: Optional[BaseInterpreter] = None,
        timeout: Optional[float] = 30.0,
        required_packages: Optional[List[str]] = None,
    ):
        r"""Initialize the PythonVerifier.

        Args:
            interpreter (Optional[BaseInterpreter]): The interpreter to use.
                If None, SubprocessInterpreter will be used.
                (default: :obj:`None`)
            timeout (Optional[float]): The execution timeout in seconds.
                (default: :obj:`30.0`)
            required_packages (Optional[List[str]]): A list of packages to
                install in the environment. (default: :obj:`None`)
        """
        super().__init__(interpreter=interpreter, timeout=timeout)
        self.interpreter = interpreter or SubprocessInterpreter(
            require_confirm=False
        )
        self.required_packages = required_packages or []
        if isinstance(self.interpreter, JupyterKernelInterpreter):
            # JupyterKernelInterpreter requires ipykernel for kernel management
            self.required_packages += ["ipykernel"]

        # Auto-detect whether to use venv based on interpreter type
        self.use_venv = not isinstance(
            self.interpreter, (DockerInterpreter, E2BInterpreter)
        )

        self.venv_path: Optional[str] = None
        self.original_state: Dict[str, Any] = {}

        if os.name == "nt":  # Windows
            self.bin_dir = "Scripts"
        else:  # Unix-like systems
            self.bin_dir = "bin"

    async def _setup(self) -> None:
        r"""Set up execution environment based on interpreter type."""
        if self.use_venv:
            self._save_interpreter_state()

            self.venv_path = tempfile.mkdtemp(
                suffix=f"_camel_python_verifier_{self.interpreter.__class__.__name__}"
            )
            venv.create(self.venv_path, with_pip=True)
            logger.info(f"Virtual environment created at {self.venv_path}")

            if self.required_packages:
                await self._install_packages_in_venv()

            self._configure_interpreter_for_venv()
        else:
            if self.required_packages:
                if isinstance(self.interpreter, DockerInterpreter):
                    await self._install_packages_in_docker()
                elif isinstance(self.interpreter, E2BInterpreter):
                    await self._install_packages_in_e2b()

    def _save_interpreter_state(self) -> None:
        r"""Save the interpreter's original state for later restoration."""
        if isinstance(self.interpreter, SubprocessInterpreter):
            # For SubprocessInterpreter,
            # save command mapping
            self.original_state["cmd_mapping"] = copy.deepcopy(
                self.interpreter._CODE_EXECUTE_CMD_MAPPING
            )
        elif isinstance(self.interpreter, InternalPythonInterpreter):
            # For InternalPythonInterpreter,
            # save import whitelist and action space
            self.original_state["import_white_list"] = copy.deepcopy(
                self.interpreter.import_white_list
            )
            self.original_state["action_space"] = copy.deepcopy(
                self.interpreter.action_space
            )
        # Add other interpreter state saving as needed

    def _configure_interpreter_for_venv(self) -> None:
        r"""Configure the interpreter to use the virtual environment."""
        if not self.venv_path:
            logger.warning(
                "Cannot configure interpreter: venv not initialized"
            )
            return

        if isinstance(self.interpreter, SubprocessInterpreter):
            # For SubprocessInterpreter,
            # modify the Python command to use venv Python
            venv_python = os.path.join(self.venv_path, self.bin_dir, "python")
            self.interpreter._CODE_EXECUTE_CMD_MAPPING["python"] = (
                f"{venv_python} {{file_name}}"
            )
            logger.info(
                f"Configured SubprocessInterpreter to use venv Python: \
                    {venv_python}"
            )

        elif isinstance(self.interpreter, InternalPythonInterpreter):
            # For InternalPythonInterpreter,
            # modify its execution environment
            self._configure_internal_python_interpreter(self.interpreter)

        elif isinstance(self.interpreter, JupyterKernelInterpreter):
            # For JupyterKernelInterpreter,
            # create a custom kernel with venv Python
            kernel_task = asyncio.create_task(
                self._configure_jupyter_kernel_interpreter(self.interpreter)
            )
            self.original_state["kernel_task"] = kernel_task

    def _configure_internal_python_interpreter(
        self, interpreter: InternalPythonInterpreter
    ) -> None:
        """Configure InternalPythonInterpreter
        to prioritize packages from venv."""
        if not self.venv_path:
            logger.warning(
                "Cannot configure InternalPythonInterpreter: "
                "venv not initialized"
            )
            return

        # Determine the site-packages directory of the virtual environment
        if os.name == "nt":
            venv_site_packages = os.path.join(
                self.venv_path, "Lib", "site-packages"
            )
        else:
            venv_site_packages = os.path.join(
                self.venv_path,
                "lib",
                f"python{sys.version_info.major}.{sys.version_info.minor}",
                "site-packages",
            )
        logger.debug(f"venv site-packages: {venv_site_packages}")

        if not os.path.exists(venv_site_packages):
            logger.warning(
                f"venv site-packages not found at {venv_site_packages}"
            )
            return

        # Save original sys.path to restore later
        self.original_state["sys_path"] = sys.path.copy()

        # Save original execute method
        original_execute = interpreter.execute
        self.original_state["original_execute"] = original_execute

        def wrapped_execute(
            code, state=None, fuzz_state=None, keep_state=True
        ):
            """Wrap the execute method to modify sys.path before execution."""
            # Create setup code to modify sys.path
            setup_code = f"""
                        import sys
                        import os

                        # Insert venv site-packages
                        venv_site_packages = {venv_site_packages!r}
                        if (os.path.exists(venv_site_packages) and 
                            venv_site_packages not in sys.path):
                            sys.path.insert(0, venv_site_packages)
                        
                        """
            # Prepend setup code to the user's code
            modified_code = setup_code + code

            # Call original execute with modified code
            return original_execute(
                modified_code, state, fuzz_state, keep_state
            )

        # Replace execute method with our wrapped version using monkey patching
        cast(Any, interpreter).execute = wrapped_execute.__get__(
            interpreter, interpreter.__class__
        )

        logger.info(
            f"Configured InternalPythonInterpreter to prioritize packages \
                from {venv_site_packages}"
        )

    async def _configure_jupyter_kernel_interpreter(
        self, interpreter: JupyterKernelInterpreter
    ) -> None:
        """Configure JupyterKernelInterpreter
        to use a kernel with venv Python."""
        if not self.venv_path:
            logger.warning(
                "Cannot configure JupyterKernelInterpreter: \
                    venv not initialized"
            )
            return

        try:
            from jupyter_client.kernelspec import KernelSpecManager

            # Create a temporary kernel spec directory
            kernel_name = f"camel_venv_kernel_{uuid.uuid4().hex[:8]}"
            kernel_dir = os.path.join(tempfile.gettempdir(), kernel_name)
            os.makedirs(kernel_dir, exist_ok=True)

            # Path to the Python executable in the virtual environment
            venv_python = os.path.join(self.venv_path, self.bin_dir, "python")

            # Create kernel.json
            kernel_spec = {
                "argv": [
                    venv_python,
                    "-m",
                    "ipykernel_launcher",
                    "-f",
                    "{connection_file}",
                ],
                "display_name": f"CAMEL Python Verifier \
                    ({os.path.basename(self.venv_path)})",
                "language": "python",
            }

            with open(os.path.join(kernel_dir, "kernel.json"), "w") as f:
                json.dump(kernel_spec, f)

            # Register the kernel spec
            kernel_spec_manager = KernelSpecManager()
            kernel_spec_manager.install_kernel_spec(
                kernel_dir, kernel_name, user=True
            )

            # Save the original kernel manager to restore later
            if hasattr(interpreter, "kernel_manager"):
                self.original_state["kernel_manager"] = (
                    interpreter.kernel_manager
                )
                self.original_state["client"] = interpreter.client

            # Shutdown existing kernel if any
            if interpreter.kernel_manager:
                interpreter.kernel_manager.shutdown_kernel()
            if interpreter.client:
                interpreter.client.stop_channels()

            # Start a new kernel using our kernel spec
            from jupyter_client.manager import start_new_kernel

            kernel_manager, client = start_new_kernel(kernel_name=kernel_name)

            # Update the interpreter with the new kernel
            interpreter.kernel_manager = kernel_manager
            interpreter.client = client

            # Save kernel name for cleanup
            self.original_state["kernel_name"] = kernel_name
            self.original_state["kernel_dir"] = kernel_dir

            logger.info(
                f"Configured JupyterKernelInterpreter with custom kernel \
                    using {venv_python}"
            )

        except Exception as e:
            logger.error(f"Failed to configure JupyterKernelInterpreter: {e}")
            logger.warning(
                "JupyterKernelInterpreter will use the default kernel. "
                "Package isolation may be limited."
            )

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
                    f"Installed packages: \
                        {', '.join(self.required_packages)}"
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

            result = await asyncio.to_thread(
                self.interpreter.run, pip_install_cmd, "bash"
            )

            if "ERROR" in result.upper():
                # TODO: Replace with a more robust extractor
                logger.error(f"Docker package installation failed: {result}")
            else:
                logger.info(
                    f"Installed packages in Docker: \
                        {', '.join(self.required_packages)}"
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

            result = await asyncio.to_thread(
                self.interpreter.run, pip_install_cmd, "bash"
            )

            if "ERROR" in result.upper():
                # TODO: Replace with a more robust extractor
                logger.error(f"E2B package installation failed: {result}")
            else:
                logger.info(
                    f"Installed packages in E2B: \
                        {', '.join(self.required_packages)}"
                )
        except Exception as e:
            logger.error(f"Error installing packages in E2B: {e}")

    def _restore_interpreter_state(self) -> None:
        r"""Restore the interpreter to its original configuration."""
        if (
            isinstance(self.interpreter, SubprocessInterpreter)
            and "cmd_mapping" in self.original_state
        ):
            type(
                self.interpreter
            )._CODE_EXECUTE_CMD_MAPPING = self.original_state["cmd_mapping"]
            logger.info("Restored SubprocessInterpreter command mapping")

        elif isinstance(self.interpreter, InternalPythonInterpreter):
            # Restore original execute method
            if "original_execute" in self.original_state:
                cast(Any, self.interpreter).execute = self.original_state[
                    "original_execute"
                ].__get__(self.interpreter, self.interpreter.__class__)

            # Restore original sys.path
            if "sys_path" in self.original_state:
                sys.path = self.original_state["sys_path"]

            # Restore states
            if "import_white_list" in self.original_state:
                self.interpreter.import_white_list = self.original_state[
                    "import_white_list"
                ]
            if "action_space" in self.original_state:
                self.interpreter.action_space = self.original_state[
                    "action_space"
                ]

            logger.info("Restored InternalPythonInterpreter state")

        elif isinstance(self.interpreter, JupyterKernelInterpreter):
            if (
                "kernel_manager" in self.original_state
                and "client" in self.original_state
            ):
                # Shutdown kernel
                if self.interpreter.kernel_manager:
                    self.interpreter.kernel_manager.shutdown_kernel()
                if self.interpreter.client:
                    self.interpreter.client.stop_channels()

                # Restore states
                self.interpreter.kernel_manager = self.original_state[
                    "kernel_manager"
                ]
                self.interpreter.client = self.original_state["client"]

            # Cleanup the temporary kernel spec
            if "kernel_name" in self.original_state:
                try:
                    from jupyter_client.kernelspec import KernelSpecManager

                    kernel_spec_manager = KernelSpecManager()
                    kernel_spec_manager.remove_kernel_spec(
                        self.original_state["kernel_name"]
                    )
                except Exception as e:
                    logger.warning(f"Failed to remove kernel spec: {e}")

            # Cleanup the temporary kernel directory
            if "kernel_dir" in self.original_state and os.path.exists(
                self.original_state["kernel_dir"]
            ):
                try:
                    shutil.rmtree(self.original_state["kernel_dir"])
                except Exception as e:
                    logger.warning(f"Failed to remove kernel directory: {e}")

            logger.info("Restored JupyterKernelInterpreter state")

    async def _cleanup(self) -> None:
        r"""Clean up resources and restore interpreter state."""
        try:
            self._restore_interpreter_state()
        except Exception as e:
            logger.error(f"Error restoring interpreter state: {e}")

        # Clear state dictionary
        self.original_state = {}

        # Clean up venv last
        if self.venv_path and os.path.exists(self.venv_path):
            try:
                shutil.rmtree(self.venv_path)
                logger.info(f"Virtual environment at {self.venv_path} removed")
            except Exception as e:
                logger.warning(f"Failed to remove virtual environment: {e}")
            finally:
                self.venv_path = None

    async def _verify_implementation(
        self, result: VerifierInput
    ) -> VerificationResult:
        r"""Executes the LLM-generated response using the interpreter.

        For local interpreters,
        this will use the configured virtual environment
        for dependency isolation. For container-based interpreters, execution
        happens in the container with installed packages.

        Args:
            result: Contains the LLM-generated Python code and
                optional ground truth for comparison.

        Returns:
            VerificationResult: Structured result containing verification
                status, output, error messages, and execution duration.
        """
        script = result.llm_response.strip()

        if self.use_venv and (
            self.venv_path is None or not os.path.exists(self.venv_path)
        ):
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message="Virtual environment is not set up",
            )

        try:
            execution_coroutine = asyncio.to_thread(
                self.interpreter.run, script, "python"
            )

            if self._timeout:
                output = await asyncio.wait_for(
                    execution_coroutine, timeout=self._timeout
                )
            else:
                output = await execution_coroutine

            # Check for error indicators in the output
            if self._output_contains_error(output):
                return VerificationResult(
                    status=VerificationOutcome.ERROR,
                    error_message="Execution resulted in an error",
                    result=output,
                )

            # Compare with ground truth if provided
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

    def _output_contains_error(self, output: str) -> bool:
        r"""A temporary solution
        check for common error patterns in the output.
        TODO: Implement a more robust extractor

        Args:
            output: The output string from code execution

        Returns:
            bool: True if error indicators are found, False otherwise
        """
        error_indicators = [
            "Error",
            "Exception",
            "Traceback (most recent call last):",
            "stderr",
        ]

        # Check for common error patterns in the output
        return any(indicator in output for indicator in error_indicators)
