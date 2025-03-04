import pytest
import os

from camel.verifiers.python_verifier import PythonVerifier
from camel.verifiers.models import (
    VerificationOutcome,
    VerifierInput,
)


@pytest.fixture
def python_verifier():
    r"""Fixture to provide a PythonVerifier instance."""
    return PythonVerifier(timeout=5.0, required_packages=["numpy"])


@pytest.mark.asyncio
async def test_python_verifier_setup_and_cleanup(python_verifier):
    r"""Test setup and cleanup of PythonVerifier."""
    await python_verifier._setup()
    assert python_verifier.venv_path is not None
    assert os.path.exists(python_verifier.venv_path)
    
    await python_verifier._cleanup()
    assert python_verifier.venv_path is None or not os.path.exists(python_verifier.venv_path)


@pytest.mark.asyncio
async def test_python_verifier_execution_success(python_verifier):
    r"""Test successful execution of a Python script."""
    await python_verifier._setup()

    script = 'print("Hello, World!")'
    result = await python_verifier._verify_implementation(
        VerifierInput(llm_response=script)
    )

    assert result.status == VerificationOutcome.SUCCESS
    assert result.result == "Hello, World!"

    await python_verifier._cleanup()


@pytest.mark.asyncio
async def test_python_verifier_execution_failure(python_verifier):
    r"""Test execution failure due to syntax error."""
    await python_verifier._setup()

    script = 'print("Hello"'  # Syntax error
    result = await python_verifier._verify_implementation(
        VerifierInput(llm_response=script)
    )

    assert result.status == VerificationOutcome.ERROR
    assert "SyntaxError" in result.error_message

    await python_verifier._cleanup()


@pytest.mark.asyncio
async def test_python_verifier_execution_timeout(python_verifier):
    r"""Test execution timeout handling."""
    python_verifier.timeout = 1  # Short timeout for testing
    await python_verifier._setup()

    script = 'import time; time.sleep(5)'
    result = await python_verifier._verify_implementation(
        VerifierInput(llm_response=script)
    )

    assert result.status == VerificationOutcome.TIMEOUT
    assert "Execution timed out" in result.error_message

    await python_verifier._cleanup()


@pytest.mark.asyncio
async def test_python_verifier_output_mismatch(python_verifier):
    r"""Test verification when output does not match ground truth."""
    await python_verifier._setup()

    script = 'print("Wrong output")'
    result = await python_verifier._verify_implementation(
        VerifierInput(llm_response=script, ground_truth="Expected output")
    )

    assert result.status == VerificationOutcome.FAILURE
    assert result.error_message == "Output doesn't match ground truth"

    await python_verifier._cleanup()


@pytest.mark.asyncio
async def test_python_verifier_correct_output_matching(python_verifier):
    r"""Test verification when output matches ground truth."""
    await python_verifier._setup()

    script = 'print("Expected output")'
    result = await python_verifier._verify_implementation(
        VerifierInput(llm_response=script, ground_truth="Expected output")
    )

    assert result.status == VerificationOutcome.SUCCESS
    assert result.result == "Expected output"

    await python_verifier._cleanup()


@pytest.mark.asyncio
async def test_python_verifier_no_venv_error():
    r"""Test verification error when no virtual environment is set up."""
    verifier = PythonVerifier()
    script = 'print("Hello")'
    result = await verifier._verify_implementation(
        VerifierInput(llm_response=script)
    )

    assert result.status == VerificationOutcome.ERROR
    assert "Virtual environment is not set up" in result.error_message


@pytest.mark.asyncio
async def test_python_verifier_with_numpy(python_verifier):
    r"""Test execution with numpy installed in the virtual environment."""
    await python_verifier._setup()
    
    script = 'import numpy as np; print(np.array([1, 2, 3]))'
    result = await python_verifier._verify_implementation(
        VerifierInput(llm_response=script)
    )
    
    assert result.status == VerificationOutcome.SUCCESS
    assert "[1 2 3]" in result.result
    await python_verifier._cleanup()