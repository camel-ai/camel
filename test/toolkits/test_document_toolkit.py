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
import zipfile
import json
from unittest.mock import MagicMock, patch, mock_open

import pytest
import requests

from camel.toolkits.document_toolkit import DocumentToolkit


@pytest.fixture
def document_toolkit():
    with patch('camel.toolkits.document_toolkit.ImageAnalysisToolkit') as mock_image_toolkit, \
            patch('camel.toolkits.document_toolkit.ExcelToolkit') as mock_excel_toolkit, \
            patch('camel.toolkits.document_toolkit._init_loader') as mock_init_loader:
        # Mock the toolkit instances
        mock_image_instance = MagicMock()
        mock_excel_instance = MagicMock()
        mock_loader_instance = MagicMock()
        mock_loader_wrapper = MagicMock()

        mock_image_toolkit.return_value = mock_image_instance
        mock_excel_toolkit.return_value = mock_excel_instance
        mock_loader_instance.convert_file.return_value = "Mocked loader content"
        mock_loader_wrapper._loader = mock_loader_instance
        mock_loader_wrapper.convert_file.return_value = "Mocked loader content"
        mock_init_loader.return_value = mock_loader_wrapper

        toolkit = DocumentToolkit(enable_cache=False)
        return toolkit


@pytest.fixture
def sample_text_file():
    """Create a temporary text file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False) as temp_file:
        temp_file.write("This is a sample text file for testing.")
        temp_path = temp_file.name

    yield temp_path

    # Clean up the temporary file
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_json_file():
    """Create a temporary JSON file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=".json", delete=False) as temp_file:
        data = {"name": "test", "value": 123, "items": ["a", "b", "c"]}
        json.dump(data, temp_file)
        temp_path = temp_file.name

    yield temp_path

    # Clean up the temporary file
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_zip_file():
    """Create a temporary ZIP file with text files for testing."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
        temp_path = temp_file.name

    with zipfile.ZipFile(temp_path, 'w') as zip_file:
        zip_file.writestr("file1.txt", "Content of file 1")
        zip_file.writestr("file2.txt", "Content of file 2")

    yield temp_path

    # Clean up the temporary file
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_extract_text_file_content(document_toolkit, sample_text_file):
    """Test extracting content from a text file."""
    success, content = document_toolkit.extract_document_content(sample_text_file)

    assert success is True
    assert "This is a sample text file for testing." in content


def test_extract_json_file_content(document_toolkit, sample_json_file):
    """Test extracting content from a JSON file."""
    success, content = document_toolkit.extract_document_content(sample_json_file)

    assert success is True
    assert "test" in content
    assert "123" in content


def test_extract_zip_file_content(document_toolkit, sample_zip_file):
    """Test extracting content from a ZIP file."""
    success, content = document_toolkit.extract_document_content(sample_zip_file)

    assert success is True
    assert "Content of file 1" in content
    assert "Content of file 2" in content


def test_handle_image_file_success(document_toolkit):
    """Test handling image files successfully."""
    # Mock the image toolkit
    document_toolkit.image_tool.ask_question_about_image.return_value = "This is a test image description"

    success, content = document_toolkit._handle_image("test.jpg")

    assert success is True
    assert "This is a test image description" in content


def test_handle_image_file_failure(document_toolkit):
    """Test handling image files with error."""
    # Mock the image toolkit to raise an exception
    document_toolkit.image_tool.ask_question_about_image.side_effect = Exception("Image processing failed")

    success, content = document_toolkit._handle_image("test.jpg")

    assert success is False
    assert "Error processing image" in content


def test_handle_excel_file_success(document_toolkit):
    """Test handling Excel files successfully."""
    # Mock the excel toolkit
    document_toolkit.excel_tool.extract_excel_content.return_value = "Excel content extracted"

    success, content = document_toolkit._handle_excel("test.xlsx")

    assert success is True
    assert "Excel content extracted" in content


def test_handle_excel_file_failure(document_toolkit):
    """Test handling Excel files with error."""
    # Mock the excel toolkit to raise an exception
    document_toolkit.excel_tool.extract_excel_content.side_effect = Exception("Excel processing failed")

    success, content = document_toolkit._handle_excel("test.xlsx")

    assert success is False
    assert "Error processing Excel file" in content


def test_handle_code_file(document_toolkit):
    """Test handling code files."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=".py", delete=False) as temp_file:
        temp_file.write("def hello():\n    print('Hello, World!')")
        temp_path = temp_file.name

    try:
        success, content = document_toolkit._handle_code_file(temp_path)

        assert success is True
        assert "def hello():" in content
        assert "print('Hello, World!')" in content
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_handle_code_file_error(document_toolkit):
    """Test handling code files with error."""
    success, content = document_toolkit._handle_code_file("/nonexistent/file.py")

    assert success is False
    assert "Error processing code file" in content


def test_is_url(document_toolkit):
    """Test URL detection."""
    assert document_toolkit._is_url("https://example.com") is True
    assert document_toolkit._is_url("http://example.com") is True
    assert document_toolkit._is_url("/local/path") is False
    assert document_toolkit._is_url("file.txt") is False


