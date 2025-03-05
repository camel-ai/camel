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

import time
from typing import Optional

from camel.logger import get_logger
from camel.verifiers.base import BaseVerifier
from camel.verifiers.models import (
    VerificationOutcome,
    VerificationResult,
    VerifierInput,
)

logger = get_logger(__name__)


class MedicalVerifier(BaseVerifier):
    r"""Verifier for medical diagnoses.

    This verifier compares the extracted diagnosis from the LLM response
    with the expected answer (ground truth) to determine if the diagnosis
    is correct.
    """

    def __init__(
        self,
        exact_match: bool = False,
        case_sensitive: bool = False,
        timeout: Optional[float] = 30.0,
    ):
        r"""Initialize the MedicalVerifier.

        Args:
            exact_match (bool): Whether to require exact string matching.
                If False, will check if the ground truth is contained in
                the response. (default: :obj:`False`)
            case_sensitive (bool): Whether to perform case-sensitive
                comparison. (default: :obj:`False`)
            timeout (Optional[float]): Timeout in seconds for verification.
                (default: :obj:`30.0`)
        """
        super().__init__(timeout=timeout)
        self.exact_match = exact_match
        self.case_sensitive = case_sensitive

    async def _setup(self) -> None:
        r"""Set up the verifier."""
        # No specific setup needed for this verifier
        pass

    async def _cleanup(self) -> None:
        r"""Clean up the verifier."""
        # No specific cleanup needed for this verifier
        pass

    async def _verify_implementation(
        self, result: VerifierInput
    ) -> VerificationResult:
        r"""Verify if the extracted diagnosis matches the ground truth.

        Args:
            result (VerifierInput): The input containing the extracted
                diagnosis and ground truth.

        Returns:
            VerificationResult: The verification result indicating success
                or failure.
        """
        start_time = time.time()

        # Get the extracted diagnosis and ground truth
        extracted_diagnosis = result.llm_response
        ground_truth = result.ground_truth

        if not ground_truth:
            logger.warning("No ground truth provided for verification")
            return VerificationResult(
                status=VerificationOutcome.ERROR,
                result="No ground truth provided",
                duration=time.time() - start_time,
                error_message="Ground truth is required for verification",
            )

        # Prepare strings for comparison based on case sensitivity
        if not self.case_sensitive:
            extracted_diagnosis = extracted_diagnosis.lower()
            ground_truth = ground_truth.lower()

        # Perform verification based on matching strategy
        if self.exact_match:
            is_correct = extracted_diagnosis == ground_truth
        else:
            # Check if the extracted diagnosis contains the ground truth
            # or vice versa (more flexible matching)
            is_correct = (
                extracted_diagnosis in ground_truth
                or ground_truth in extracted_diagnosis
            )

        # Create verification result
        if is_correct:
            status = VerificationOutcome.SUCCESS
            result_msg = "Diagnosis matches ground truth"
        else:
            status = VerificationOutcome.FAILURE
            result_msg = (
                f"Diagnosis mismatch. Expected: '{ground_truth}', "
                f"Got: '{extracted_diagnosis}'"
            )

        return VerificationResult(
            status=status,
            result=result_msg,
            duration=time.time() - start_time,
            metadata={
                "extracted_diagnosis": result.llm_response,
                "ground_truth": result.ground_truth,
                "exact_match": self.exact_match,
                "case_sensitive": self.case_sensitive,
            },
        )
