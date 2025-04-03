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

from typing import Optional

from camel.extractors.base import BaseExtractor
from camel.logger import get_logger
from camel.verifiers import BaseVerifier
from camel.verifiers.models import VerificationOutcome, VerificationResult

logger = get_logger(__name__)


class MathVerifier(BaseVerifier):
    r"""Verifier for mathematical expressions using Math-Verify.

    Features:
    - Supports LaTeX and plain mathematical expressions
    - Handles complex numbers, matrices, and sets
    - Configurable precision for floating-point comparisons
    - Optional LaTeX wrapping to ensure proper parsing and rendering
    - Comprehensive error handling and logging
    """

    def __init__(
        self,
        extractor: Optional[BaseExtractor] = None,
        timeout: Optional[float] = 30.0,
        float_rounding: int = 6,
        numeric_precision: int = 15,
        enable_wrapping: Optional[bool] = False,
        **kwargs,
    ):
        r"""Initializes the MathVerifier.

        Args:
            extractor (Optional[BaseExtractor], optional): The extractor to use
                for extracting code from the solution. (default: :obj:`None`)
            timeout (Optional[float], optional): The execution timeout in
                seconds. (default: :obj:`30.0`)
            float_rounding (int, optional): The number of decimal places to
                round floating-point numbers. (default: :obj:`6`)
            numeric_precision (int, optional): The numeric precision for
                floating-point comparisons. (default: :obj:`15`)
            enable_wrapping (Optional[bool], optional): Whether to wrap LaTeX
                expressions in math mode delimiters. (default: :obj:`False`)
        """
        super().__init__(extractor=extractor, timeout=timeout, **kwargs)
        self.float_rounding = float_rounding
        self.numeric_precision = numeric_precision
        self.enable_wrapping = enable_wrapping

    @staticmethod
    def _latex_wrapping(s: str) -> str:
        r"""Wrap a LaTeX expression in math mode delimiters.

        This function checks whether the input string is already in a LaTeX
        math environment (e.g., $, \[, \begin{}, etc.). If not, it wraps the
        expression in $$...$$ to ensure proper parsing and rendering as a
        mathematical expression.

        Args:
            s (str): The input LaTeX string.

        Returns:
            str: The LaTeX string wrapped in math mode if necessary.
        """
        s_stripped = s.strip()
        if (
            not any(
                s_stripped.startswith(prefix)
                for prefix in ("$", "\\(", "\\[", "\\begin")
            )
            and "\\boxed" not in s_stripped
        ):
            s = f"$$ {s_stripped} $$"
        return s

    async def _setup(self, **kwargs) -> None:
        r"""No special setup needed for math verification."""
        pass

    async def _cleanup(self) -> None:
        r"""No cleanup needed for math verification."""
        pass

    async def _verify_implementation(
        self, solution: str, reference_answer: Optional[str]
    ) -> VerificationResult:
        r"""Verify mathematical expressions using Math-Verify.

        Args:
            solution: The solution to verify
            reference_answer: The expected answer to compare against

        Returns:
            VerificationResult containing the verification status and details
        """
        from math_verify import parse, verify
        from math_verify.parser import (
            ExprExtractionConfig,
            LatexExtractionConfig,
        )

        if reference_answer is None:
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message=(
                    "Ground truth is required for " "mathematical verification"
                ),
            )

        try:
            # Apply LaTeX wrapping if enabled
            if self.enable_wrapping:
                solution = self._latex_wrapping(solution)
                reference_answer = self._latex_wrapping(reference_answer)
                logger.debug("Applied LaTeX wrapping")

            # Parse both expressions with LaTeX and plain expression support
            parsed_reference_answer = parse(
                reference_answer,
                extraction_config=[
                    LatexExtractionConfig(boxed_match_priority=0),
                    ExprExtractionConfig(),
                ],
            )
            parsed_solution = parse(
                solution,
                extraction_config=[
                    LatexExtractionConfig(),
                    ExprExtractionConfig(),
                ],
            )

            if not parsed_reference_answer or not parsed_solution:
                return VerificationResult(
                    status=VerificationOutcome.ERROR,
                    result="",
                    error_message="Failed to parse expressions",
                )

            # Order matters! reference_answer must be first argument
            is_correct = verify(
                parsed_reference_answer,
                parsed_solution,
                float_rounding=self.float_rounding,
                numeric_precision=self.numeric_precision,
            )

            if is_correct:
                logger.debug("Mathematical verification succeeded")
                return VerificationResult(
                    status=VerificationOutcome.SUCCESS, result=solution
                )
            else:
                logger.debug("Mathematical verification failed")
                return VerificationResult(
                    status=VerificationOutcome.FAILURE,
                    result=solution,
                    error_message="Solution does not match ground truth",
                )

        except Exception as error:
            logger.error(f"Mathematical verification error: {error!s}")
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="",
                error_message=f"Mathematical verification error: {error!s}",
            )
