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

import json
import os
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

from camel.toolkits.document_toolkit import (
    DocumentToolkit,
    _init_loader,
    _LoaderWrapper,
)


class TestLoaderWrapper:
    r"""Test the _LoaderWrapper class."""

    def test_loader_wrapper_with_convert_file(self):
        r"""Test _LoaderWrapper with a loader that has convert_file method."""
        mock_loader = MagicMock()
        mock_loader.convert_file.return_value = "test content"

        wrapper = _LoaderWrapper(mock_loader)
        result = wrapper.parse_file("test.txt")

        assert result == "test content"
        mock_loader.convert_file.assert_called_once_with("test.txt")

    def test_loader_wrapper_without_convert_file(self):
        r"""Test _LoaderWrapper with a loader that doesn't have
        convert_file method."""
        mock_loader = MagicMock(spec=[])  # No convert_file method

        wrapper = _LoaderWrapper(mock_loader)

        with pytest.raises(
            AttributeError, match="Loader must expose convert_file method"
        ):
            wrapper.parse_file("test.txt")


class TestInitLoader:
    r"""Test the _init_loader function."""

    @patch('camel.toolkits.document_toolkit.MarkItDownLoader')
    def test_init_loader_markitdown_success(self, mock_markitdown):
        r"""Test initializing MarkItDownLoader successfully."""
        mock_instance = MagicMock()
        mock_markitdown.return_value = mock_instance

        result = _init_loader("markitdown", {"param": "value"})

        assert isinstance(result, _LoaderWrapper)
        mock_markitdown.assert_called_once_with(param="value")

    @patch('camel.toolkits.document_toolkit.MarkItDownLoader', None)
    def test_init_loader_markitdown_unavailable(self):
        r"""Test initializing MarkItDownLoader when unavailable."""
        with pytest.raises(ImportError, match="MarkItDownLoader unavailable"):
            _init_loader("markitdown", {})

    def test_init_loader_unsupported_type(self):
        r"""Test initializing unsupported loader type."""
        with pytest.raises(ValueError, match="Unsupported loader_type"):
            _init_loader("unsupported", {})


@pytest.fixture
def mock_markitdown_loader():
    r"""Mock MarkItDownLoader for testing."""
    with patch('camel.toolkits.document_toolkit.MarkItDownLoader') as mock:
        mock_instance = MagicMock()
        mock_instance.convert_file.return_value = "MarkItDown content"
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def document_toolkit(mock_markitdown_loader):
    r"""Create a DocumentToolkit instance with mocked dependencies."""
    with (
        patch(
            'camel.toolkits.document_toolkit.ImageAnalysisToolkit'
        ) as mock_image_toolkit,
        patch(
            'camel.toolkits.document_toolkit._init_loader'
        ) as mock_init_loader,
    ):
        # Mock the image toolkit
        mock_image_instance = MagicMock()
        mock_image_toolkit.return_value = mock_image_instance

        # Mock the loader wrapper
        mock_loader_wrapper = MagicMock()
        mock_loader_wrapper.convert_file.return_value = (
            "Generic loader content"
        )
        mock_init_loader.return_value = mock_loader_wrapper

        toolkit = DocumentToolkit(enable_cache=False)
        toolkit.mid_loader = mock_markitdown_loader
        return toolkit


