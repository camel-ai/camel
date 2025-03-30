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

import pytest

from camel.verifiers import MathVerifier
from camel.verifiers.models import VerificationOutcome


@pytest.mark.asyncio
async def test_math_verifier_basic():
    verifier = MathVerifier()
    try:
        # Test basic numerical equivalence
        result = await verifier.verify("0.5", "1/2")
        assert result.status == VerificationOutcome.SUCCESS
        assert result.error_message is None

        # Test LaTeX expressions
        result = await verifier.verify(r"$\frac{1}{2}$", "0.5")
        assert result.status == VerificationOutcome.SUCCESS
        assert result.error_message is None

        # Test deliberate mismatch
        result = await verifier.verify("0.5", "0.3333")
        assert result.status == VerificationOutcome.FAILURE
        assert result.error_message is not None

    finally:
        await verifier.cleanup()


@pytest.mark.asyncio
async def test_math_verifier_complex():
    verifier = MathVerifier()
    try:
        # Test complex expressions
        result = await verifier.verify(
            r"$\frac{1}{2} + \frac{1}{3}$", r"$\frac{5}{6}$"
        )
        assert result.status == VerificationOutcome.SUCCESS
        assert result.error_message is None

        # Test algebraic expressions
        result = await verifier.verify(r"$x^2 + 2x + 1$", r"$(x + 1)^2$")
        assert result.status == VerificationOutcome.SUCCESS
        assert result.error_message is None

    finally:
        await verifier.cleanup()


@pytest.mark.asyncio
async def test_math_verifier_precision():
    verifier = MathVerifier(float_rounding=3)
    try:
        # Test with custom precision
        result = await verifier.verify("0.3333", "1/3")
        assert result.status == VerificationOutcome.SUCCESS
        assert result.error_message is None

        # Test precision failure
        result = await verifier.verify("0.33", "1/3")
        assert result.status == VerificationOutcome.FAILURE
        assert result.error_message is not None

    finally:
        await verifier.cleanup()
