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
import tempfile
from unittest.mock import patch

import pytest

# Try importing markitdown, skip tests if not available
try:
    import markitdown  # noqa: F401

    from camel.loaders import MarkItDownLoader

    markitdown_available = True
except ImportError:
    markitdown_available = False

# Skip all tests in this module if markitdown isn't available
pytestmark = pytest.mark.skipif(
    not markitdown_available,
    reason="markitdown is not installed (only available for Python >= 3.13)",
)


@pytest.fixture
def mock_files():
    files = {
        "demo_html": (
            "demo.html",
            "<html><body><h1>Mock HTML </h1></body></html>",
        ),
        "report_pdf": ("report.pdf", "Mock PDF content"),
        "presentation_pptx": ("presentation.pptx", "Mock PPTX content"),
        "data_xlsx": ("data.xlsx", "Mock XLSX content"),
        "unsupported_xxx": ("unsupported.xxx", "unsupported extension"),
    }
    created_paths = {}

    for key, (filename, content) in files.items():
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(filename)[1], mode="w"
        )
        temp_file.write(content)
        temp_file.close()
        created_paths[key] = temp_file.name

    yield created_paths

    for path in created_paths.values():
        if os.path.exists(path):
            os.remove(path)


def test_convert_file_success(mock_files):
    converter = MarkItDownLoader()
    markdown_text = converter.convert_file(mock_files["demo_html"])
    assert markdown_text is not None
    assert isinstance(markdown_text, str)


def test_convert_file_not_found():
    converter = MarkItDownLoader()
    with pytest.raises(
        FileNotFoundError, match="File not found: nonexistent.txt"
    ):
        converter.convert_file("nonexistent.txt")


def test_convert_file_unsupported_format(mock_files):
    converter = MarkItDownLoader()
    with pytest.raises(ValueError, match="Unsupported file format"):
        converter.convert_file(mock_files["unsupported_xxx"])


def test_convert_file_conversion_error(mock_files):
    converter = MarkItDownLoader()
    with patch.object(
        converter.converter,
        "convert",
        side_effect=Exception("Mock conversion error"),
    ):
        with pytest.raises(Exception, match="Mock conversion error"):
            converter.convert_file(mock_files["demo_html"])


def test_convert_files_success(mock_files):
    converter = MarkItDownLoader()
    file_paths = [mock_files["demo_html"], mock_files["report_pdf"]]
    results = converter.convert_files(file_paths)
    assert mock_files["demo_html"] in results
    assert mock_files["report_pdf"] in results
    assert all(isinstance(result, str) for result in results.values())
    assert len(results) == 2


def test_convert_files_with_errors(mock_files):
    converter = MarkItDownLoader()
    file_paths = [
        mock_files["demo_html"],
        mock_files["report_pdf"],
        "nonexistent.txt",
    ]
    results = converter.convert_files(file_paths)
    assert mock_files["demo_html"] in results
    assert mock_files["report_pdf"] in results
    assert "nonexistent.txt" in results
    assert results["nonexistent.txt"].startswith("Error:")
    assert len(results) == 3


def test_convert_files_skip_failed(mock_files):
    converter = MarkItDownLoader()
    file_paths = [
        mock_files["demo_html"],
        mock_files["report_pdf"],
        "nonexistent.txt",
    ]
    results = converter.convert_files(file_paths, skip_failed=True)
    assert mock_files["demo_html"] in results
    assert mock_files["report_pdf"] in results
    assert "nonexistent.txt" not in results
    assert all(isinstance(result, str) for result in results.values())
    assert len(results) == 2


def test_convert_files_parallel(mock_files):
    converter = MarkItDownLoader()
    file_paths = [mock_files["demo_html"], mock_files["report_pdf"]]
    results = converter.convert_files(file_paths, parallel=True)
    assert mock_files["demo_html"] in results
    assert mock_files["report_pdf"] in results
    assert all(isinstance(result, str) for result in results.values())
    assert len(results) == 2
