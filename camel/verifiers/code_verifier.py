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
from typing import Optional

from camel.interpreters import BaseInterpreter, SubprocessInterpreter
from camel.logger import get_logger
from camel.verifiers.base import BaseVerifier
from camel.verifiers.models import (
    VerificationOutcome,
    VerificationResult,
    VerifierInput,
)

logger = get_logger(__name__)


class CodeVerifier(BaseVerifier):
    r"""Verifier for code solutions using an interpreter.

    This verifier executes code through an interpreter and verifies the output
    against an expected ground truth.
    """

    def __init__(
        self,
        interpreter: Optional[BaseInterpreter] = None,
        max_parallel: Optional[int] = None,
        timeout: Optional[float] = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        initial_batch_size: Optional[int] = None,
        **kwargs,
    ):
        r"""Initialize the code verifier.

        Args:
            interpreter (Optional[BaseInterpreter]): The interpreter to use for
                code execution.If None, a SubprocessInterpreter will be created
                (default: None)
            max_parallel (Optional[int]): Max number of parallel verifications
            timeout (Optional[float]): Execution timeout in seconds
                (default: 30.0)
            max_retries (int): Max number of retries for failed verifications
            retry_delay (float): Delay between retries in seconds
            initial_batch_size (Optional[int]): Initial batch size for
                parallel processing
            **kwargs: Additional parameters for the base verifier
        """
        super().__init__(
            max_parallel=max_parallel,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            initial_batch_size=initial_batch_size,
            **kwargs,
        )

        self.interpreter: BaseInterpreter
        if interpreter is None:
            self.interpreter = SubprocessInterpreter(
                require_confirm=False,
            )
        else:
            self.interpreter = interpreter

        logger.info(
            f"Initialized CodeVerifier with interpreter"
            f"{self.interpreter.__class__.__name__}"
        )

    async def _setup(self) -> None:
        r"""Set up the verifier and the interpreter if needed."""
        pass

    async def _cleanup(self) -> None:
        r"""Clean up the verifier and the interpreter if needed."""
        pass

    async def _verify_implementation(
        self, result: VerifierInput
    ) -> VerificationResult:
        r"""Execute code and verify the output against ground truth.

        Args:
            result (VerifierInput): Contains the code to execute and optional
                ground truth for comparison.

        Returns:
            VerificationResult: Contains verification status, execution output,
                and error messages if any.
        """
        script = result.llm_response.strip()
        language = "python"

        try:
            # Run the code using the interpreter
            output_result = await asyncio.wait_for(
                self._run_code(script, language), timeout=self._timeout
            )

            # If ground truth is provided, compare it with the result
            if result.ground_truth is not None:
                # Normalize both strings by removing extra whitespace
                normalized_output = ' '.join(output_result.strip().split())
                normalized_truth = ' '.join(
                    str(result.ground_truth).strip().split()
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

    async def _run_code(self, code: str, language: str) -> str:
        """Run code using the interpreter.

        Args:
            code (str): Code to execute
            language (str): Programming language

        Returns:
            str: Output from code execution
        """
        try:
            # Handle both sync and async interpreters
            if hasattr(self.interpreter, "run_async"):
                return await self.interpreter.run_async(code, language)
            else:
                # Run synchronously but in a thread to avoid blocking
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, self.interpreter.run, code, language
                )
        except Exception as e:
            logger.error(f"Error running code: {e}")
            raise
