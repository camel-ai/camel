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
import contextlib
import os
from unittest.mock import patch

import pytest

from camel.interpreters import (
    DockerInterpreter,
    E2BInterpreter,
    InternalPythonInterpreter,
    JupyterKernelInterpreter,
    SubprocessInterpreter,
)
from camel.verifiers.models import (
    VerificationOutcome,
    VerifierInput,
)
from camel.verifiers.python_verifier import PythonVerifier


@pytest.fixture
def python_verifier():
    r"""Fixture to provide a PythonVerifier instance."""
    return PythonVerifier(timeout=5.0, required_packages=["numpy"])


# Context manager for automatic setup and cleanup
@contextlib.asynccontextmanager
async def verifier_context(verifier):
    r"""Context manager to handle setup and cleanup of a verifier."""
    try:
        await verifier._setup()
        yield verifier
    finally:
        await verifier._cleanup()


@pytest.mark.asyncio
async def test_python_verifier_setup_and_cleanup(python_verifier):
    r"""Test setup and cleanup of PythonVerifier."""
    await python_verifier._setup()
    assert python_verifier.venv_path is not None
    assert os.path.exists(python_verifier.venv_path)

    path = python_verifier.venv_path

    await python_verifier._cleanup()
    assert python_verifier.venv_path is None
    assert not os.path.exists(path)


@pytest.mark.asyncio
async def test_python_verifier_execution_success(python_verifier):
    r"""Test successful execution of a Python script."""
    async with verifier_context(python_verifier) as verifier:
        script = 'print("Hello, World!")'
        result = await verifier._verify_implementation(
            VerifierInput(llm_response=script)
        )

        assert result.status == VerificationOutcome.SUCCESS
        assert result.result == "Hello, World!\n"


@pytest.mark.asyncio
async def test_python_verifier_execution_failure(python_verifier):
    r"""Test execution failure due to syntax error."""
    async with verifier_context(python_verifier) as verifier:
        script = 'print("Hello"'  # Syntax error
        result = await verifier._verify_implementation(
            VerifierInput(llm_response=script)
        )

        assert result.status == VerificationOutcome.ERROR
        assert "SyntaxError" in result.result


@pytest.mark.asyncio
async def test_python_verifier_execution_timeout(python_verifier):
    r"""Test execution timeout handling."""
    # Set timeout before creating context
    python_verifier._timeout = 1  # Short timeout for testing

    async with verifier_context(python_verifier) as verifier:
        script = "import time; time.sleep(2)"
        result = await verifier._verify_implementation(
            VerifierInput(llm_response=script)
        )

        assert result.status == VerificationOutcome.TIMEOUT
        assert "Execution timed out" in result.error_message


@pytest.mark.asyncio
async def test_python_verifier_output_mismatch(python_verifier):
    r"""Test verification when output does not match ground truth."""
    async with verifier_context(python_verifier) as verifier:
        script = 'print("Wrong output")'
        result = await verifier._verify_implementation(
            VerifierInput(llm_response=script, ground_truth="Expected output")
        )

        assert result.status == VerificationOutcome.FAILURE
        assert result.error_message == "Output doesn't match ground truth"


@pytest.mark.asyncio
async def test_python_verifier_correct_output_matching(python_verifier):
    r"""Test verification when output matches ground truth."""
    async with verifier_context(python_verifier) as verifier:
        script = 'print("Expected output")'
        result = await verifier._verify_implementation(
            VerifierInput(llm_response=script, ground_truth="Expected output")
        )

        assert result.status == VerificationOutcome.SUCCESS
        assert result.result == "Expected output\n"


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
    async with verifier_context(python_verifier) as verifier:
        script = "import numpy as np; print(np.array([1, 2, 3]))"
        result = await verifier._verify_implementation(
            VerifierInput(llm_response=script)
        )

        assert result.status == VerificationOutcome.SUCCESS
        assert "[1 2 3]" in result.result


@pytest.mark.asyncio
async def test_python_verifier_with_subprocess_interpreter():
    r"""Test PythonVerifier with SubprocessInterpreter."""
    interpreter = SubprocessInterpreter(require_confirm=False)
    verifier = PythonVerifier(interpreter=interpreter, timeout=5.0)

    async with verifier_context(verifier) as v:
        script = 'print("Using subprocess interpreter")'
        result = await v.verify(VerifierInput(llm_response=script))

        assert result.status == VerificationOutcome.SUCCESS
        assert result.result == "Using subprocess interpreter\n"


@pytest.mark.asyncio
async def test_python_verifier_with_internal_python_interpreter():
    r"""Test PythonVerifier with InternalPythonInterpreter."""
    interpreter = InternalPythonInterpreter(unsafe_mode=True)
    verifier = PythonVerifier(interpreter=interpreter, timeout=5.0)

    async with verifier_context(verifier) as v:
        script = 'print("Using internal Python interpreter")'
        result = await v.verify(VerifierInput(llm_response=script))

        assert result.status == VerificationOutcome.SUCCESS
        assert result.result == "Using internal Python interpreter\n"


@pytest.mark.asyncio
async def test_python_verifier_with_ipython_interpreter():
    r"""Test PythonVerifier with JupyterKernelInterpreter."""
    interpreter = JupyterKernelInterpreter(require_confirm=False)
    verifier = PythonVerifier(
        interpreter=interpreter, timeout=5.0, required_packages=["jupyter"]
    )

    async with verifier_context(verifier) as v:
        script = 'print("Using IPython interpreter")'
        result = await v.verify(VerifierInput(llm_response=script))

        assert result.status == VerificationOutcome.SUCCESS
        assert result.result == "Using IPython interpreter\n"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "interpreter_class,expected_output",
    [
        (DockerInterpreter, "Using Docker interpreter"),
        (E2BInterpreter, "Using E2B interpreter"),
    ],
)
async def test_python_verifier_with_non_local_interpreters(
    interpreter_class, expected_output
):
    r"""Test PythonVerifier with non-local interpreters (Docker and E2B)."""
    with patch(
        f"camel.interpreters.{interpreter_class.__name__}"
    ) as MockInterpreter:
        mock_instance = MockInterpreter.return_value
        mock_instance.run.return_value = expected_output
        mock_instance.__class__ = interpreter_class
        verifier = PythonVerifier(interpreter=mock_instance, timeout=5.0)
        # Check if use_venv was auto-detected correctly as False
        assert verifier.use_venv is False

        async with verifier_context(verifier) as v:
            script = f'print("Using {interpreter_class.__name__}")'
            result = await v.verify(VerifierInput(llm_response=script))

            assert result.status == VerificationOutcome.SUCCESS
            assert result.result == expected_output
            mock_instance.run.assert_called_once_with(script, "python")
