<a id="camel.toolkits.excel_toolkit"></a>

<a id="camel.toolkits.excel_toolkit.ExcelToolkit"></a>

## ExcelToolkit

```python
class ExcelToolkit(BaseToolkit):
```

A class representing a toolkit for extract detailed cell information
from an Excel file.

This class provides methods extracting detailed content from Excel files
(including .xls, .xlsx,.csv), and converting the data into
Markdown formatted table.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    timeout: Optional[float] = None,
    file_path: Optional[str] = None
):
```

Initializes a new instance of the ExcelToolkit class.

**Parameters:**

- **timeout** (Optional[float]): The timeout value for API requests in seconds. If None, no timeout is applied. (default: :obj:`None`)
- **file_path** (Optional[str]): Path to an existing Excel file to load. (default: :obj:`None`)

<a id="camel.toolkits.excel_toolkit.ExcelToolkit._validate_file_path"></a>

### _validate_file_path

```python
def _validate_file_path(self, file_path: str):
```

Validate file path for security.

**Parameters:**

- **file_path** (str): The file path to validate.

**Returns:**

  bool: True if path is safe, False otherwise.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit._convert_to_markdown"></a>

### _convert_to_markdown

```python
def _convert_to_markdown(self, df: 'DataFrame'):
```

Convert DataFrame to Markdown format table.

**Parameters:**

- **df** (DataFrame): DataFrame containing the Excel data.

**Returns:**

  str: Markdown formatted table.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.extract_excel_content"></a>

### extract_excel_content

```python
def extract_excel_content(self, document_path: str):
```

Extract and analyze the full content of an Excel file (.xlsx/.xls/.
csv).

Use this tool to read and understand the structure and content of
Excel files. This is typically the first step when working with
existing Excel files.

**Parameters:**

- **document_path** (str): The file path to the Excel file.

**Returns:**

  str: A comprehensive report containing:
- Sheet names and their content in markdown table format
- Detailed cell information including values, colors, and
positions
- Formatted data that's easy to understand and analyze

<a id="camel.toolkits.excel_toolkit.ExcelToolkit._save_workbook"></a>

### _save_workbook

```python
def _save_workbook(self, file_path: Optional[str] = None):
```

Save the current workbook to file.

**Parameters:**

- **file_path** (Optional[str]): The path to save the workbook. If None, uses self.file_path.

**Returns:**

  str: Success or error message.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.create_workbook"></a>

### create_workbook

```python
def create_workbook(
    self,
    file_path: str,
    sheet_name: Optional[str] = None,
    data: Optional[List[List[Union[str, int, float, None]]]] = None
):
```

Create a new Excel workbook from scratch.

Use this when you need to create a new Excel file. This sets up the
toolkit to work with the new file and optionally adds initial data.

**Parameters:**

- **file_path** (str): Where to save the new Excel file. Must end with . xlsx.
- **sheet_name** (Optional[str]): Name for the first sheet. If None, creates "Sheet1". (default: :obj:`None`)
- **data** (Optional[List[List[Union[str, int, float, None]]]]): Initial data as rows. Each inner list is one row. (default: :obj:`None`)

**Returns:**

  str: Success confirmation message or error details

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.delete_workbook"></a>

### delete_workbook

```python
def delete_workbook(self, file_path: Optional[str] = None):
```

Delete a spreadsheet file.

**Parameters:**

- **file_path** (Optional[str]): The path of the file to delete. If None, uses self.file_path.

**Returns:**

  str: Success message.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.create_sheet"></a>

### create_sheet

```python
def create_sheet(
    self,
    sheet_name: str,
    data: Optional[List[List[Union[str, int, float, None]]]] = None
):
```

Create a new sheet with the given sheet name and data.

**Parameters:**

- **sheet_name** (str): The name of the sheet to create.
- **data** (Optional[List[List[Union[str, int, float, None]]]]): The data to write to the sheet.

**Returns:**

  str: Success message.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.delete_sheet"></a>

### delete_sheet

```python
def delete_sheet(self, sheet_name: str):
```

Delete a sheet from the workbook.

**Parameters:**

- **sheet_name** (str): The name of the sheet to delete.

**Returns:**

  str: Success message.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.clear_sheet"></a>

### clear_sheet

```python
def clear_sheet(self, sheet_name: str):
```

Clear all data from a sheet.

**Parameters:**

- **sheet_name** (str): The name of the sheet to clear.

**Returns:**

  str: Success message.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.delete_rows"></a>

### delete_rows

```python
def delete_rows(
    self,
    sheet_name: str,
    start_row: int,
    end_row: Optional[int] = None
):
```

Delete rows from a sheet.

Use this to remove unwanted rows. You can delete single rows or ranges.

**Parameters:**

- **sheet_name** (str): Name of the sheet to modify.
- **start_row** (int): Starting row number to delete (1-based, where 1 is first row).
- **end_row** (Optional[int]): Ending row number to delete (1-based). If None, deletes only start_row. (default: :obj:`None`)

**Returns:**

  str: Success confirmation message or error details

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.delete_columns"></a>

### delete_columns

```python
def delete_columns(
    self,
    sheet_name: str,
    start_col: int,
    end_col: Optional[int] = None
):
```

Delete columns from a sheet.

Use this to remove unwanted columns. You can delete single columns or
ranges.

**Parameters:**

- **sheet_name** (str): Name of the sheet to modify.
- **start_col** (int): Starting column number to delete (1-based, where 1 is column A).
- **end_col** (Optional[int]): Ending column number to delete (1-based). If None, deletes only start_col. (default: :obj:`None`)

**Returns:**

  str: Success confirmation message or error details

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.get_cell_value"></a>

### get_cell_value

```python
def get_cell_value(self, sheet_name: str, cell_reference: str):
```

Get the value from a specific cell.

Use this to read a single cell's value. Useful for checking specific
data points or getting values for calculations.

**Parameters:**

- **sheet_name** (str): Name of the sheet containing the cell.
- **cell_reference** (str): Excel-style cell reference (column letter + row number).

**Returns:**

  Union[str, int, float, None]: The cell's value or error message
Returns None for empty cells.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.set_cell_value"></a>

### set_cell_value

```python
def set_cell_value(
    self,
    sheet_name: str,
    cell_reference: str,
    value: Union[str, int, float, None]
):
```

Set the value of a specific cell.

Use this to update individual cells with new values. Useful for
corrections, calculations, or updating specific data points.

**Parameters:**

- **sheet_name** (str): Name of the sheet containing the cell.
- **cell_reference** (str): Excel-style cell reference (column letter + row number).
- **value** (Union[str, int, float, None]): New value for the cell. (default: :obj:`None`)

**Returns:**

  str: Success confirmation message or error details.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.get_column_data"></a>

### get_column_data

```python
def get_column_data(self, sheet_name: str, column: Union[int, str]):
```

Get all data from a specific column.

Use this to extract all values from a column for analysis or
processing.

**Parameters:**

- **sheet_name** (str): Name of the sheet to read from.
- **column** (Union[int, str]): Column identifier - either number (1-based) or letter.

**Returns:**

  Union[List[Union[str, int, float, None]], str]:
List of all non-empty values in the column or error message

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.find_cells"></a>

### find_cells

```python
def find_cells(
    self,
    sheet_name: str,
    search_value: Union[str, int, float],
    search_column: Optional[Union[int, str]] = None
):
```

Find cells containing a specific value.

Use this to locate where specific data appears in the sheet.

**Parameters:**

- **sheet_name** (str): Name of the sheet to search in.
- **search_value** (Union[str, int, float]): Value to search for.
- **search_column** (Optional[Union[int, str]]): Limit search to specific column. If None, searches entire sheet. (default: :obj:`None`)

**Returns:**

  Union[List[str], str]: List of cell references (like "A5", "B12")
where the value was found, or error message.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.get_range_values"></a>

### get_range_values

```python
def get_range_values(self, sheet_name: str, cell_range: str):
```

Get values from a specific range of cells.

Use this to read a rectangular block of cells at once.

**Parameters:**

- **sheet_name** (str): Name of the sheet to read from.
- **cell_range** (str): Range in Excel format (start:end).

**Returns:**

  Union[List[List[Union[str, int, float, None]]], str]:
2D list where each inner list is a row of cell values, or
error message.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.set_range_values"></a>

### set_range_values

```python
def set_range_values(
    self,
    sheet_name: str,
    cell_range: str,
    values: List[List[Union[str, int, float, None]]]
):
```

Set values for a specific range of cells.

Use this to update multiple cells at once with a 2D array of data.

**Parameters:**

- **sheet_name** (str): Name of the sheet to modify.
- **cell_range** (str): Range in Excel format to update.
- **values** (List[List[Union[str, int, float, None]]]): 2D array of values. Each inner list represents a row.

**Returns:**

  str: Success confirmation message or error details.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.export_sheet_to_csv"></a>

### export_sheet_to_csv

```python
def export_sheet_to_csv(self, sheet_name: str, csv_path: str):
```

Export a specific sheet to CSV format.

Use this to convert Excel sheets to CSV files for compatibility or
data exchange.

**Parameters:**

- **sheet_name** (str): Name of the sheet to export.
- **csv_path** (str): File path where CSV will be saved.

**Returns:**

  str: Success confirmation message or error details.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.get_rows"></a>

### get_rows

```python
def get_rows(
    self,
    sheet_name: str,
    start_row: Optional[int] = None,
    end_row: Optional[int] = None
):
```

Retrieve rows of data from a sheet.

Use this to read data from a sheet. You can get all rows or specify a
range. Returns actual data as lists, making it easy to process
programmatically.

**Parameters:**

- **sheet_name** (str): Name of the sheet to read from.
- **start_row** (Optional[int]): First row to read (1-based). If None, starts from row 1. (default: :obj:`None`)
- **end_row** (Optional[int]): Last row to read (1-based). If None, reads to the end. (default: :obj:`None`)

**Returns:**

  Union[List[List[Union[str, int, float, None]]], str]:
List of rows (each row is a list of cell values) or error
message.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.append_row"></a>

### append_row

```python
def append_row(
    self,
    sheet_name: str,
    row_data: List[Union[str, int, float, None]]
):
```

Add a single row to the end of a sheet.

Use this to add one row of data to the end of existing content.
For multiple rows, use multiple calls to this function.

**Parameters:**

- **sheet_name** (str): Name of the target sheet.
- **row_data** (List[Union[str, int, float, None]]): Single row of data to add.

**Returns:**

  str: Success confirmation message or error details.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.update_row"></a>

### update_row

```python
def update_row(
    self,
    sheet_name: str,
    row_number: int,
    row_data: List[Union[str, int, float, None]]
):
```

Update a specific row in the sheet.

Use this to replace all data in a specific row with new values.

**Parameters:**

- **sheet_name** (str): Name of the sheet to modify.
- **row_number** (int): The row number to update (1-based, where 1 is first row).
- **row_data** (List[Union[str, int, float, None]]): New data for the entire row.

**Returns:**

  str: Success confirmation message or error details.

<a id="camel.toolkits.excel_toolkit.ExcelToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects representing
the functions in the toolkit.
