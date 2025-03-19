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
import subprocess
import tempfile
import venv
from typing import List, Optional

from camel.extractors import BaseExtractor
from camel.logger import get_logger
from camel.verifiers import BaseVerifier

from .models import VerificationOutcome, VerificationResult

logger = get_logger(__name__)


class PythonVerifier(BaseVerifier):
    r"""The PythonVerifier class verifies Python-based implementations
    by executing them in an isolated virtual environment.

    Features:
    - Creates a virtual environment with a specified Python version.
    - Installs required packages before executing the provided script.
    - Executes the script and compares the output against a ground truth,
      if supplied.
    - Automatically cleans up the virtual environment after execution.

    The verification process ensures that the code runs in a controlled
    environment, minimizing external dependencies and conflicts.
    """

    def __init__(
        self,
        timeout: Optional[float] = 30.0,
        required_packages: Optional[List[str]] = None,
        extractor: Optional[BaseExtractor] = None,
    ):
        r"""Initializes the PythonVerifier.

        Args:
            timeout (Optional[float], optional): The execution timeout in
                seconds. (default: :obj:`30.0`)
            required_packages (Optional[List[str]], optional): A list of
                packages to install in the virtual environment.
                (default: :obj:`None`)
        """
        # TODO: Use CAMEL's Interpreter to execute the code
        super().__init__(timeout=timeout)
        self.venv_path: Optional[str] = None
        self.required_packages = required_packages or []

        if os.name == 'nt':  # Windows
            self.bin_dir = 'Scripts'
        else:  # Unix-like systems
            self.bin_dir = 'bin'

    async def _setup(self) -> None:
        r"""Set up a virtual environment for execution
        and install required packages.
        """
        self.venv_path = tempfile.mkdtemp()
        venv.create(self.venv_path, with_pip=True)
        logger.info(f"Virtual environment created at {self.venv_path}")

        venv_pip = os.path.join(self.venv_path, self.bin_dir, "pip")

        if self.required_packages:
            try:
                subprocess.run(
                    [venv_pip, "install", *self.required_packages],
                    check=True,
                    capture_output=True,
                )
                logger.info(
                    "Installed required packages:"
                    f"{', '.join(self.required_packages)}"
                )
            except subprocess.CalledProcessError as e:
                logger.error(
                    "Failed to install required packages: "
                    f"{e.stderr.decode().strip()}"
                )

    async def _cleanup(self) -> None:
        r"""Clean up the virtual environment."""
        if self.venv_path:
            shutil.rmtree(self.venv_path)
            logger.info(f"Virtual environment at {self.venv_path} removed")
            self.venv_path = None

    async def _verify_implementation(
        self, solution: str, ground_truth: Optional[str]
    ) -> VerificationResult:
        r"""Executes and verifies the LLM-generated Python solution in an
        isolated virtual environment.

        This method runs the given Python solution inside a controlled virtual
        environment, captures its execution output, and optionally compares it
        against a provided ground truth. Handles timeouts and execution errors.

        Args:
            solution (str): The Python code to execute and verify.
            ground_truth (Optional[str]): The expected output for comparison.
                If None, verification is based only on execution success.

        Returns:
            VerificationResult: A structured object containing:
                - status (VerificationOutcome): SUCCESS, FAILURE, ERROR,
                or TIMEOUT.
                - result (str): The execution output of the solution.
                - error_message (Optional[str]): Captured error message,
                if any.
                - duration (float, optional): Execution time (set externally).

        Raises:
            asyncio.TimeoutError: If execution exceeds the configured timeout.
            Exception: Any unexpected errors are caught and converted to an
            ERROR verification result.
        """
        if not self.venv_path:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message="Virtual environment is not set up.",
            )

        script = solution.strip()
        venv_python = os.path.join(self.venv_path, self.bin_dir, "python")

        if not os.path.exists(venv_python):
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message="Python binary not found in virtual environment",
            )

        try:
            process = await asyncio.create_subprocess_exec(
                venv_python,
                "-c",
                script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self._timeout
            )

            output_result = stdout.decode().strip()
            error_output = stderr.decode().strip()

            if process.returncode == 0:
                # If ground truth is provided, compare it with the result
                if ground_truth is not None:
                    # Normalize both strings by removing extra whitespace
                    normalized_output = ' '.join(output_result.strip().split())
                    normalized_truth = ' '.join(
                        str(ground_truth).strip().split()
                    )

                    if normalized_output == normalized_truth:
                        return VerificationResult(
                            status=VerificationOutcome.SUCCESS,
                            result=output_result,
                        )
                    else:
                        return VerificationResult(
                            status=VerificationOutcome.FAILURE,
                            error_message="Output doesn't match ground truth",
                            result=output_result,
                        )
                else:
                    return VerificationResult(
                        status=VerificationOutcome.SUCCESS,
                        result=output_result,
                    )

            else:
                return VerificationResult(
                    status=VerificationOutcome.ERROR,
                    error_message=error_output,
                    result=output_result,
                )

        except asyncio.TimeoutError:
            return VerificationResult(
                status=VerificationOutcome.TIMEOUT,
                result="",
                error_message="Execution timed out.",
            )

        except Exception as e:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message=f"Execution error: {e}",
            )