@pytest.fixture
def sample_text_file():
    r"""Create a temporary text file for testing."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix=".txt", delete=False
    ) as temp_file:
        temp_file.write("This is a sample text file for testing.")
        temp_path = temp_file.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_json_file():
    r"""Create a temporary JSON file for testing."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix=".json", delete=False
    ) as temp_file:
        data = {"name": "test", "value": 123, "items": ["a", "b", "c"]}
        json.dump(data, temp_file)
        temp_path = temp_file.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_jsonl_file():
    r"""Create a temporary JSONL file for testing."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix=".jsonl", delete=False
    ) as temp_file:
        temp_file.write('{"line": 1, "data": "first"}\n')
        temp_file.write('{"line": 2, "data": "second"}\n')
        temp_path = temp_file.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_xml_file():
    r"""Create a temporary XML file for testing."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix=".xml", delete=False
    ) as temp_file:
        xml_content = '<?xml version="1.0"?><root><item id="1">test content</item><item id="2">more content</item></root>'  # noqa: E501

        temp_file.write(xml_content)
        temp_path = temp_file.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_code_file():
    r"""Create a temporary Python code file for testing."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix=".py", delete=False
    ) as temp_file:
        code_content = '''def hello_world():
    """A simple greeting function."""
    print("Hello, World!")
    return "greeting"

if __name__ == "__main__":
    hello_world()
'''
        temp_file.write(code_content)
        temp_path = temp_file.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_html_file():
    r"""Create a temporary HTML file for testing."""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix=".html", delete=False
    ) as temp_file:
        html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Sample HTML Content</h1>
    <p>This is a test paragraph.</p>
</body>
</html>'''
        temp_file.write(html_content)
        temp_path = temp_file.name

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_zip_file():
    r"""Create a temporary ZIP file with various files for testing."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
        temp_path = temp_file.name

    with zipfile.ZipFile(temp_path, 'w') as zip_file:
        zip_file.writestr("file1.txt", "Content of file 1")
        zip_file.writestr("file2.txt", "Content of file 2")
        zip_file.writestr("data.json", '{"key": "value", "number": 42}')
        zip_file.writestr("subfolder/nested.txt", "Nested file content")

    yield temp_path

    if os.path.exists(temp_path):
        os.remove(temp_path)


