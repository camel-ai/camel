# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
"""
Test that the following decorators are correctly applied to camel.interpreters:
@dependencies_required - should raise ImportError if package/module is missing
"""

from unittest.mock import patch

import pytest


def _mock_missing(module_name: str):
    """Patch is_module_available to return False for a specific module."""
    original = __import__(
        'camel.utils.commons', fromlist=['is_module_available']
    ).is_module_available

    def fake(m):
        if m == module_name:
            return False
        return original(m)

    return patch('camel.utils.commons.is_module_available', side_effect=fake)


def test_docker_interpreter_missing_dependency():
    from camel.interpreters import DockerInterpreter

    with _mock_missing('docker'):
        with pytest.raises(ImportError, match="docker"):
            DockerInterpreter()


def test_e2b_interpreter_missing_dependency():
    from camel.interpreters import E2BInterpreter

    with _mock_missing('e2b_code_interpreter'):
        with pytest.raises(ImportError, match="e2b_code_interpreter"):
            E2BInterpreter()


def test_jupyter_kernel_interpreter_missing_dependency():
    from camel.interpreters import JupyterKernelInterpreter

    with _mock_missing('jupyter_client'):
        with pytest.raises(ImportError, match="jupyter_client"):
            JupyterKernelInterpreter()


def test_jupyter_kernel_interpreter_missing_ipykernel():
    from camel.interpreters import JupyterKernelInterpreter

    with _mock_missing('ipykernel'):
        with pytest.raises(ImportError, match="ipykernel"):
            JupyterKernelInterpreter()


def test_microsandbox_interpreter_missing_dependency():
    from camel.interpreters import MicrosandboxInterpreter

    with _mock_missing('microsandbox'):
        with pytest.raises(ImportError, match="microsandbox"):
            MicrosandboxInterpreter()
