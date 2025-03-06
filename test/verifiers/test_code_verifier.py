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

from camel.interpreters import SubprocessInterpreter
from camel.verifiers.code_verifier import CodeVerifier
from camel.verifiers.models import (
    VerificationOutcome,
    VerifierInput,
)


@pytest.fixture
def code_verifier():
    r"""Fixture to provide a CodeVerifier instance."""
    return CodeVerifier(timeout=5.0)


@pytest.mark.asyncio
async def test_code_verifier_setup_and_cleanup(code_verifier):
    r"""Test setup and cleanup of CodeVerifier."""
    await code_verifier.setup()
    assert isinstance(code_verifier.interpreter, SubprocessInterpreter)

    await code_verifier.cleanup()


@pytest.mark.asyncio
async def test_code_verifier_execution_success(code_verifier):
    r"""Test successful execution of a Python script."""
    await code_verifier.setup()

    script = 'print("Hello, World!")'
    result = await code_verifier._verify_implementation(
        VerifierInput(llm_response=script)
    )

    assert result.status == VerificationOutcome.SUCCESS
    assert result.result.strip() == "Hello, World!"

    await code_verifier.cleanup()


@pytest.mark.asyncio
async def test_code_verifier_execution_failure(code_verifier):
    r"""Test execution failure due to syntax error."""
    await code_verifier.setup()

    script = 'print("Hello"'  # Syntax error
    result = await code_verifier._verify_implementation(
        VerifierInput(llm_response=script)
    )

    assert result.status == VerificationOutcome.SUCCESS
    assert "SyntaxError" in result.result or "error" in result.result.lower()
    await code_verifier.cleanup()


@pytest.mark.asyncio
async def test_code_verifier_execution_timeout(code_verifier):
    r"""Test execution timeout handling."""
    code_verifier._timeout = 1  # Short timeout for testing
    await code_verifier.setup()

    script = 'import time; time.sleep(5)'
    result = await code_verifier._verify_implementation(
        VerifierInput(llm_response=script)
    )

    assert result.status == VerificationOutcome.TIMEOUT
    assert "Execution timed out" in result.error_message

    await code_verifier.cleanup()


@pytest.mark.asyncio
async def test_code_verifier_output_mismatch(code_verifier):
    r"""Test verification when output does not match ground truth."""
    await code_verifier.setup()

    script = 'print("Wrong output")'
    result = await code_verifier._verify_implementation(
        VerifierInput(llm_response=script, ground_truth="Expected output")
    )

    assert result.status == VerificationOutcome.FAILURE
    assert result.error_message == "Output doesn't match ground truth"

    await code_verifier.cleanup()


@pytest.mark.asyncio
async def test_code_verifier_correct_output_matching(code_verifier):
    r"""Test verification when output matches ground truth."""
    await code_verifier.setup()

    script = 'print("Expected output")'
    result = await code_verifier._verify_implementation(
        VerifierInput(llm_response=script, ground_truth="Expected output")
    )

    assert result.status == VerificationOutcome.SUCCESS
    assert result.result.strip() == "Expected output"

    await code_verifier.cleanup()


@pytest.mark.asyncio
async def test_code_verifier_batch_processing():
    r"""Test batch processing of multiple verifications."""
    verifier = CodeVerifier(max_parallel=2)
    await verifier.setup()

    inputs = [
        VerifierInput(llm_response='print("Test 1")', ground_truth="Test 1"),
        VerifierInput(llm_response='print("Test 2")', ground_truth="Test 2"),
        VerifierInput(llm_response='print("Test 3")', ground_truth="Test 3"),
    ]

    results = await verifier.verify_batch(inputs)

    assert len(results) == 3
    assert all(r.status == VerificationOutcome.SUCCESS for r in results)

    await verifier.cleanup()


@pytest.mark.asyncio
async def test_code_verifier_with_custom_interpreter():
    r"""Test CodeVerifier with a custom interpreter."""
    # Create a custom interpreter
    custom_interpreter = SubprocessInterpreter(require_confirm=False)
    verifier = CodeVerifier(interpreter=custom_interpreter)
    await verifier.setup()

    script = 'print("Using custom interpreter")'
    result = await verifier._verify_implementation(
        VerifierInput(llm_response=script)
    )

    assert result.status == VerificationOutcome.SUCCESS
    assert "Using custom interpreter" in result.result

    await verifier.cleanup()
