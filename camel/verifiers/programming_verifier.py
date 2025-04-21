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
import sys
import tempfile
import traceback
from typing import Any, Dict, List, Optional

from camel.extractors.base import BaseExtractor
from camel.logger import get_logger
from camel.verifiers import BaseVerifier

from .models import VerificationOutcome, VerificationResult

logger = get_logger(__name__)


class ProgrammingVerifier(BaseVerifier):
    r"""The ProgrammingVerifier class verifies programming solutions by executing
    test cases against the solution.

    This verifier takes a solution (code) and a rationale (test cases) and
    verifies if the solution passes all the test cases. The test cases are
    expected to be in the form of Python assert statements.

    Features:
    - Executes the solution against a series of test cases
    - Provides detailed error messages for failing test cases
    - Handles timeouts and execution errors
    """

    def __init__(
        self,
        extractor: Optional[BaseExtractor] = None,
        timeout: Optional[float] = 30.0,
        **kwargs,
    ):
        r"""Initializes the ProgrammingVerifier.

        Args:
            extractor (Optional[BaseExtractor], optional): The extractor to use
                for extracting code from the solution. (default: :obj:`None`)
            timeout (Optional[float], optional): The execution timeout in
                seconds. (default: :obj:`30.0`)
        """
        super().__init__(extractor=extractor, timeout=timeout, **kwargs)

    async def _setup(self, **kwargs) -> None:
        r"""Set up the verifier. No special setup needed for this verifier."""
        pass

    async def _cleanup(self) -> None:
        r"""Clean up the verifier. No special cleanup needed for this verifier."""
        pass

    async def _verify_implementation(
        self, solution: str, reference_answer: Optional[str]
    ) -> VerificationResult:
        r"""Executes the provided solution against test cases in the reference_answer.

        This method combines the solution with test cases from the reference_answer
        and executes them to verify if the solution passes all the test cases.

        Args:
            solution (str): The programming solution to verify.
            reference_answer (Optional[str]): The test cases to run against the
                solution. Expected to be Python assert statements.

        Returns:
            VerificationResult: Result of the verification process.

        Note: 
            def candidate(nums, target): must be defined in the solution.
        
        """
        if not reference_answer:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message="No test cases provided in the reference answer",
            )

        # Ensure the test cases include a call to check(candidate)
        reference_answer = reference_answer + "\ncheck(candidate)"

        # Create a temporary file to execute the code
        with tempfile.NamedTemporaryFile(
            suffix=".py", mode="w+", delete=False
        ) as temp_file:
            try:
                # Combine the solution and test cases
                combined_code = f"{solution}\n\n{reference_answer}"
                temp_file.write(combined_code)
                temp_file.flush()
                temp_file_path = temp_file.name

                # Execute the combined code
                cmd = [sys.executable, temp_file_path]
                
                try:
                    # Run the code with timeout
                    proc = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    
                    try:
                        stdout, stderr = await asyncio.wait_for(
                            proc.communicate(), timeout=self._timeout
                        )
                        stdout_str = stdout.decode("utf-8", errors="replace")
                        stderr_str = stderr.decode("utf-8", errors="replace")
                        
                        if proc.returncode == 0:
                            # All tests passed
                            return VerificationResult(
                                status=VerificationOutcome.SUCCESS,
                                result="All test cases passed",
                                metadata={
                                    "stdout": stdout_str,
                                    "stderr": stderr_str,
                                    "return_code": proc.returncode,
                                },
                            )
                        else:
                            # Some tests failed
                            return VerificationResult(
                                status=VerificationOutcome.FAILURE,
                                result="",
                                error_message=f"Test cases failed: {stderr_str}",
                                metadata={
                                    "stdout": stdout_str,
                                    "stderr": stderr_str,
                                    "return_code": proc.returncode,
                                },
                            )
                    except asyncio.TimeoutError:
                        # Kill the process if it times out
                        try:
                            proc.kill()
                        except ProcessLookupError:
                            pass
                        
                        return VerificationResult(
                            status=VerificationOutcome.TIMEOUT,
                            result="",
                            error_message=f"Execution timed out after {self._timeout} seconds",
                        )
                except Exception as e:
                    return VerificationResult(
                        status=VerificationOutcome.ERROR,
                        result="",
                        error_message=f"Error executing code: {str(e)}",
                        metadata={"traceback": traceback.format_exc()},
                    )
            finally:
                # Clean up the temporary file
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete temporary file: {e}")

    @staticmethod
    def format_test_cases(test_cases: List[Dict[str, Any]]) -> str:
        r"""Formats test cases into Python assert statements.

        Args:
            test_cases (List[Dict[str, Any]]): List of test case dictionaries.
                Each dictionary should have 'input' and 'expected' keys.

        Returns:
            str: Formatted test cases as Python assert statements.
        """
        formatted_tests = []
        for i, test in enumerate(test_cases):
            inputs = ", ".join([f"{k} = {v}" for k, v in test["input"].items()])
            expected = test["expected"]
            formatted_tests.append(f"assert candidate({inputs}) == {expected}")
        
        return "def check(candidate):\n    " + "\n    ".join(formatted_tests)
