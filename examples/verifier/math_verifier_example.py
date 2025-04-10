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

from camel.logger import get_logger
from camel.verifiers import MathVerifier

logger = get_logger(__name__)

# Initialize verifier with configuration
verifier = MathVerifier(float_rounding=6, numeric_precision=15)


async def main():
    r"""Run test cases demonstrating different verification scenarios."""

    print("\nStarting Math Verifier Examples\n")
    await verifier.setup()

    try:
        # Test case 1: Basic numerical equivalence (should succeed)
        print("=== Test 1: Basic Numerical ===")
        result = await verifier.verify(
            solution="0.333333", reference_answer="1/3"
        )
        print("Input: 0.333333 ≈ 1/3")
        print(f"Result: {result.status}")
        print(
            f"err: {result.error_message if result.error_message else 'None'}"
        )

        # Test case 2: LaTeX expressions (should succeed)
        print("=== Test 2: LaTeX Expression ===")
        result = await verifier.verify(
            solution=r"$\frac{1}{2}$", reference_answer=r"0.5"
        )
        print("Input: \\frac{1}{2} = 0.5")
        print(f"Result: {result.status}")
        print(
            f"err: {result.error_message if result.error_message else 'None'}"
        )

        # Test case 3: Deliberate mismatch (should fail)
        print("=== Test 3: Expected Failure ===")
        result = await verifier.verify(
            solution="0.5", reference_answer="0.3333"
        )
        print("Input: 0.5 ≠ 0.3333")
        print(f"Result: {result.status}")
        print(
            f"err: {result.error_message if result.error_message else 'None'}"
        )

    finally:
        await verifier.cleanup()
        print("Math Verifier Examples Completed")


if __name__ == "__main__":
    asyncio.run(main())

"""
===============================================================================
Starting Math Verifier Examples

=== Test 1: Basic Numerical ===
Input: 0.333333 ≈ 1/3
Result: VerificationOutcome.SUCCESS
err: None

=== Test 2: LaTeX Expression ===
Input: \frac{1}{2} = 0.5
Result: VerificationOutcome.SUCCESS
err: None

=== Test 3: Expected Failure ===
Input: 0.5 ≠ 0.3333
Result: VerificationOutcome.FAILURE
err: Solution does not match ground truth

Math Verifier Examples Completed
===============================================================================
"""
