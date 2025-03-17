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

import sys
from unittest.mock import patch

import pytest

from camel.loaders import olmOCRLoader


@pytest.fixture
def mock_subprocess_run():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Extracted text from PDF"
        yield mock_run


@pytest.fixture
def mock_importlib():
    with patch("importlib.import_module") as mock_import:
        yield mock_import


@pytest.fixture
def mock_pip_install():
    with patch("subprocess.check_call") as mock_pip:
        yield mock_pip


def test_init(mock_importlib, mock_pip_install):
    r"""Test initialization of olmOCRLoader and dependency
    installation.
    """
    config = {"workspace": "./workspace"}
    _ = olmOCRLoader(config)

    mock_importlib.assert_any_call("cached-path")
    mock_importlib.assert_any_call("pypdf")
    mock_importlib.assert_any_call("torch")

    mock_pip_install.assert_not_called()


def test_load_success(mock_subprocess_run):
    r"""Test that load() correctly calls olmOCR and
    returns extracted text.
    """
    config = {"workspace": "./workspace"}
    loader = olmOCRLoader(config)

    pdf_path = "test.pdf"
    with patch("os.path.exists", return_value=True):
        result = loader.load(pdf_path)

    # Ensure olmOCR is called
    mock_subprocess_run.assert_called_once_with(
        [
            sys.executable,
            "-m",
            "olmocr.pipeline",
            "./workspace",
            "--pdfs",
            pdf_path,
        ],
        capture_output=True,
        text=True,
    )

    assert result == "Extracted text from PDF"


def test_load_missing_file():
    config = {"workspace": "./workspace"}
    loader = olmOCRLoader(config)

    with pytest.raises(FileNotFoundError, match="File not found: missing.pdf"):
        loader.load("missing.pdf")


def test_load_fail(mock_subprocess_run):
    config = {"workspace": "./workspace"}
    loader = olmOCRLoader(config)

    mock_subprocess_run.return_value.returncode = 1
    mock_subprocess_run.return_value.stderr = "Error processing PDF"

    with patch("os.path.exists", return_value=True):
        with pytest.raises(
            RuntimeError,
            match="olmOCR processing failed: Error processing PDF",
        ):
            loader.load("test.pdf")
