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

from camel.toolkits import ExcelToolkit


@pytest.fixture
def excel_toolkit():
    return ExcelToolkit()


@pytest.fixture
def sample_csv_file():
    r"""Create a temporary CSV file for testing."""
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


@pytest.fixture
def sample_xlsx_file():
    r"""Create a temporary XLSX file for testing."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        df = pd.DataFrame(
            {
                'Name': ['Alice', 'Bob', 'Charlie'],
                'Age': [25, 30, 35],
                'City': ['New York', 'San Francisco', 'Seattle'],
            }
        )
        df.to_excel(temp_file.name, index=False, sheet_name='Sheet1')
        temp_path = temp_file.name

    yield temp_path

    # Clean up the temporary file
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_extract_excel_content_csv(excel_toolkit, sample_csv_file):
    r"""Test extracting content from a CSV file."""
    result = excel_toolkit.extract_excel_content(sample_csv_file)

    # Check that the result contains expected content
    assert "CSV File Processed" in result
    assert "Name" in result
    assert "Age" in result
    assert "City" in result
    assert "Alice" in result
    assert "Bob" in result
    assert "Charlie" in result


def test_extract_excel_content_unsupported_format(excel_toolkit):
    r"""Test handling of unsupported file formats."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
        temp_file.write(b"This is a text file, not an Excel file.")
        temp_path = temp_file.name

    try:
        result = excel_toolkit.extract_excel_content(temp_path)
        assert "Failed to process file" in result
        assert "It is not excel format" in result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_extract_excel_content_xlsx(excel_toolkit):
    r"""Test extracting content from an XLSX file using mocks."""
    with (
        patch('openpyxl.load_workbook') as mock_load_workbook,
        patch('pandas.read_excel') as mock_read_excel,
        patch('os.path.exists') as mock_exists,
    ):
        mock_exists.return_value = True

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
        result = excel_toolkit.extract_excel_content("test.xlsx")

        # Verify the function was called correctly
        mock_load_workbook.assert_called_once_with("test.xlsx", data_only=True)
        mock_read_excel.assert_called_once()

        # Check the result contains expected content
        assert "Sheet Name: Sheet1" in result
        assert "Cell information list" in result
        assert "Markdown View of the content" in result


def test_extract_excel_content_xls(excel_toolkit):
    r"""Test extracting content from an XLS file using mocks."""
    with (
        patch('xls2xlsx.XLS2XLSX') as mock_xls2xlsx,
        patch('openpyxl.load_workbook') as mock_load_workbook,
        patch('pandas.read_excel') as mock_read_excel,
        patch('os.path.exists') as mock_exists,
    ):
        mock_exists.return_value = True

        # Mock the XLS2XLSX conversion
        mock_xls_converter = MagicMock()
        mock_xls2xlsx.return_value = mock_xls_converter

        # Mock the workbook and sheet
        mock_workbook = MagicMock()
        mock_sheet = MagicMock()

        # Configure the mocks
        mock_load_workbook.return_value = mock_workbook
        mock_workbook.sheetnames = ['Sheet1']
        mock_workbook.__getitem__.return_value = mock_sheet

        # Set up the sheet to return an empty list of cells
        mock_sheet.iter_rows.return_value = []

        # Mock pandas read_excel to return a sample DataFrame
        df = pd.DataFrame({'Column1': ['XLS Value'], 'Column2': [100]})
        mock_read_excel.return_value = df

        # Call the function with a fake xls path
        result = excel_toolkit.extract_excel_content("test.xls")

        # Verify the XLS conversion was called
        mock_xls2xlsx.assert_called_once_with("test.xls")
        mock_xls_converter.to_xlsx.assert_called_once()

        # Verify the workbook was loaded
        mock_load_workbook.assert_called_once()

        # Check the result contains expected content
        assert "Sheet Name: Sheet1" in result
        assert "Markdown View of the content" in result


def test_convert_to_markdown(excel_toolkit):
    r"""Test the _convert_to_markdown method."""
    df = pd.DataFrame({'Name': ['Alice', 'Bob'], 'Age': [25, 30]})

    result = excel_toolkit._convert_to_markdown(df)

    # Check that the result contains expected markdown table format
    assert "|" in result  # Table separator
    assert "Name" in result
    assert "Age" in result
    assert "Alice" in result
    assert "Bob" in result
    assert "25" in result
    assert "30" in result


