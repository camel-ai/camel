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
import os

import pytest

from camel.verifiers.models import (
    VerificationOutcome,
)
from camel.verifiers.python_verifier import PythonVerifier


@pytest.fixture
def python_verifier():
    r"""Fixture to provide a PythonVerifier instance."""
    return PythonVerifier(timeout=5.0, required_packages=["numpy"])


@pytest.mark.asyncio
async def test_python_verifiersetup_andcleanup(
    python_verifier: PythonVerifier,
):
    r"""Test setup and cleanup of PythonVerifier."""
    await python_verifier.setup(uv=True)
    assert python_verifier.venv_path is not None
    assert os.path.exists(python_verifier.venv_path)

    await python_verifier.cleanup()
    assert python_verifier.venv_path is None or not os.path.exists(
        python_verifier.venv_path
    )


@pytest.mark.asyncio
async def test_python_verifier_execution_success(python_verifier):
    r"""Test successful execution of a Python script."""
    await python_verifier.setup(uv=True)

    script = 'print("Hello, World!")'
    result = await python_verifier.verify(
        solution=script, reference_answer=None
    )
    assert result.status == VerificationOutcome.SUCCESS
    assert result.result == "Hello, World!"

    await python_verifier.cleanup()


@pytest.mark.asyncio
async def test_python_verifier_execution_failure(python_verifier):
    r"""Test execution failure due to syntax error."""
    await python_verifier.setup(uv=True)

    script = 'print("Hello"'  # Syntax error
    result = await python_verifier._verify_implementation(
        solution=script, reference_answer=None
    )

    assert result.status == VerificationOutcome.ERROR
    assert "SyntaxError" in result.error_message

    await python_verifier.cleanup()


@pytest.mark.asyncio
async def test_python_verifier_execution_timeout(python_verifier):
    r"""Test execution timeout handling."""
    python_verifier.timeout = 1  # Short timeout for testing
    await python_verifier.setup(uv=True)

    script = 'import time; time.sleep(5)'
    result = await python_verifier._verify_implementation(
        solution=script, reference_answer=None
    )

    assert result.status == VerificationOutcome.TIMEOUT
    assert "Execution timed out" in result.error_message

    await python_verifier.cleanup()


@pytest.mark.asyncio
async def test_python_verifier_output_mismatch(python_verifier):
    r"""Test verification when output does not match ground truth."""
    await python_verifier.setup(uv=True)

    script = 'print("Wrong output")'
    result = await python_verifier._verify_implementation(
        solution=script, reference_answer="Expected output"
    )

    assert result.status == VerificationOutcome.FAILURE
    assert (
        result.error_message
        == "Fallback string mismatch: 'Wrong output' != 'Expected output'"
    )

    await python_verifier.cleanup()


@pytest.mark.asyncio
async def test_python_verifier_correct_output_matching(python_verifier):
    r"""Test verification when output matches ground truth."""
    await python_verifier.setup(uv=True)

    script = 'print("Expected output")'
    result = await python_verifier._verify_implementation(
        solution=script, reference_answer="Expected output"
    )

    assert result.status == VerificationOutcome.SUCCESS
    assert result.result == "Expected output"

    await python_verifier.cleanup()


@pytest.mark.asyncio
async def test_python_verifier_no_venv_error():
    r"""Test verification error when no virtual environment is set up."""
    verifier = PythonVerifier()
    script = 'print("Hello")'
    result = await verifier._verify_implementation(
        solution=script, reference_answer=None
    )

    assert result.status == VerificationOutcome.ERROR
    assert "Virtual environment is not set up" in result.error_message


@pytest.mark.asyncio
async def test_python_verifier_with_numpy(python_verifier):
    r"""Test execution with numpy installed in the virtual environment."""
    await python_verifier.setup(uv=True)

    script = 'import numpy as np; print(np.array([1, 2, 3]))'
    result = await python_verifier._verify_implementation(
        solution=script, reference_answer=None
    )

    assert result.status == VerificationOutcome.SUCCESS
    assert "[1 2 3]" in result.result
    await python_verifier.cleanup()