class TestDocumentToolkitBasics:
    r"""Test basic DocumentToolkit functionality."""

    def test_initialization_default(self):
        r"""Test DocumentToolkit initialization with default parameters."""
        with (
            patch('camel.toolkits.document_toolkit.ImageAnalysisToolkit'),
            patch('camel.toolkits.document_toolkit._init_loader'),
            patch('camel.toolkits.document_toolkit.MarkItDownLoader'),
        ):
            toolkit = DocumentToolkit()

            assert toolkit.cache_dir.exists()
            assert toolkit.enable_cache is True
            assert hasattr(toolkit, 'image_tool')
            assert hasattr(toolkit, '_loader')

    def test_initialization_custom_cache_dir(self):
        r"""Test DocumentToolkit initialization with custom cache directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_cache = Path(temp_dir) / "custom_cache"

            with (
                patch('camel.toolkits.document_toolkit.ImageAnalysisToolkit'),
                patch('camel.toolkits.document_toolkit._init_loader'),
                patch('camel.toolkits.document_toolkit.MarkItDownLoader'),
            ):
                toolkit = DocumentToolkit(
                    cache_dir=custom_cache, enable_cache=False
                )

                assert toolkit.cache_dir == custom_cache
                assert toolkit.enable_cache is False

    def test_get_tools(self, document_toolkit):
        r"""Test the get_tools method returns correct tools."""
        tools = document_toolkit.get_tools()

        assert len(tools) == 1
        assert tools[0].get_function_name() == "extract_document_content"


class TestUtilityMethods:
    r"""Test utility methods in DocumentToolkit."""

    def test_is_url_valid_urls(self, document_toolkit):
        r"""Test URL detection for valid URLs."""
        assert document_toolkit._is_url("https://example.com") is True
        assert document_toolkit._is_url("http://example.com") is True
        assert (
            document_toolkit._is_url("https://example.com/path/file.pdf")
            is True
        )

    def test_is_url_invalid_urls(self, document_toolkit):
        r"""Test URL detection for invalid URLs."""
        assert document_toolkit._is_url("/local/path") is False
        assert document_toolkit._is_url("file.txt") is False
        assert document_toolkit._is_url("relative/path/file.txt") is False
        assert document_toolkit._is_url("") is False

    @patch('requests.head')
    def test_is_webpage_html_content(self, mock_head, document_toolkit):
        r"""Test webpage detection for HTML content."""
        mock_response = MagicMock()
        mock_response.headers.get.return_value = "text/html; charset=utf-8"
        mock_head.return_value = mock_response

        result = document_toolkit._is_webpage("https://example.com")
        assert result is True

    @patch('requests.head')
    def test_is_webpage_non_html_content(self, mock_head, document_toolkit):
        r"""Test webpage detection for non-HTML content."""
        mock_response = MagicMock()
        mock_response.headers.get.return_value = "application/pdf"
        mock_head.return_value = mock_response

        result = document_toolkit._is_webpage("https://example.com/file.pdf")
        assert result is False

    @patch('requests.head')
    def test_is_webpage_request_exception(self, mock_head, document_toolkit):
        """Test webpage detection when request fails."""
        mock_head.side_effect = requests.exceptions.RequestException(
            "Connection error"
        )

        result = document_toolkit._is_webpage("https://invalid-url.com")
        assert result is False

    def test_hash_key_local_file(self, document_toolkit, sample_text_file):
        r"""Test hash key generation for local files."""
        key1 = document_toolkit._hash_key(sample_text_file)
        key2 = document_toolkit._hash_key(sample_text_file)

        assert key1 == key2
        assert len(key1) == 64  # SHA-256 hex digest length

    @patch.object(DocumentToolkit, '_is_webpage', return_value=True)
    def test_hash_key_webpage(self, mock_is_webpage, document_toolkit):
        r"""Test hash key generation for webpages."""
        url = "https://example.com"
        key = document_toolkit._hash_key(url)

        assert len(key) == 64  # SHA-256 hex digest length
        mock_is_webpage.assert_called_once_with(url)

    def test_short_hash(self, document_toolkit):
        r"""Test short hash generation."""
        path = Path("/some/test/path")
        hash_str = document_toolkit._short_hash(path)

        assert len(hash_str) == 8
        assert isinstance(hash_str, str)


class TestFileHandlers:
    r"""Test individual file type handlers."""

    def test_handle_text_file_success(
        self, document_toolkit, sample_text_file
    ):
        r"""Test handling text files successfully."""
        success, content = document_toolkit._handle_text_file(sample_text_file)

        assert success is True
        assert "This is a sample text file for testing." in content

    def test_handle_text_file_not_found(self, document_toolkit):
        r"""Test handling non-existent text files."""
        success, content = document_toolkit._handle_text_file(
            "/nonexistent/file.txt"
        )

        assert success is False
        assert "Error reading text file" in content

    def test_handle_code_file_success(
        self, document_toolkit, sample_code_file
    ):
        r"""Test handling code files successfully."""
        success, content = document_toolkit._handle_code_file(sample_code_file)

        assert success is True
        assert "def hello_world():" in content
        assert "print(\"Hello, World!\")" in content

    def test_handle_code_file_not_found(self, document_toolkit):
        r"""Test handling non-existent code files."""
        success, content = document_toolkit._handle_code_file(
            "/nonexistent/file.py"
        )

        assert success is False
        assert "Error processing code file" in content

    def test_handle_data_file_json(self, document_toolkit, sample_json_file):
        r"""Test handling JSON data files."""
        success, content = document_toolkit._handle_data_file(sample_json_file)

        assert success is True
        assert "test" in content
        assert "123" in content

    def test_handle_data_file_jsonl(self, document_toolkit, sample_jsonl_file):
        r"""Test handling JSONL data files."""
        success, content = document_toolkit._handle_data_file(
            sample_jsonl_file
        )

        assert success is True
        assert "first" in content
        assert "second" in content

    @patch('xmltodict.parse')
    def test_handle_data_file_xml_success(
        self, mock_parse, document_toolkit, sample_xml_file
    ):
        r"""Test handling XML data files successfully."""
        mock_parse.return_value = {
            "root": {"item": [{"@id": "1", "#text": "test content"}]}
        }

        success, content = document_toolkit._handle_data_file(sample_xml_file)

        assert success is True
        assert "test content" in content

    @patch('xmltodict.parse')
    def test_handle_data_file_xml_parse_error(
        self, mock_parse, document_toolkit, sample_xml_file
    ):
        r"""Test handling XML data files when parsing fails."""
        mock_parse.side_effect = Exception("XML parse error")

        success, content = document_toolkit._handle_data_file(sample_xml_file)

        assert success is True
        assert "test content" in content  # Should return raw content

    def test_handle_data_file_unsupported(self, document_toolkit):
        r"""Test handling unsupported data file format."""
        with tempfile.NamedTemporaryFile(
            suffix=".unknown", delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            success, content = document_toolkit._handle_data_file(temp_path)

            assert success is False
            assert "Unsupported data file format" in content
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_handle_html_file_success(
        self, document_toolkit, sample_html_file
    ):
        r"""Test handling HTML files successfully with loader."""
        document_toolkit._loader.parse_file.return_value = (
            "Processed HTML content"
        )

        success, content = document_toolkit._handle_html_file(sample_html_file)

        assert success is True
        assert "Processed HTML content" in content

    def test_handle_html_file_fallback(
        self, document_toolkit, sample_html_file
    ):
        r"""Test handling HTML files with fallback to raw content."""
        document_toolkit._loader.parse_file.side_effect = Exception(
            "Loader error"
        )

        success, content = document_toolkit._handle_html_file(sample_html_file)

        assert success is True
        assert "Sample HTML Content" in content

    def test_handle_image_success(self, document_toolkit):
        r"""Test handling image files successfully."""
        document_toolkit.image_tool.ask_question_about_image.return_value = (
            "A beautiful landscape image"
        )

        success, content = document_toolkit._handle_image("test.jpg")

        assert success is True
        assert "A beautiful landscape image" in content

    def test_handle_image_failure(self, document_toolkit):
        r"""Test handling image files with error."""
        document_toolkit.image_tool.ask_question_about_image.side_effect = (
            Exception("Image processing failed")
        )

        success, content = document_toolkit._handle_image("test.jpg")

        assert success is False
        assert "Error processing image" in content


class TestExcelHandling:
    r"""Test Excel file handling with dependencies."""

    @patch('pandas.read_csv')
    @patch(
        'camel.toolkits.document_toolkit.DocumentToolkit._convert_to_markdown'
    )
    def test_extract_excel_content_csv(
        self, mock_convert, mock_read_csv, document_toolkit
    ):
        r"""Test extracting CSV content."""
        # Mock pandas DataFrame
        mock_df = MagicMock()
        mock_read_csv.return_value = mock_df
        mock_convert.return_value = (
            "| Column1 | Column2 |\n|---------|---------|"
        )

        result = document_toolkit._extract_excel_content("test.csv")

        assert "CSV File Processed:" in result
        mock_read_csv.assert_called_once_with("test.csv")
        mock_convert.assert_called_once_with(mock_df)

    def test_extract_excel_content_unsupported(self, document_toolkit):
        r"""Test extracting content from unsupported file format."""
        result = document_toolkit._extract_excel_content("test.txt")

        assert "Failed to process file" in result
        assert "not excel format" in result

    def test_handle_excel_success(self, document_toolkit):
        r"""Test handling Excel files successfully."""
        with patch.object(
            document_toolkit,
            '_extract_excel_content',
            return_value="Excel content extracted",
        ):
            success, content = document_toolkit._handle_excel("test.xlsx")

            assert success is True
            assert "Excel content extracted" in content

    def test_handle_excel_failure(self, document_toolkit):
        r"""Test handling Excel files with error."""
        with patch.object(
            document_toolkit,
            '_extract_excel_content',
            return_value="Failed to process file test.xlsx: Error",
        ):
            success, content = document_toolkit._handle_excel("test.xlsx")

            assert success is False
            assert "Failed to process file" in content


class TestZipHandling:
    r"""Test ZIP file handling."""

    def test_handle_zip_success(self, document_toolkit, sample_zip_file):
        r"""Test handling ZIP files successfully."""
        success, content = document_toolkit._handle_zip(sample_zip_file)

        assert success is True
        assert "Content of file 1" in content
        assert "Content of file 2" in content
        assert "file1.txt" in content
        assert "file2.txt" in content

    def test_handle_zip_not_found(self, document_toolkit):
        r"""Test handling non-existent ZIP files."""
        success, content = document_toolkit._handle_zip(
            "/nonexistent/file.zip"
        )

        assert success is False
        assert "Error processing ZIP" in content

    def test_ensure_local_zip_local_file(
        self, document_toolkit, sample_zip_file
    ):
        r"""Test ensuring ZIP file is local when it's already local."""
        result = document_toolkit._ensure_local_zip(sample_zip_file)

        assert isinstance(result, Path)
        assert result.exists()

    @patch.object(DocumentToolkit, '_download_file')
    def test_ensure_local_zip_remote_file(
        self, mock_download, document_toolkit
    ):
        r"""Test ensuring ZIP file is local when it's remote."""
        mock_download.return_value = Path("/local/path/downloaded.zip")

        result = document_toolkit._ensure_local_zip(
            "https://example.com/file.zip"
        )

        assert result == Path("/local/path/downloaded.zip")
        mock_download.assert_called_once_with("https://example.com/file.zip")