@patch('requests.head')
def test_is_webpage_success(mock_head, document_toolkit):
    """Test webpage detection with HTML content type."""
    mock_response = MagicMock()
    mock_response.headers.get.return_value = "text/html"
    mock_head.return_value = mock_response

    result = document_toolkit._is_webpage("https://example.com")
    assert result is True


@patch('requests.head')
def test_is_webpage_non_html(mock_head, document_toolkit):
    """Test webpage detection for non-HTML content."""
    mock_response = MagicMock()
    mock_response.headers.get.return_value = "application/pdf"
    mock_head.return_value = mock_response

    result = document_toolkit._is_webpage("https://example.com/file.pdf")
    assert result is False


@patch('requests.head')
def test_is_webpage_request_exception(mock_head, document_toolkit):
    """Test webpage detection when request fails."""
    mock_head.side_effect = requests.exceptions.RequestException("Connection error")

    result = document_toolkit._is_webpage("https://invalid-url.com")
    assert result is False


@patch('requests.get')
def test_download_file(mock_get, document_toolkit):
    """Test file download functionality."""
    mock_response = MagicMock()
    mock_response.headers.get.side_effect = lambda key, default="": {
        "Content-Disposition": 'attachment; filename="test.pdf"',
        "Content-Type": "application/pdf"
    }.get(key, default)
    mock_response.iter_content.return_value = [b"PDF content"]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    with patch('builtins.open', mock_open()) as mock_file:
        result_path = document_toolkit._download_file("https://example.com/test.pdf")

        assert result_path.name == "test.pdf"
        mock_file.assert_called_once()


def test_handle_data_file_json(document_toolkit, sample_json_file):
    """Test handling JSON data files directly."""
    success, content = document_toolkit._handle_data_file(sample_json_file)

    assert success is True
    assert "test" in content
    assert "123" in content


def test_handle_data_file_jsonl(document_toolkit):
    """Test handling JSONL data files."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=".jsonl", delete=False) as temp_file:
        temp_file.write('{"line": 1}\n{"line": 2}\n')
        temp_path = temp_file.name

    try:
        success, content = document_toolkit._handle_data_file(temp_path)

        assert success is True
        assert "line" in content
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_handle_data_file_xml_success(document_toolkit):
    """Test handling XML data files successfully."""
    xml_content = '<?xml version="1.0"?><root><item>test</item></root>'
    with tempfile.NamedTemporaryFile(mode='w', suffix=".xml", delete=False) as temp_file:
        temp_file.write(xml_content)
        temp_path = temp_file.name

    try:
        # Test the actual functionality - this will likely fall back to raw content
        success, content = document_toolkit._handle_data_file(temp_path)

        assert success is True
        # Should contain the test data either parsed or as raw XML
        assert "test" in content
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_handle_data_file_unsupported_format(document_toolkit):
    """Test handling unsupported data file format."""
    with tempfile.NamedTemporaryFile(suffix=".unknown", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        success, content = document_toolkit._handle_data_file(temp_path)

        assert success is False
        assert "Unsupported data file format" in content
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@patch('os.environ.get')
@patch('camel.toolkits.document_toolkit.FirecrawlApp')
def test_handle_webpage_with_firecrawl(mock_firecrawl, mock_env_get, document_toolkit):
    """Test webpage handling with FireCrawl."""
    mock_env_get.return_value = 'test_key'
    mock_app = MagicMock()
    mock_app.crawl_url.return_value = {
        "success": True,
        "data": [{"markdown": "# Test Page\nThis is test content"}]
    }
    mock_firecrawl.return_value = mock_app

    success, content = document_toolkit._handle_webpage("https://example.com")

    assert success is True
    assert "Test Page" in content


def test_handle_webpage_without_api_key(document_toolkit):
    """Test webpage handling without FireCrawl API key."""
    with patch('os.environ.get', return_value=None):
        with patch.object(document_toolkit, 'uio', None):
            success, content = document_toolkit._handle_webpage("https://example.com")

            assert success is False
            assert "No suitable loader for webpage processing" in content


def test_extract_document_content_unsupported_format(document_toolkit):
    """Test handling of unsupported file formats."""
    with tempfile.NamedTemporaryFile(suffix=".unknown", delete=False) as temp_file:
        temp_file.write(b"This is an unknown file format.")
        temp_path = temp_file.name

    try:
        # Mock the generic loader to return some content
        document_toolkit._loader.convert_file.return_value = "Converted unknown file content"

        success, content = document_toolkit.extract_document_content(temp_path)

        assert success is True
        assert "Converted unknown file content" in content
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_extract_document_content_error_handling(document_toolkit):
    """Test error handling for invalid file paths."""
    success, content = document_toolkit.extract_document_content("/nonexistent/file.txt")

    assert success is False
    # The actual error message may vary, so just check that it's an error message
    assert "Error" in content or "No such file" in content


def test_get_tools(document_toolkit):
    """Test the get_tools method returns the correct tools."""
    tools = document_toolkit.get_tools()

    # Check that we have the expected number of tools
    assert len(tools) == 1

    # Check that the tool has the correct function name
    assert tools[0].get_function_name() == "extract_document_content"