@pytest.mark.parametrize(
    "a,b,tol,expected",
    [
        (0.123456, 0.123457, 1e-5, True),
        (0.123456, 0.123467, 1e-5, False),
        ([1.0, 2.0], [1.0, 2.000001], 1e-5, True),
        ([1.0, 2.0], [1.0, 2.1], 1e-5, False),
        ({'a': 1.0, 'b': 2.0}, {'a': 1.0000001, 'b': 2.0}, 1e-5, True),
        ({'a': 1.0, 'b': 2.0}, {'a': 1.0001, 'b': 2.0}, 1e-5, False),
        ((1.0, 2.0), (1.0, 2.000001), 1e-5, True),
        ((1.0, 2.0), (1.0, 2.01), 1e-5, False),
        ({1.0, 2.0}, {2.000001, 1.0}, 1e-5, True),
        ({1.0, 2.0}, {2.1, 1.0}, 1e-5, False),
        ({1.0, 1.000001}, {1.000002, 2.0}, 1e-5, False),
        ({"x": [1.0, 2.0]}, {"x": [1.000001, 2.0]}, 1e-5, True),
        ({"x": [1.0, 2.0]}, {"x": [1.1, 2.0]}, 1e-5, False),
    ],
)
def test_is_equal_with_tolerance(a, b, tol, expected):
    r"""Test the function calculating whether two floats are equal
    given tolerance"""
    verifier = PythonVerifier(float_tolerance=tol)
    assert verifier._is_equal_with_tolerance(a, b) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "script,expected_output,tol,should_pass",
    [
        # Float scalar
        ("0.123456", "0.123457", 1e-5, True),
        ("0.123456", "0.123467", 1e-5, False),
        # Lists
        ("[1.0, 2.0]", "[1.0, 2.000001]", 1e-5, True),
        ("[1.0, 2.0]", "[1.0, 2.1]", 1e-5, False),
        # Dicts
        ("{'a': 1.0, 'b': 2.0}", "{'a': 1.000001, 'b': 2.0}", 1e-5, True),
        ("{'a': 1.0, 'b': 2.0}", "{'a': 1.1, 'b': 2.0}", 1e-5, False),
        # Sets
        ("{1.0, 2.0}", "{1.0, 2.000001}", 1e-5, True),
        ("{1.0, 2.0}", "{1.0, 2.1}", 1e-5, False),
        # Tuples
        ("(1.0, 2.0)", "(1.0, 2.000001)", 1e-5, True),
        ("(1.0, 2.0)", "(1.0, 2.1)", 1e-5, False),
        # Mixed nesting
        ("{'a': [1.0, 2.0]}", "{'a': [1.000001, 2.0]}", 1e-5, True),
        ("{'a': [1.0, 2.0]}", "{'a': [1.1, 2.0]}", 1e-5, False),
        # Same as above, but as code blocks
        ("print(0.123456)", "0.123457", 1e-5, True),
        ("print(0.123456)", "0.123467", 1e-5, False),
        ("print([1.0, 2.0])", "[1.0, 2.000001]", 1e-5, True),
        ("print([1.0, 2.0])", "[1.0, 2.1]", 1e-5, False),
        (
            "print({'a': 1.0, 'b': 2.0})",
            "{'a': 1.000001, 'b': 2.0}",
            1e-5,
            True,
        ),
        ("print({'a': 1.0, 'b': 2.0})", "{'a': 1.1, 'b': 2.0}", 1e-5, False),
        ("print({1.0, 2.0})", "{1.0, 2.000001}", 1e-5, True),
        ("print({1.0, 2.0})", "{1.0, 2.1}", 1e-5, False),
        # This test should fail with the simplified all(any(...)) logic
        ("print({1.0, 1.000001})", "{1.000002, 2.0}", 1e-5, False),
    ],
)
async def test_verify_with_float_tolerance(
    script, expected_output, tol, should_pass
):
    r"""Test verifier end-to-end with float tolerance"""
    verifier = PythonVerifier(float_tolerance=tol)
    await verifier.setup(uv=True)

    result = await verifier.verify(
        solution=script, reference_answer=expected_output
    )

    if should_pass:
        assert (
            result.status == VerificationOutcome.SUCCESS
        ), f"Expected success, got {result}"
    else:
        assert (
            result.status == VerificationOutcome.FAILURE
        ), f"Expected failure, got {result}"

    await verifier.cleanup()
