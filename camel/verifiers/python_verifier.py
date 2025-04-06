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
import sys
import tempfile
import venv
from typing import List, Optional, Tuple

from camel.extractors.base import BaseExtractor
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
        extractor: Optional[BaseExtractor] = None,
        timeout: Optional[float] = 30.0,
        required_packages: Optional[List[str]] = None,
        **kwargs,
    ):
        r"""Initializes the PythonVerifier.

        Args:
            extractor (Optional[BaseExtractor], optional): The extractor to use
                for extracting code from the solution. (default: :obj:`None`)
            timeout (Optional[float], optional): The execution timeout in
                seconds. (default: :obj:`30.0`)
            required_packages (Optional[List[str]], optional): A list of
                packages to install in the virtual environment.
                (default: :obj:`None`)
        """
        # TODO: Use CAMEL's Interpreter to execute the code
        super().__init__(extractor=extractor, timeout=timeout, **kwargs)
        self.venv_path: Optional[str] = None
        self.required_packages = required_packages or []

        if os.name == 'nt':  # Windows
            self.bin_dir = 'Scripts'
        else:  # Unix-like systems
            self.bin_dir = 'bin'

    async def _setup(self, **kwargs) -> None:
        r"""Set up a virtual environment and install required packages."""
        # Check if we're in a uv environment and use uv if available
        if kwargs.get("uv", False) or self._is_uv_environment():
            logger.info("[UV] Detected uv environment. Using uv for setup.")
            self._setup_with_uv()
            return

        self.venv_path = tempfile.mkdtemp()
        try:
            # Use system=True to ensure that the virtual environment uses the
            # system Python libraries
            venv.create(
                self.venv_path, with_pip=True, system_site_packages=True
            )
            logger.info(f"Virtual environment created at {self.venv_path}")
        except Exception as e:
            logger.error(f"Failed to create virtual environment: {e}")
            # Clean up resources before re-raising
            if self.venv_path and os.path.exists(self.venv_path):
                shutil.rmtree(self.venv_path)
                self.venv_path = None
            raise

        venv_pip = os.path.join(self.venv_path, self.bin_dir, "pip")

        if self.required_packages:
            try:
                # Add timeout to subprocess call
                subprocess.run(
                    [venv_pip, "install", *self.required_packages],
                    check=True,
                    capture_output=True,
                    timeout=self._timeout,
                )
                logger.info(
                    "Installed required packages: "
                    f"{', '.join(self.required_packages)}"
                )
            except subprocess.CalledProcessError as e:
                logger.error(
                    "Failed to install required packages: "
                    f"{e.stderr.decode().strip()}"
                )
                # Clean up resources before re-raising
                if self.venv_path and os.path.exists(self.venv_path):
                    shutil.rmtree(self.venv_path)
                    self.venv_path = None
                raise
            except subprocess.TimeoutExpired:
                logger.error(
                    f"Package installation timed out "
                    f"after {self._timeout} seconds"
                )
                if self.venv_path and os.path.exists(self.venv_path):
                    shutil.rmtree(self.venv_path)
                    self.venv_path = None
                raise

    def _is_uv_environment(self) -> bool:
        r"""Detect whether the current Python runtime is managed by uv."""
        return "UV_CACHE_DIR" in os.environ or "uv" in sys.executable

    def _setup_with_uv(self) -> None:
        r"""Create virtual environment and install packages using uv."""
        self.venv_path = tempfile.mkdtemp()
        try:
            subprocess.run(
                ["uv", "venv", "--python", sys.executable, self.venv_path],
                check=True,
                capture_output=True,
                timeout=self._timeout,
            )
            logger.info(
                f"[UV] Virtual environment created at {self.venv_path}"
            )
        except subprocess.CalledProcessError as e:
            logger.error(
                "[UV] Failed to create virtual environment:\n"
                f"{e.stderr.decode().strip()}"
            )
            # Clean up resources before re-raising
            if self.venv_path and os.path.exists(self.venv_path):
                shutil.rmtree(self.venv_path)
                self.venv_path = None
            raise
        except subprocess.TimeoutExpired:
            logger.error(
                f"[UV] Virtual environment creation timed "
                f"out after {self._timeout} seconds"
            )
            if self.venv_path and os.path.exists(self.venv_path):
                shutil.rmtree(self.venv_path)
                self.venv_path = None
            raise

        if self.required_packages:
            venv_python = os.path.join(
                self.venv_path,
                self.bin_dir,
                "python.exe" if os.name == 'nt' else "python",
            )
            try:
                subprocess.run(
                    [
                        "uv",
                        "pip",
                        "install",
                        "--python",
                        venv_python,
                        *self.required_packages,
                    ],
                    check=True,
                    capture_output=True,
                    timeout=self._timeout,
                )
                logger.info(
                    "[UV] Installed required packages via uv: "
                    f"{', '.join(self.required_packages)}"
                )
            except subprocess.CalledProcessError as e:
                logger.error(
                    "[UV] Failed to install required packages via uv:\n"
                    f"{e.stderr.decode().strip()}"
                )
                # Clean up resources before re-raising
                if self.venv_path and os.path.exists(self.venv_path):
                    shutil.rmtree(self.venv_path)
                    self.venv_path = None
                raise
            except subprocess.TimeoutExpired:
                logger.error(
                    f"[UV] Package installation timed "
                    f"out after {self._timeout} seconds"
                )
                if self.venv_path and os.path.exists(self.venv_path):
                    shutil.rmtree(self.venv_path)
                    self.venv_path = None
                raise

    async def _cleanup(self) -> None:
        r"""Clean up the virtual environment."""
        if self.venv_path:
            shutil.rmtree(self.venv_path)
            logger.info(f"Virtual environment at {self.venv_path} removed")
            self.venv_path = None

    async def _verify_implementation(
        self, solution: str, reference_answer: Optional[str]
    ) -> VerificationResult:
        r"""Executes the provided Python solution in an isolated environment
        and verifies its output against an expected ground truth expression.

        This method runs the solution in a subprocess inside a virtual
        environment. The ground truth is assumed to be a pure Python
        expression and is evaluated directly in the verifier process.

        If both executions are successful, the actual output is compared
        against the evaluated ground truth using semantic equality. If
        evaluation fails, string comparison is used as a fallback.

        Args:
            solution (str): The Python code or expression to execute and
                verify.
            reference_answer (Optional[str]): The expected value as a Python
             expression. If None, only execution success is verified.

        Returns:
            VerificationResult: Result of the verification process.
        """
        # Check for virtual environment setup
        if not self.venv_path:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message="Virtual environment is not set up.",
            )

        # If the solution is an expression, evaluate it directly
        if self._is_expression(solution):
            try:
                sol_val = ast.literal_eval(solution)
            except Exception as e:
                return VerificationResult(
                    status=VerificationOutcome.ERROR,
                    result="",
                    error_message=f"Expression evaluation error: {e}",
                )

            if reference_answer is not None:
                try:
                    gt_val = ast.literal_eval(reference_answer)
                except Exception as e:
                    return VerificationResult(
                        status=VerificationOutcome.ERROR,
                        result="",
                        error_message=f"Ground truth evaluation error: {e}",
                    )
                if sol_val == gt_val:
                    return VerificationResult(
                        status=VerificationOutcome.SUCCESS,
                        result=str(sol_val),
                    )
                else:
                    return VerificationResult(
                        status=VerificationOutcome.FAILURE,
                        result=str(sol_val),
                        error_message="Output mismatch: "
                        f"{sol_val} != {gt_val}",
                    )
            else:
                return VerificationResult(
                    status=VerificationOutcome.SUCCESS,
                    result=str(sol_val),
                )

        # Otherwise, run the code block,
        # which should already include a print(...) in the end
        venv_python = os.path.join(
            self.venv_path,
            self.bin_dir,
            "python.exe" if os.name == 'nt' else "python",
        )
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
            if sol_code != 0:
                return VerificationResult(
                    status=VerificationOutcome.ERROR,
                    result=sol_out,
                    error_message=f"Solution code error:\n{sol_err}",
                )

            if reference_answer is not None:
                try:
                    # First, try to evaluate the output as-is.
                    sol_val = ast.literal_eval(sol_out)
                except Exception as e:
                    logger.warning(f"Direct eval failed: {e}.")
                    sol_val = None

                if sol_val is not None:
                    try:
                        gt_val = ast.literal_eval(reference_answer)
                    except Exception as e:
                        return VerificationResult(
                            status=VerificationOutcome.ERROR,
                            result="",
                            error_message="Ground truth evaluation error:"
                            f"{e}",
                        )
                    if sol_val == gt_val:
                        return VerificationResult(
                            status=VerificationOutcome.SUCCESS,
                            result=sol_out,
                        )
                    else:
                        return VerificationResult(
                            status=VerificationOutcome.FAILURE,
                            result=sol_out,
                            error_message="Output mismatch: "
                            f"{sol_val} != {gt_val}",
                        )
                else:
                    # Fallback: string comparison
                    if sol_out.strip() == reference_answer.strip():
                        return VerificationResult(
                            status=VerificationOutcome.SUCCESS,
                            result=sol_out,
                        )
                    else:
                        return VerificationResult(
                            status=VerificationOutcome.FAILURE,
                            result=sol_out,
                            error_message="Fallback string mismatch: "
                            f"'{sol_out}' != '{reference_answer}'",
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
        r"""Executes a block of Python code in the virtual environment.

        The code is written to a temporary file, executed using the Python
        interpreter from the specified virtual environment, and
        its output and error streams are captured.

        Args:
            code (str): The Python code to execute.
            venv_path (str): The path to the virtual environment's Python
                binary.

        Returns:
            Tuple[str, str, int]: A tuple containing the stdout output,
            stderr output, and return code from the executed script.
        """
        # No longer checking for expressions since they're handled separately
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
            proc.returncode if proc.returncode is not None else -1,
        )

    def _is_expression(self, code: str) -> bool:
        r"""Determines whether a given string of code is a single expression.

        This utility uses Python's AST module to parse the code and checks if
        it consists of a single expression node.

        Args:
            code (str): The Python code to analyze.

        Returns:
            bool: True if the code is a single expression, False otherwise.
        """
        # Skip empty or whitespace-only strings
        if not code or code.isspace():
            return False

        try:
            # First try parsing as an expression - this is more reliable than
            # starting with literal_eval
            tree = ast.parse(code.strip(), mode='eval')
            # Check if it's a function call (like print()) - these should not
            # be treated as expressions
            if isinstance(tree.body, ast.Call):
                return False
            # If parsing succeeds in 'eval' mode and it's not a function call,
            # it's a valid expression
            return True
        except SyntaxError:
            # If parsing as expression fails, it's not a valid expression
            return False
        except Exception:
            # For any other parsing errors, try literal_eval as fallback for
            # simple literals
            try:
                ast.literal_eval(code)
                return True
            except Exception:
                return False