class TestDownloadFile:
    r"""Test file download functionality."""

    @patch('requests.get')
    def test_download_file_with_content_disposition(
        self, mock_get, document_toolkit
    ):
        r"""Test downloading file with Content-Disposition header."""
        mock_response = MagicMock()
        mock_response.headers.get.side_effect = lambda key, default="": {
            "Content-Disposition": 'attachment; filename="document.pdf"',
            "Content-Type": "application/pdf",
        }.get(key, default)
        mock_response.iter_content.return_value = [
            b"PDF content chunk 1",
            b"PDF content chunk 2",
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch('builtins.open', mock_open()) as mock_file:
            result_path = document_toolkit._download_file(
                "https://example.com/test.pdf"
            )

            assert result_path.name == "document.pdf"
            mock_file.assert_called_once()
            mock_get.assert_called_once_with(
                "https://example.com/test.pdf", stream=True, timeout=60
            )

    @patch('requests.get')
    def test_download_file_from_url_path(self, mock_get, document_toolkit):
        r"""Test downloading file using URL path for filename."""
        mock_response = MagicMock()
        mock_response.headers.get.return_value = ""
        mock_response.iter_content.return_value = [b"File content"]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch('builtins.open', mock_open()):
            result_path = document_toolkit._download_file(
                "https://example.com/path/document.txt"
            )

            assert result_path.name == "document.txt"

    @patch('requests.get')
    def test_download_file_with_content_type_extension(
        self, mock_get, document_toolkit
    ):
        r"""Test downloading file with extension guessed from content type."""
        mock_response = MagicMock()
        mock_response.headers.get.side_effect = lambda key, default="": {
            "Content-Type": "application/pdf"
        }.get(key, default)
        mock_response.iter_content.return_value = [b"PDF content"]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch('builtins.open', mock_open()):
            result_path = document_toolkit._download_file(
                "https://example.com/download"
            )

            assert result_path.suffix == ".pdf"

    @patch('requests.get')
    def test_download_file_request_error(self, mock_get, document_toolkit):
        r"""Test download file with request error."""
        mock_get.side_effect = requests.exceptions.RequestException(
            "Network error"
        )

        with pytest.raises(requests.exceptions.RequestException):
            document_toolkit._download_file("https://example.com/file.pdf")

    @patch('requests.get')
    def test_download_file_io_error(self, mock_get, document_toolkit):
        """Test download file with IO error during saving."""
        mock_response = MagicMock()
        mock_response.headers.get.return_value = ""
        mock_response.iter_content.return_value = [b"File content"]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        with patch('builtins.open', side_effect=IOError("Disk full")):
            with pytest.raises(IOError):
                document_toolkit._download_file("https://example.com/file.txt")


class TestWebpageHandling:
    r"""Test webpage content extraction."""

    @patch('camel.loaders.Crawl4AI')
    def test_extract_webpage_content_success(
        self, mock_crawl4ai, document_toolkit
    ):
        r"""Test successful webpage content extraction."""
        mock_crawler = MagicMock()
        mock_crawl4ai.return_value = mock_crawler

        # Mock the async scrape method
        with patch('asyncio.run') as mock_run:
            mock_run.return_value = {
                'markdown': '# Test Page\n\nThis is test content'
            }

            result = document_toolkit._extract_webpage_content(
                "https://example.com"
            )

            assert "# Test Page" in result
            assert "This is test content" in result

    @patch('camel.loaders.Crawl4AI')
    def test_extract_webpage_content_no_markdown(
        self, mock_crawl4ai, document_toolkit
    ):
        r"""Test webpage content extraction with no markdown key in result."""
        mock_crawler = MagicMock()
        mock_crawl4ai.return_value = mock_crawler

        with patch('asyncio.run') as mock_run:
            mock_run.return_value = {
                'html': '<html>content</html>'
            }  # No markdown key

            result = document_toolkit._extract_webpage_content(
                "https://example.com"
            )

            assert result == "Error while crawling the webpage."

    @patch('camel.loaders.Crawl4AI')
    def test_extract_webpage_content_empty_markdown(
        self, mock_crawl4ai, document_toolkit
    ):
        r"""Test webpage content extraction with empty markdown content."""
        mock_crawler = MagicMock()
        mock_crawl4ai.return_value = mock_crawler

        with patch('asyncio.run') as mock_run:
            mock_run.return_value = {'markdown': ''}  # Empty markdown

            result = document_toolkit._extract_webpage_content(
                "https://example.com"
            )

            assert result == "No content found on the webpage."

    @patch('camel.loaders.Crawl4AI')
    def test_extract_webpage_content_error(
        self, mock_crawl4ai, document_toolkit
    ):
        r"""Test webpage content extraction with error."""
        mock_crawler = MagicMock()
        mock_crawl4ai.return_value = mock_crawler

        with patch('asyncio.run', side_effect=Exception("Crawling failed")):
            result = document_toolkit._extract_webpage_content(
                "https://example.com"
            )

            assert "Error while crawling the webpage" in result

    @patch.object(DocumentToolkit, '_extract_webpage_content')
    def test_handle_webpage_success(self, mock_extract, document_toolkit):
        r"""Test handling webpage successfully."""
        mock_extract.return_value = "Extracted webpage content"

        success, content = document_toolkit._handle_webpage(
            "https://example.com"
        )

        assert success is True
        assert "Extracted webpage content" in content

    @patch.object(DocumentToolkit, '_extract_webpage_content')
    def test_handle_webpage_fallback_to_markitdown(
        self, mock_extract, document_toolkit
    ):
        r"""Test handling webpage with fallback to MarkItDown."""
        mock_extract.side_effect = Exception("Crawl4AI failed")
        document_toolkit.mid_loader.parse_file.return_value = (
            "MarkItDown webpage content"
        )

        success, content = document_toolkit._handle_webpage(
            "https://example.com"
        )

        assert success is True
        assert "MarkItDown webpage content" in content

    @patch.object(DocumentToolkit, '_extract_webpage_content')
    def test_handle_webpage_all_methods_fail(
        self, mock_extract, document_toolkit
    ):
        r"""Test handling webpage when all methods fail."""
        mock_extract.side_effect = Exception("Crawl4AI failed")
        document_toolkit.mid_loader = None

        success, content = document_toolkit._handle_webpage(
            "https://example.com"
        )

        assert success is False
        assert "No suitable loader for webpage processing" in content


class TestMainExtractionMethod:
    r"""Test the main extract_document_content method."""

    def test_extract_text_file(self, document_toolkit, sample_text_file):
        r"""Test extracting content from text file."""
        success, content = document_toolkit.extract_document_content(
            sample_text_file
        )

        assert success is True
        assert "This is a sample text file for testing." in content

    def test_extract_json_file(self, document_toolkit, sample_json_file):
        r"""Test extracting content from JSON file."""
        success, content = document_toolkit.extract_document_content(
            sample_json_file
        )

        assert success is True
        assert "test" in content
        assert "123" in content

    def test_extract_code_file(self, document_toolkit, sample_code_file):
        r"""Test extracting content from code file."""
        success, content = document_toolkit.extract_document_content(
            sample_code_file
        )

        assert success is True
        assert "def hello_world():" in content

    def test_extract_html_file(self, document_toolkit, sample_html_file):
        r"""Test extracting content from HTML file."""
        success, content = document_toolkit.extract_document_content(
            sample_html_file
        )

        assert success is True
        # Should use the generic loader
        assert content == "Generic loader content"

    def test_extract_zip_file(self, document_toolkit, sample_zip_file):
        r"""Test extracting content from ZIP file."""
        success, content = document_toolkit.extract_document_content(
            sample_zip_file
        )

        assert success is True
        assert "Content of file 1" in content
        assert "Content of file 2" in content

    @patch.object(DocumentToolkit, '_is_webpage', return_value=True)
    @patch.object(DocumentToolkit, '_handle_webpage')
    def test_extract_webpage(
        self, mock_handle_webpage, mock_is_webpage, document_toolkit
    ):
        r"""Test extracting content from webpage."""
        mock_handle_webpage.return_value = (True, "Webpage content")

        success, content = document_toolkit.extract_document_content(
            "https://example.com"
        )

        assert success is True
        assert "Webpage content" in content
        mock_handle_webpage.assert_called_once_with("https://example.com")

    @patch.object(DocumentToolkit, '_download_file')
    def test_extract_url_with_file_extension(
        self, mock_download, document_toolkit
    ):
        r"""Test extracting content from URL with file extension."""
        mock_download.return_value = Path("/downloaded/file.txt")

        with patch(
            'builtins.open', mock_open(read_data="Downloaded file content")
        ):
            success, content = document_toolkit.extract_document_content(
                "https://example.com/file.txt"
            )

            assert success is True
            assert "Downloaded file content" in content

    def test_extract_office_document_with_markitdown(self, document_toolkit):
        r"""Test extracting Office document with MarkItDown loader."""
        document_toolkit.mid_loader.parse_file.return_value = (
            "Office document content"
        )

        success, content = document_toolkit.extract_document_content(
            "document.docx"
        )

        assert success is True
        assert "Office document content" in content

    def test_extract_office_document_without_markitdown(
        self, document_toolkit
    ):
        r"""Test extracting Office document without MarkItDown loader."""
        document_toolkit.mid_loader = None

        success, content = document_toolkit.extract_document_content(
            "document.docx"
        )

        assert success is True
        assert (
            content == "Generic loader content"
        )  # Falls back to generic loader

    def test_extract_unknown_format_fallback(self, document_toolkit):
        r"""Test extracting unknown file format with fallback to
        generic loader."""
        with tempfile.NamedTemporaryFile(
            suffix=".unknown", delete=False
        ) as temp_file:
            temp_path = temp_file.name

        try:
            success, content = document_toolkit.extract_document_content(
                temp_path
            )

            assert success is True
            assert content == "Generic loader content"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_document_general_error(self, document_toolkit):
        r"""Test general error handling in extract_document_content."""
        # Mock the generic loader to raise an exception
        document_toolkit._loader.parse_file.side_effect = Exception(
            "Generic loader error"
        )

        success, content = document_toolkit.extract_document_content(
            "test.unknown"
        )

        assert success is False
        assert "Error extracting document" in content


class TestCaching:
    r"""Test caching functionality."""

    def test_cache_and_return_success_with_cache(self, document_toolkit):
        r"""Test cache_and_return with successful operation and
        caching enabled."""
        document_toolkit.enable_cache = True

        result = document_toolkit._cache_and_return(
            "test_key", True, "test content"
        )

        assert result == (True, "test content")
        assert document_toolkit._cache["test_key"] == "test content"

    def test_cache_and_return_success_without_cache(self, document_toolkit):
        r"""Test cache_and_return with successful operation and
        caching disabled."""
        document_toolkit.enable_cache = False

        result = document_toolkit._cache_and_return(
            "test_key", True, "test content"
        )

        assert result == (True, "test content")
        assert "test_key" not in document_toolkit._cache

    def test_cache_and_return_failure(self, document_toolkit):
        r"""Test cache_and_return with failed operation."""
        result = document_toolkit._cache_and_return(
            "test_key", False, "error message"
        )

        assert result == (False, "error message")
        assert "test_key" not in document_toolkit._cache

    def test_cache_hit(self, document_toolkit):
        r"""Test cache hit for previously processed document."""
        document_toolkit.enable_cache = True
        document_toolkit._cache["cached_key"] = "cached content"

        with patch.object(
            document_toolkit, '_hash_key', return_value="cached_key"
        ):
            success, content = document_toolkit.extract_document_content(
                "test.txt"
            )

            assert success is True
            assert content == "cached content"


class TestAsyncMethods:
    r"""Test asynchronous methods."""

    @pytest.mark.asyncio
    async def test_extract_async(self, document_toolkit):
        r"""Test asynchronous document extraction."""
        document_toolkit._loader.parse_file.return_value = (
            "Async extracted content"
        )

        result = await document_toolkit._extract_async("test.txt")

        assert result == "Async extracted content"

    def test_extract_document_content_sync(self, document_toolkit):
        r"""Test synchronous wrapper for document extraction."""
        document_toolkit._loader.parse_file.return_value = (
            "Sync extracted content"
        )

        with (
            patch('asyncio.get_event_loop') as mock_get_loop,
            patch('asyncio.new_event_loop'),
        ):
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = False
            mock_loop.run_until_complete.return_value = (True, "Sync content")
            mock_get_loop.return_value = mock_loop

            result = document_toolkit.extract_document_content_sync("test.txt")

            assert result == (True, "Sync content")


class TestEdgeCases:
    r"""Test edge cases and error conditions."""

    def test_extract_empty_file(self, document_toolkit):
        r"""Test extracting content from empty file."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix=".txt", delete=False
        ) as temp_file:
            temp_path = temp_file.name  # Empty file

        try:
            success, content = document_toolkit.extract_document_content(
                temp_path
            )

            assert success is True
            assert content == ""
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_binary_file_as_text(self, document_toolkit):
        r"""Test extracting binary file as text (should handle gracefully)."""
        with tempfile.NamedTemporaryFile(
            mode='wb', suffix=".bin", delete=False
        ) as temp_file:
            temp_file.write(b'\x00\x01\x02\x03\xff\xfe\xfd')
            temp_path = temp_file.name

        try:
            # Should fall back to generic loader
            success, content = document_toolkit.extract_document_content(
                temp_path
            )

            assert success is True
            assert content == "Generic loader content"
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_extract_file_with_unicode_name(self, document_toolkit):
        r"""Test extracting file with Unicode filename."""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix=".txt", delete=False, prefix="тест_файл_"
        ) as temp_file:
            temp_file.write("Unicode filename test content")
            temp_path = temp_file.name

        try:
            success, content = document_toolkit.extract_document_content(
                temp_path
            )

            assert success is True
            assert "Unicode filename test content" in content
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_very_long_filepath(self, document_toolkit):
        r"""Test handling very long file paths."""
        long_filename = "a" * 200 + ".txt"

        success, content = document_toolkit.extract_document_content(
            long_filename
        )

        assert success is False
        assert "Error extracting document" in content