def test_get_tools(excel_toolkit):
    r"""Test the get_tools method returns the correct tools."""
    tools = excel_toolkit.get_tools()

    assert len(tools) == 18

    # Check that all expected function names are present
    expected_function_names = [
        "extract_excel_content",
        "create_workbook",
        "delete_workbook",
        "export_sheet_to_csv",
        "create_sheet",
        "delete_sheet",
        "clear_sheet",
        "get_rows",
        "get_cell_value",
        "get_column_data",
        "get_range_values",
        "find_cells",
        "append_row",
        "update_row",
        "set_cell_value",
        "set_range_values",
        "delete_rows",
        "delete_columns",
    ]

    actual_function_names = [tool.get_function_name() for tool in tools]
    assert set(actual_function_names) == set(expected_function_names)


def test_create_workbook(excel_toolkit):
    r"""Test creating a new workbook."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25], ['Bob', 30]]
        result = excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        assert "Workbook created successfully" in result
        assert excel_toolkit.wb is not None
        assert excel_toolkit.file_path == temp_path
        assert 'TestSheet' in excel_toolkit.wb.sheetnames
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_create_workbook_without_data(excel_toolkit):
    r"""Test creating a workbook without data."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        result = excel_toolkit.create_workbook(temp_path)

        assert "Workbook created successfully" in result
        assert excel_toolkit.wb is not None
        assert excel_toolkit.file_path == temp_path
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_delete_workbook(excel_toolkit):
    r"""Test deleting a workbook."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        # Create a file first
        excel_toolkit.create_workbook(temp_path)
        assert os.path.exists(temp_path)

        # Delete the workbook
        result = excel_toolkit.delete_workbook(temp_path)
        assert "deleted successfully" in result
        assert not os.path.exists(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_delete_workbook_nonexistent(excel_toolkit):
    r"""Test deleting a non-existent workbook."""
    result = excel_toolkit.delete_workbook("nonexistent.xlsx")
    assert "does not exist" in result


def test_create_sheet(excel_toolkit):
    r"""Test creating a new sheet."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        # Create workbook first
        excel_toolkit.create_workbook(temp_path)

        data = [['Name', 'Age'], ['Alice', 25]]
        result = excel_toolkit.create_sheet('NewSheet', data)

        assert "created successfully" in result
        assert 'NewSheet' in excel_toolkit.wb.sheetnames
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_create_sheet_no_workbook(excel_toolkit):
    r"""Test creating a sheet without initializing workbook."""
    result = excel_toolkit.create_sheet('TestSheet')
    assert "Workbook not initialized" in result


