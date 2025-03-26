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
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from camel.toolkits import DocumentProcessingToolkit


@pytest.fixture
def document_processing_toolkit():
    return DocumentProcessingToolkit()


@pytest.fixture
def sample_csv_file():
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as temp_file:
        df = pd.DataFrame(
            {
                'Name': ['Alice', 'Bob', 'Charlie'],
                'Age': [25, 30, 35],
                'City': ['New York', 'San Francisco', 'Seattle'],
            }
        )
        df.to_csv(temp_file.name, index=False)
        temp_path = temp_file.name

    yield temp_path

    # Clean up the temporary file
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_extract_excel_content_csv(
    document_processing_toolkit, sample_csv_file
):
    """Test extracting content from a CSV file."""
    result = document_processing_toolkit.extract_excel_content(
        sample_csv_file, header_only=False
    )

    # Check that the result contains expected content
    assert "CSV File Processed" in result
    assert "Name" in result
    assert "Age" in result
    assert "City" in result
    assert "Alice" in result
    assert "Bob" in result
    assert "Charlie" in result


def test_extract_excel_content_unsupported_format(document_processing_toolkit):
    """Test handling of unsupported file formats."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
        temp_file.write(b"This is a text file, not an Excel file.")
        temp_path = temp_file.name

    try:
        result = document_processing_toolkit.extract_excel_content(
            temp_path, header_only=False
        )
        assert "Failed to process file" in result
        assert "It is not excel format" in result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_extract_excel_content_xlsx(document_processing_toolkit):
    """Test extracting content from an XLSX file using mocks."""
    with (
        patch('openpyxl.load_workbook') as mock_load_workbook,
        patch('pandas.read_excel') as mock_read_excel,
    ):
        # Mock the workbook and sheet
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()
        mock_cell = MagicMock()

        # Configure the mocks
        mock_load_workbook.return_value = mock_workbook
        mock_workbook.sheetnames = ['Sheet1']
        mock_workbook.__getitem__.return_value = mock_sheet

        # Mock cell properties
        mock_cell.row = 1
        mock_cell.column_letter = 'A'
        mock_cell.value = 'Test Value'
        mock_cell.font.color = None
        mock_cell.fill.fgColor = None

        # Set up the sheet to return our mock cell
        mock_sheet.iter_rows.return_value = [[mock_cell]]

        # Mock pandas read_excel to return a sample DataFrame
        df = pd.DataFrame({'Column1': ['Test Value'], 'Column2': [42]})
        mock_read_excel.return_value = df

        # Call the function with a fake xlsx path
        result = document_processing_toolkit.extract_excel_content(
            "test.xlsx", header_only=False
        )

        # Verify the function was called correctly
        mock_load_workbook.assert_called_once_with("test.xlsx", data_only=True)
        mock_read_excel.assert_called_once()

        # Check the result contains expected content
        assert "Sheet Name: Sheet1" in result
        assert "Cell information list" in result
        assert "Markdown View of the content" in result


def test_extract_document_content_docx(document_processing_toolkit):
    """Test extracting content from a DOCX file."""
    with patch('docx2markdown._docx_to_markdown') as mock_docx_to_markdown:
        mock_docx_to_markdown.return_value = "This is a test markdown content."

        result = document_processing_toolkit.extract_document_content(
            "test.docx"
        )

        # Check if the DOCX file was processed and converted to markdown
        mock_docx_to_markdown.assert_called_once_with(
            "test.docx", "test.docx.md"
        )
        assert "This is a test markdown content." in result


def test_extract_document_content_unsupported_type(
    document_processing_toolkit,
):
    """Test handling unsupported file types."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        result = document_processing_toolkit.extract_document_content(
            temp_path
        )
        assert "Please make a detailed caption about the image." in result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_extract_document_content_zip(document_processing_toolkit):
    """Test extracting content from a ZIP file."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        result = document_processing_toolkit.extract_document_content(
            temp_path
        )
        assert "The extracted files are" in result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_convert_to_markdown(document_processing_toolkit):
    """Test the _convert_to_markdown method."""
    df = pd.DataFrame({'Name': ['Alice', 'Bob'], 'Age': [25, 30]})

    result = document_processing_toolkit._convert_to_markdown(df)

    # Check that the result contains expected markdown table format
    assert "|" in result  # Table separator
    assert "Name" in result
    assert "Age" in result
    assert "Alice" in result
    assert "Bob" in result
    assert "25" in result
    assert "30" in result


def test_get_tools(document_processing_toolkit):
    """Test the get_tools method returns the correct tools."""
    tools = document_processing_toolkit.get_tools()

    # Check that we have the expected number of tools
    assert len(tools) == 2

    # Check that the tool has the correct function name
    assert tools[0].get_function_name() == "extract_document_content"
    assert tools[1].get_function_name() == "extract_excel_content"
