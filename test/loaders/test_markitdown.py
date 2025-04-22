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
from unittest.mock import patch

import pytest

from camel.loaders import MarkItDownConverter


@pytest.fixture
def mock_files():
    files = {
        "demo.html": "<html><body><h1>Demo HTML</h1></body></html>",
        "report.pdf": "%PDF-1.4\n% Mock PDF content",
        "presentation.pptx": "Mock PPTX content",
        "data.xlsx": "Mock XLSX content",
        "nonexistent.txt": None,
    }
    for filename, content in files.items():
        if content:
            with open(filename, "w") as f:
                f.write(content)
    yield files
    for filename in files.keys():
        if os.path.exists(filename):
            os.remove(filename)


def test_convert_file_success(mock_files):
    converter = MarkItDownConverter()
    markdown_text = converter.convert_file("demo.html")
    assert markdown_text is not None


def test_convert_file_not_found():
    converter = MarkItDownConverter()
    with pytest.raises(FileNotFoundError):
        converter.convert_file("nonexistent.txt")


def test_convert_file_conversion_error(mock_files):
    converter = MarkItDownConverter()
    with patch.object(
        converter.converter,
        'convert',
        side_effect=Exception("Mock conversion error"),
    ):
        with pytest.raises(Exception, match="Mock conversion error"):
            converter.convert_file("demo.html")


def test_convert_files_success(mock_files):
    converter = MarkItDownConverter()
    file_paths = ["demo.html", "report.pdf"]
    results = converter.convert_files(file_paths)
    assert "demo.html" in results
    assert "report.pdf" in results
    assert "nonexistent.txt" not in results


def test_convert_files_with_errors(mock_files):
    converter = MarkItDownConverter()
    file_paths = ["demo.html", "nonexistent.txt"]
    results = converter.convert_files(file_paths)
    assert "demo.html" in results
    assert "nonexistent.txt" in results
    assert results["nonexistent.txt"].startswith("Error:")
