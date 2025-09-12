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

import importlib
import subprocess
from pathlib import Path

import pytest

MODULES_TO_IMPORT = [
    "camel.agents",
    "camel.messages",
    "camel.prompts",
    "camel.utils",
    "camel.types",
    "camel.societies",
    "camel.societies.workforce",
]


@pytest.mark.parametrize("module_path", MODULES_TO_IMPORT)
def test_minimum_deps_module_importable(module_path):
    r"""Test whether a module can be imported under minimal dependencies.

    This ensures that the module does not require optional or heavyweight
    dependencies to be imported, which is important for lightweight usage
    or constrained environments.

    Args:
        module_path (str): The dotted import path of the module to test.
    """
    try:
        importlib.import_module(module_path)
    except ImportError as e:
        pytest.fail(
            f"Failed to import {module_path} with"
            f" minimal dependencies:\n{e!s}"
        )


EXAMPLES = [
    "examples/agents/single_agent.py",
]


@pytest.mark.model_backend
@pytest.mark.parametrize("example_path", EXAMPLES)
def test_example_runs_or_skips(example_path):
    r"""Test if an example script runs successfully or fails clearly.

    This validates that user-facing example scripts execute without errors
    when the appropriate model backend is available.

    Args:
        example_path (str): Relative file path to the example script.
    """
    path = Path(example_path)
    assert path.exists(), f"{example_path} does not exist"

    try:
        subprocess.run(
            ["python", str(path)], check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        pytest.fail(f"{example_path} failed:\n{e.stderr.strip()}")
