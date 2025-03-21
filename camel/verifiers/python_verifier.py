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

import ast
import asyncio
import os
import shutil
import subprocess
import tempfile
import venv
from typing import List, Optional, Tuple

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
        r"""Executes the provided Python solution in an isolated environment
        and verifies its output against an optional ground truth.

        This method evaluates both the solution and the ground truth by running
        each in a temporary script within the configured virtual environment.
        It supports both full code blocks and standalone expressions by
        automatically wrapping expressions in `print(...)`.

        If both executions are successful, the outputs are compared using
        Python semantics (via `eval`). If evaluation fails, a fallback to
        raw string comparison is used.

        Args:
            solution (str): The Python code or expression to execute
                and verify.
            ground_truth (Optional[str]): The expected output as code or
                expression for comparison. If None, execution is only checked
                for success.

        Returns:
            VerificationResult: Structured result containing status, result,
            and any error messages from execution or comparison.
        """

        if not self.venv_path:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message="Virtual environment is not set up.",
            )

        venv_python = os.path.join(self.venv_path, self.bin_dir, "python")

        if not os.path.exists(venv_python):
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message="Python binary not found in virtual environment",
            )

        try:
            sol_out, sol_err, sol_code = await self._run_code_block(
                solution, venv_python
            )
            if ground_truth is not None:
                gt_out, gt_err, gt_code = await self._run_code_block(
                    ground_truth, venv_python
                )
            else:
                gt_out = None

            if sol_code != 0:
                return VerificationResult(
                    status=VerificationOutcome.ERROR,
                    result=sol_out,
                    error_message=f"Solution code error:\n{sol_err}",
                )

            if ground_truth is not None and gt_code != 0:
                return VerificationResult(
                    status=VerificationOutcome.ERROR,
                    result=gt_out,
                    error_message=f"Ground truth code error:\n{gt_err}",
                )

            # Compare outputs semantically if possible
            if ground_truth is not None:
                try:
                    sol_val = eval(sol_out, {}, {})
                    gt_val = eval(gt_out, {}, {})
                    if sol_val == gt_val:
                        return VerificationResult(
                            status=VerificationOutcome.SUCCESS,
                            result=sol_out,
                        )
                    else:
                        return VerificationResult(
                            status=VerificationOutcome.FAILURE,
                            result=sol_out,
                            error_message="Printed outputs differ.",
                        )
                except Exception:
                    # Fallback to string comparison
                    logger.warning("Fallback to String matching.")
                    if sol_out == gt_out:
                        return VerificationResult(
                            status=VerificationOutcome.SUCCESS,
                            result=sol_out,
                        )
                    else:
                        return VerificationResult(
                            status=VerificationOutcome.FAILURE,
                            result=sol_out,
                            error_message="Fallback to string matching:"
                            f"printed outputs {sol_out} and {gt_out} differ.",
                        )
            else:
                return VerificationResult(
                    status=VerificationOutcome.SUCCESS,
                    result=sol_out,
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
                error_message=f"Unexpected error: {e}",
            )

    async def _run_code_block(
        self, code: str, venv_path: str
    ) -> Tuple[str, str, int]:
        r"""Executes a block of Python code or expression in the virtual
         environment.

        If the input is a single-line expression, it is automatically wrapped
        in `print(...)` to ensure its result is captured via stdout. The code
        is written to a temporary file, executed using the Python interpreter
        from the specified virtual environment, and its output and
        error streams are captured.

        Args:
            code (str): The Python code or expression to execute.
            venv_path (str): The path to the virtual environment's
                Python binary.

        Returns:
            Tuple[str, str, int]: A tuple containing the stdout output,
            stderr output, and return code from the executed script.
        """

        if self._is_expression(code):
            code = f"print({code})"

        with tempfile.NamedTemporaryFile(
            "w+", suffix=".py", delete=False
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        proc = await asyncio.create_subprocess_exec(
            venv_path,
            tmp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=self._timeout
        )
        os.remove(tmp_path)
        return (
            stdout.decode().strip(),
            stderr.decode().strip(),
            proc.returncode,
        )

    def _is_expression(self, code: str) -> bool:
        r"""Determines whether a given string of code is a single expression.

        This utility uses Python's AST module to parse the code and checks if
        it consists of a single expression node. This helps distinguish between
        full code blocks (e.g., function definitions) and evaluatable
        expressions (e.g., `2 + 2`, `[1, 2, 3]`).

        Args:
            code (str): The Python code to analyze.

        Returns:
            bool: True if the code is a single expression, False otherwise.
        """
        try:
            parsed = ast.parse(code)
            return len(parsed.body) == 1 and isinstance(
                parsed.body[0], ast.Expr
            )
        except Exception:
            return False
