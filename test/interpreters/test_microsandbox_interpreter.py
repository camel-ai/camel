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

from unittest.mock import patch

import pytest

from camel.interpreters import InterpreterError, MicrosandboxInterpreter

# Test server configuration
MICROSANDBOX_SERVER = "http://192.168.122.56:5555"


@pytest.fixture
def interpreter():
    """Create a MicrosandboxInterpreter for testing."""
    with (
        patch('microsandbox.PythonSandbox'),
        patch('microsandbox.NodeSandbox'),
    ):
        return MicrosandboxInterpreter(
            require_confirm=False,
            server_url=MICROSANDBOX_SERVER,
            namespace="test",
            timeout=30,
        )


def test_initialization():
    """Test basic initialization."""
    with (
        patch('microsandbox.PythonSandbox'),
        patch('microsandbox.NodeSandbox'),
    ):
        interpreter = MicrosandboxInterpreter(
            require_confirm=False,
            server_url=MICROSANDBOX_SERVER,
            namespace="test-init",
            timeout=60,
        )

        assert interpreter.require_confirm is False
        assert interpreter.server_url == MICROSANDBOX_SERVER
        assert interpreter.namespace == "test-init"
        assert interpreter.timeout == 60


def test_supported_code_types():
    """Test supported code types."""
    with (
        patch('microsandbox.PythonSandbox'),
        patch('microsandbox.NodeSandbox'),
    ):
        interpreter = MicrosandboxInterpreter(require_confirm=False)
        supported_types = interpreter.supported_code_types()

        # Check basic types are supported
        assert "python" in supported_types
        assert "javascript" in supported_types
        assert "bash" in supported_types


def test_unsupported_language(interpreter):
    """Test unsupported language raises error."""
    with pytest.raises(InterpreterError) as exc_info:
        interpreter.run("test", "unsupported_language")

    assert "Unsupported code type" in str(exc_info.value)