def test_delete_sheet(excel_toolkit):
    r"""Test deleting a sheet."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        # Create workbook with multiple sheets
        excel_toolkit.create_workbook(temp_path)
        excel_toolkit.create_sheet('SheetToDelete')

        assert 'SheetToDelete' in excel_toolkit.wb.sheetnames

        result = excel_toolkit.delete_sheet('SheetToDelete')
        assert "deleted successfully" in result
        assert 'SheetToDelete' not in excel_toolkit.wb.sheetnames
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_delete_sheet_nonexistent(excel_toolkit):
    r"""Test deleting a non-existent sheet."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        excel_toolkit.create_workbook(temp_path)
        result = excel_toolkit.delete_sheet('NonexistentSheet')
        assert "does not exist" in result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_clear_sheet(excel_toolkit):
    r"""Test clearing a sheet."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        # Create workbook with data
        data = [['Name', 'Age'], ['Alice', 25], ['Bob', 30]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        # Clear the sheet
        result = excel_toolkit.clear_sheet('TestSheet')
        assert "cleared successfully" in result

        # Verify sheet is empty
        rows = excel_toolkit.get_rows('TestSheet')
        assert len(rows) == 0
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_add_data_to_sheet(excel_toolkit):
    r"""Test adding data to a sheet using append_row."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        excel_toolkit.create_workbook(temp_path, 'TestSheet')

        # Add data using append_row
        result1 = excel_toolkit.append_row('TestSheet', ['Alice', 25])
        result2 = excel_toolkit.append_row('TestSheet', ['Bob', 30])
        assert "appended to sheet" in result1
        assert "appended to sheet" in result2

        # Verify data was added
        rows = excel_toolkit.get_rows('TestSheet')
        assert len(rows) == 2
        assert rows[0] == ['Alice', 25]
        assert rows[1] == ['Bob', 30]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_get_rows(excel_toolkit):
    r"""Test getting rows from a sheet."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25], ['Bob', 30], ['Charlie', 35]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        # Get all rows
        all_rows = excel_toolkit.get_rows('TestSheet')
        assert len(all_rows) == 4

        # Get specific range
        range_rows = excel_toolkit.get_rows('TestSheet', 2, 3)
        assert len(range_rows) == 2
        assert range_rows[0] == ['Alice', 25]
        assert range_rows[1] == ['Bob', 30]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_get_rows_no_workbook(excel_toolkit):
    r"""Test getting rows without workbook."""
    result = excel_toolkit.get_rows('TestSheet')
    assert "Workbook not initialized" in result


def test_update_row(excel_toolkit):
    r"""Test updating a row."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25], ['Bob', 30]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        new_data = ['Alice Updated', 26]
        result = excel_toolkit.update_row('TestSheet', 2, new_data)
        assert "Row 2 updated in sheet TestSheet successfully" in result

        # Verify row was updated
        rows = excel_toolkit.get_rows('TestSheet')
        assert rows[1] == ['Alice Updated', 26]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_append_or_update_row_new(excel_toolkit):
    r"""Test appending a new row using append_row."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        new_data = ['Bob', 30]
        result = excel_toolkit.append_row('TestSheet', new_data)
        assert "appended to sheet" in result

        # Verify new row was added
        rows = excel_toolkit.get_rows('TestSheet')
        assert len(rows) == 3
        assert rows[2] == ['Bob', 30]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_append_or_update_row_existing(excel_toolkit):
    r"""Test updating an existing row using update_row."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25], ['Bob', 30]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        updated_data = ['Alice', 26]  # Same name, different age
        result = excel_toolkit.update_row('TestSheet', 2, updated_data)
        assert "updated in sheet TestSheet successfully" in result

        # Verify row was updated
        rows = excel_toolkit.get_rows('TestSheet')
        assert rows[1] == ['Alice', 26]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_delete_rows(excel_toolkit):
    r"""Test deleting rows."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25], ['Bob', 30], ['Charlie', 35]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        # Delete single row
        result = excel_toolkit.delete_rows('TestSheet', 2)
        assert (
            "Deleted rows 2 to 2 from sheet TestSheet successfully" in result
        )

        # Verify row was deleted
        rows = excel_toolkit.get_rows('TestSheet')
        assert len(rows) == 3
        assert rows[0] == ['Name', 'Age']
        assert rows[1] == ['Bob', 30]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_delete_columns(excel_toolkit):
    r"""Test deleting columns."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [
            ['Name', 'Age', 'City'],
            ['Alice', 25, 'NY'],
            ['Bob', 30, 'SF'],
        ]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        # Delete second column (Age)
        result = excel_toolkit.delete_columns('TestSheet', 2)
        assert (
            "Deleted columns 2 to 2 from sheet TestSheet successfully"
            in result
        )

        # Verify column was deleted
        rows = excel_toolkit.get_rows('TestSheet')
        assert len(rows) == 3
        assert rows[0] == ['Name', 'City']
        assert rows[1] == ['Alice', 'NY']
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_get_cell_value(excel_toolkit):
    r"""Test getting cell value."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        value = excel_toolkit.get_cell_value('TestSheet', 'A1')
        assert value == 'Name'

        value = excel_toolkit.get_cell_value('TestSheet', 'B2')
        assert value == 25
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_set_cell_value(excel_toolkit):
    r"""Test setting cell value."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        result = excel_toolkit.set_cell_value(
            'TestSheet', 'A1', 'Updated Name'
        )
        assert "updated successfully" in result

        # Verify cell was updated
        value = excel_toolkit.get_cell_value('TestSheet', 'A1')
        assert value == 'Updated Name'
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_get_column_data(excel_toolkit):
    r"""Test getting column data."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25], ['Bob', 30]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        # Get column by number
        col_data = excel_toolkit.get_column_data('TestSheet', 1)
        assert col_data == ['Name', 'Alice', 'Bob']

        # Get column by letter
        col_data = excel_toolkit.get_column_data('TestSheet', 'B')
        assert col_data == ['Age', 25, 30]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_find_cells(excel_toolkit):
    r"""Test finding cells with specific value."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25], ['Bob', 30], ['Alice', 35]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        # Find all cells with 'Alice'
        cells = excel_toolkit.find_cells('TestSheet', 'Alice')
        assert len(cells) == 2
        assert 'A2' in cells
        assert 'A4' in cells

        # Find in specific column
        cells = excel_toolkit.find_cells('TestSheet', 25, 2)
        assert len(cells) == 1
        assert 'B2' in cells
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_get_range_values(excel_toolkit):
    r"""Test getting range values."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [
            ['Name', 'Age', 'City'],
            ['Alice', 25, 'NY'],
            ['Bob', 30, 'SF'],
        ]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        range_values = excel_toolkit.get_range_values('TestSheet', 'A1:C2')
        assert len(range_values) == 2
        assert range_values[0] == ['Name', 'Age', 'City']
        assert range_values[1] == ['Alice', 25, 'NY']
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_set_range_values(excel_toolkit):
    r"""Test setting range values."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        new_values = [['Bob', 30], ['Charlie', 35]]
        result = excel_toolkit.set_range_values(
            'TestSheet', 'A2:B3', new_values
        )
        assert "Values set for range" in result

        # Verify values were set
        range_values = excel_toolkit.get_range_values('TestSheet', 'A2:B3')
        assert range_values == new_values
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_export_sheet_to_csv(excel_toolkit):
    r"""Test exporting sheet to CSV."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as csv_file:
        csv_path = csv_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25], ['Bob', 30]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        result = excel_toolkit.export_sheet_to_csv('TestSheet', csv_path)
        assert "exported to CSV" in result
        assert os.path.exists(csv_path)

        # Verify CSV content
        df = pd.read_csv(csv_path)
        assert len(df) == 2
        assert list(df.columns) == ['Name', 'Age']
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(csv_path):
            os.remove(csv_path)


def test_append_row(excel_toolkit):
    r"""Test appending a row."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        data = [['Name', 'Age'], ['Alice', 25]]
        excel_toolkit.create_workbook(temp_path, 'TestSheet', data)

        new_row = ['Bob', 30]
        result = excel_toolkit.append_row('TestSheet', new_row)
        assert "appended to sheet" in result

        # Verify row was appended
        rows = excel_toolkit.get_rows('TestSheet')
        assert len(rows) == 3
        assert rows[2] == ['Bob', 30]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_save_workbook(excel_toolkit):
    r"""Test saving workbook."""
    with tempfile.NamedTemporaryFile(
        suffix=".xlsx", delete=False
    ) as temp_file:
        temp_path = temp_file.name

    try:
        excel_toolkit.create_workbook(temp_path)

        # Modify workbook
        excel_toolkit.set_cell_value('Sheet1', 'A1', 'Test Value')

        # Save workbook
        result = excel_toolkit._save_workbook()
        assert "saved successfully" in result

        # Verify file exists and has content
        assert os.path.exists(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_save_workbook_no_workbook(excel_toolkit):
    r"""Test saving when no workbook is loaded."""
    result = excel_toolkit._save_workbook()
    assert "No workbook loaded" in result


def test_initialization_with_file_path(excel_toolkit, sample_xlsx_file):
    r"""Test initialization with existing file path."""
    toolkit = ExcelToolkit(file_path=sample_xlsx_file)
    assert toolkit.file_path == sample_xlsx_file
    assert toolkit.wb is not None


def test_initialization_with_nonexistent_file():
    r"""Test initialization with non-existent file path."""
    toolkit = ExcelToolkit(file_path="nonexistent.xlsx")
    assert toolkit.file_path == "nonexistent.xlsx"
    assert toolkit.wb is None
