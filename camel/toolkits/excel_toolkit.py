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

# Enables postponed evaluation of annotations (for string-based type hints)
import os
from typing import TYPE_CHECKING, List, Optional, Union

import pandas as pd

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

# Import only for type hints (not executed at runtime)
if TYPE_CHECKING:
    import pandas as pd

logger = get_logger(__name__)


@MCPServer()
class ExcelToolkit(BaseToolkit):
    r"""A class representing a toolkit for extract detailed cell information
    from an Excel file.

    This class provides methods extracting detailed content from Excel files
    (including .xls, .xlsx,.csv), and converting the data into
    Markdown formatted table.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        file_path: Optional[str] = None,
    ):
        r"""Initializes a new instance of the ExcelToolkit class.

        Args:
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        self.file_path = file_path
        self.wb = None
        if file_path and os.path.exists(file_path):
            from openpyxl import load_workbook

            self.wb = load_workbook(file_path)

    def _convert_to_markdown(self, df: pd.DataFrame) -> str:
        r"""Convert DataFrame to Markdown format table.

        Args:
            df (pd.DataFrame): DataFrame containing the Excel data.

        Returns:
            str: Markdown formatted table.
        """
        from tabulate import tabulate

        md_table = tabulate(df, headers='keys', tablefmt='pipe')
        return str(md_table)

    def extract_excel_content(self, document_path: str) -> str:
        r"""Extract detailed cell information from an Excel file, including
        multiple sheets.

        Args:
            document_path (str): The path of the Excel file.

        Returns:
            str: Extracted excel information, including details of each sheet.
        """
        import pandas as pd
        from openpyxl import load_workbook
        from xls2xlsx import XLS2XLSX

        logger.debug(
            f"Calling extract_excel_content with document_path"
            f": {document_path}"
        )

        if not (
            document_path.endswith("xls")
            or document_path.endswith("xlsx")
            or document_path.endswith("csv")
        ):
            logger.error("Only xls, xlsx, csv files are supported.")
            return (
                f"Failed to process file {document_path}: "
                f"It is not excel format. Please try other ways."
            )

        if document_path.endswith("csv"):
            try:
                df = pd.read_csv(document_path)
                md_table = self._convert_to_markdown(df)
                return f"CSV File Processed:\n{md_table}"
            except Exception as e:
                logger.error(f"Failed to process file {document_path}: {e}")
                return f"Failed to process file {document_path}: {e}"

        if document_path.endswith("xls"):
            output_path = document_path.replace(".xls", ".xlsx")
            x2x = XLS2XLSX(document_path)
            x2x.to_xlsx(output_path)
            document_path = output_path

        # Load the Excel workbook
        wb = load_workbook(document_path, data_only=True)
        sheet_info_list = []

        # Iterate through all sheets
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            cell_info_list = []

            for row in ws.iter_rows():
                for cell in row:
                    row_num = cell.row
                    col_letter = cell.column_letter

                    cell_value = cell.value

                    font_color = None
                    if (
                        cell.font
                        and cell.font.color
                        and "rgb=None" not in str(cell.font.color)
                    ):  # Handle font color
                        font_color = cell.font.color.rgb

                    fill_color = None
                    if (
                        cell.fill
                        and cell.fill.fgColor
                        and "rgb=None" not in str(cell.fill.fgColor)
                    ):  # Handle fill color
                        fill_color = cell.fill.fgColor.rgb

                    cell_info_list.append(
                        {
                            "index": f"{row_num}{col_letter}",
                            "value": cell_value,
                            "font_color": font_color,
                            "fill_color": fill_color,
                        }
                    )

            # Convert the sheet to a DataFrame and then to markdown
            sheet_df = pd.read_excel(
                document_path, sheet_name=sheet, engine='openpyxl'
            )
            markdown_content = self._convert_to_markdown(sheet_df)

            # Collect all information for the sheet
            sheet_info = {
                "sheet_name": sheet,
                "cell_info_list": cell_info_list,
                "markdown_content": markdown_content,
            }
            sheet_info_list.append(sheet_info)

        result_str = ""
        for sheet_info in sheet_info_list:
            result_str += f"""
            Sheet Name: {sheet_info['sheet_name']}
            Cell information list:
            {sheet_info['cell_info_list']}
            
            Markdown View of the content:
            {sheet_info['markdown_content']}
            
            {'-'*40}
            """

        return result_str

    def _save_workbook(self, file_path: Optional[str] = None) -> str:
        r"""Save the current workbook to file.

        Args:
            file_path (Optional[str]): The path to save the workbook.
                If None, uses self.file_path.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("No workbook loaded to save.")

        save_path = file_path or self.file_path
        if not save_path:
            raise ValueError("No file path specified for saving.")

        self.wb.save(save_path)
        return f"Workbook saved successfully to {save_path}"

    def create_workbook(
        self,
        file_path: str,
        sheet_name: Optional[str] = None,
        data: Optional[List[List[Union[str, int, float, None]]]] = None,
    ) -> str:
        r"""Create a new workbook with the given sheet name and data.

        Args:
            file_path (str): The path where the new Excel file will be saved.
            sheet_name (Optional[str]): The name of the sheet to create.
            data (Optional[List[List[Union[str, int, float, None]]]]):
                The data to write to the sheet.

        Returns:
            str: Success message.
        """
        from openpyxl import Workbook

        # Create a new workbook
        wb = Workbook()
        self.wb = wb
        self.file_path = file_path

        # Remove default sheet if we're creating a custom one
        if sheet_name:
            # Remove the default sheet
            wb.remove(wb.active)
            ws = wb.create_sheet(sheet_name)
        else:
            ws = wb.active
            if sheet_name is None:
                sheet_name = "Sheet1"
                ws.title = sheet_name

        # Add data if provided
        if data:
            for row in data:
                ws.append(row)

        # Save the workbook to the specified file path
        wb.save(file_path)

        return f"Workbook created successfully at {file_path}"

    def delete_workbook(self, file_path: Optional[str] = None) -> str:
        r"""Delete a spreadsheet file.

        Args:
            file_path (Optional[str]): The path of the file to delete.
                If None, uses self.file_path.

        Returns:
            str: Success message.
        """
        target_path = file_path or self.file_path
        if not target_path:
            raise ValueError("No file path specified for deletion.")

        if not os.path.exists(target_path):
            return f"File {target_path} does not exist."

        try:
            os.remove(target_path)
            if target_path == self.file_path:
                self.wb = None
                self.file_path = None
            return f"Workbook {target_path} deleted successfully."
        except Exception as e:
            return f"Failed to delete workbook {target_path}: {e}"

    def create_sheet(
        self,
        sheet_name: str,
        data: Optional[List[List[Union[str, int, float, None]]]] = None,
    ) -> str:
        r"""Create a new sheet with the given sheet name and data.

        Args:
            sheet_name (str): The name of the sheet to create.
            data (Optional[List[List[Union[str, int, float, None]]]]):
                The data to write to the sheet.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError(
                "Workbook not initialized. Please create a workbook first."
            )

        if sheet_name in self.wb.sheetnames:
            return f"Sheet {sheet_name} already exists."

        ws = self.wb.create_sheet(sheet_name)
        if data:
            for row in data:
                ws.append(row)

        self._save_workbook()
        return f"Sheet {sheet_name} created successfully."

    def delete_sheet(self, sheet_name: str) -> str:
        r"""Delete a sheet from the workbook.

        Args:
            sheet_name (str): The name of the sheet to delete.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."

        if len(self.wb.sheetnames) == 1:
            return "Cannot delete the last remaining sheet in the workbook."

        ws = self.wb[sheet_name]
        self.wb.remove(ws)
        self._save_workbook()
        return f"Sheet {sheet_name} deleted successfully."

    def clear_sheet(self, sheet_name: str) -> str:
        r"""Clear all data from a sheet.

        Args:
            sheet_name (str): The name of the sheet to clear.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."

        ws = self.wb[sheet_name]

        # Clear all cells
        for row in ws.iter_rows():
            for cell in row:
                cell.value = None

        self._save_workbook()
        return f"Sheet {sheet_name} cleared successfully."

    def add_data_to_sheet(
        self, sheet_name: str, data: List[List[Union[str, int, float, None]]]
    ) -> str:
        r"""Add data to the given sheet.

        Args:
            sheet_name (str): The name of the sheet to add data to.
            data (List[List[Union[str, int, float, None]]]):
                The data to add to the sheet.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError(
                "Workbook not initialized. Please create a workbook first."
            )

        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."

        ws = self.wb[sheet_name]
        if data:
            for row in data:
                ws.append(row)

        self._save_workbook()
        return f"Data added to sheet {sheet_name} successfully."

    def get_rows(
        self,
        sheet_name: str,
        start_row: Optional[int] = None,
        end_row: Optional[int] = None,
    ) -> List[List[Union[str, int, float, None]]]:
        r"""Get all rows or a range of rows from a sheet.

        Args:
            sheet_name (str): The name of the sheet.
            start_row (Optional[int]): Starting row number (1-based).
                If None, starts from first row.
            end_row (Optional[int]): Ending row number (1-based).
                If None, goes to last row.

        Returns:
            List[List[Union[str, int, float, None]]]:
                List of rows, where each row is a list of cell values.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            raise ValueError(f"Sheet {sheet_name} does not exist.")

        ws = self.wb[sheet_name]
        rows = []

        # Get all rows with data
        for row in ws.iter_rows(
            min_row=start_row, max_row=end_row, values_only=True
        ):
            # Skip completely empty rows
            if any(cell is not None for cell in row):
                rows.append(list(row))

        return rows

    def update_row(
        self,
        sheet_name: str,
        row_number: int,
        row_data: List[Union[str, int, float, None]],
    ) -> str:
        r"""Update a specific row in the sheet.

        Args:
            sheet_name (str): The name of the sheet.
            row_number (int): The row number to update (1-based).
            row_data (List[Union[str, int, float, None]]):
                The new data for the row.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."

        ws = self.wb[sheet_name]

        # Clear the existing row first
        for col_idx in range(1, ws.max_column + 1):
            ws.cell(row=row_number, column=col_idx).value = None

        # Set new values
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_number, column=col_idx).value = value

        self._save_workbook()
        return f"Row {row_number} updated in sheet {sheet_name} successfully."

    def append_or_update_row(
        self,
        sheet_name: str,
        row_data: List[Union[str, int, float, None]],
        key_column: int = 1,
        key_value: Optional[Union[str, int, float, None]] = None,
    ) -> str:
        r"""Append a new row or update an existing one based on a key column.

        Args:
            sheet_name (str): The name of the sheet.
            row_data (List[Union[str, int, float, None]]):
                The data for the row.
            key_column (int): The column number to use as key (1-based).
            key_value (Optional[Union[str, int, float, None]]):
                The value to search for in the key column. If None, uses first
                value from row_data.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."

        ws = self.wb[sheet_name]

        # Use first value from row_data as key if not specified
        if key_value is None and row_data:
            key_value = row_data[0]

        # Search for existing row with the key value
        existing_row = None
        for row_idx, row in enumerate(
            ws.iter_rows(min_row=1, values_only=True), 1
        ):
            if len(row) >= key_column and row[key_column - 1] == key_value:
                existing_row = row_idx
                break

        if existing_row:
            # Update existing row
            result = self.update_row(sheet_name, existing_row, row_data)
            return f"Updated existing row {existing_row}: {result}"
        else:
            # Append new row
            result = self.append_row(sheet_name, row_data)
            return f"Appended new row: {result}"

    def delete_rows(
        self, sheet_name: str, start_row: int, end_row: Optional[int] = None
    ) -> str:
        r"""Delete rows from a sheet.

        Args:
            sheet_name (str): The name of the sheet.
            start_row (int): Starting row number to delete (1-based).
            end_row (Optional[int]): Ending row number to delete (1-based).
                If None, deletes only start_row.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."

        ws = self.wb[sheet_name]

        if end_row is None:
            end_row = start_row

        # Delete rows (openpyxl uses 1-based indexing)
        num_rows = end_row - start_row + 1
        ws.delete_rows(start_row, num_rows)

        self._save_workbook()
        return f"Deleted rows {start_row} to {end_row} from sheet \
         {sheet_name} successfully."

    def delete_columns(
        self, sheet_name: str, start_col: int, end_col: Optional[int] = None
    ) -> str:
        r"""Delete columns from a sheet.

        Args:
            sheet_name (str): The name of the sheet.
            start_col (int): Starting column number to delete (1-based).
            end_col (Optional[int]): Ending column number to delete (1-based).
                If None, deletes only start_col.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."

        ws = self.wb[sheet_name]

        if end_col is None:
            end_col = start_col

        # Delete columns (openpyxl uses 1-based indexing)
        num_cols = end_col - start_col + 1
        ws.delete_cols(start_col, num_cols)

        self._save_workbook()
        return f"Deleted columns {start_col} to {end_col} from sheet \
         {sheet_name} successfully."

    def get_cell_value(
        self, sheet_name: str, cell_reference: str
    ) -> Union[str, int, float, None]:
        """Get the value of a specific cell.

        Args:
            sheet_name (str): The name of the sheet.
            cell_reference (str): Cell reference (e.g., 'A1', 'B2').

        Returns:
            Union[str, int, float, None]: The cell value.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            raise ValueError(f"Sheet {sheet_name} does not exist.")

        ws = self.wb[sheet_name]
        return ws[cell_reference].value

    def set_cell_value(
        self,
        sheet_name: str,
        cell_reference: str,
        value: Union[str, int, float, None],
    ) -> str:
        """Set the value of a specific cell.

        Args:
            sheet_name (str): The name of the sheet.
            cell_reference (str): Cell reference (e.g., 'A1', 'B2').
            value (Union[str, int, float, None]):
                The value to set.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."

        ws = self.wb[sheet_name]
        ws[cell_reference] = value
        self._save_workbook()
        return f"Cell {cell_reference} updated successfully in sheet \
         {sheet_name}."

    def get_column_data(
        self, sheet_name: str, column: Union[int, str]
    ) -> List[Union[str, int, float, None]]:
        """Get all data from a specific column.

        Args:
            sheet_name (str): The name of the sheet.
            column (Union[int, str]):
                Column number (1-based) or letter (e.g., 'A', 'B').

        Returns:
            List[Union[str, int, float, None]]: List of values in the column.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            raise ValueError(f"Sheet {sheet_name} does not exist.")

        ws = self.wb[sheet_name]

        if isinstance(column, str):
            col_letter = column.upper()
        else:
            from openpyxl.utils import (  # type: ignore[import]
                get_column_letter,
            )

            col_letter = get_column_letter(column)

        column_data = []
        for cell in ws[col_letter]:
            if cell.value is not None:
                column_data.append(cell.value)

        return column_data

    def find_cells(
        self,
        sheet_name: str,
        search_value: Union[str, int, float],
        search_column: Optional[Union[int, str]] = None,
    ) -> List[str]:
        """Find cells containing a specific value.

        Args:
            sheet_name (str): The name of the sheet.
            search_value (Union[str, int, float]): Value to search for.
            search_column (Optional[Union[int, str]]):
                Specific column to search in. If None, searches entire sheet.

        Returns:
            List[str]: List of cell references containing the value.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            raise ValueError(f"Sheet {sheet_name} does not exist.")

        ws = self.wb[sheet_name]
        found_cells = []

        if search_column:
            # Search in specific column
            if isinstance(search_column, str):
                col_letter = search_column.upper()
                for cell in ws[col_letter]:
                    if cell.value == search_value:
                        found_cells.append(cell.coordinate)
            else:
                from openpyxl.utils import (  # type: ignore[import]
                    get_column_letter,
                )

                col_letter = get_column_letter(search_column)
                for cell in ws[col_letter]:
                    if cell.value == search_value:
                        found_cells.append(cell.coordinate)
        else:
            # Search entire sheet
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value == search_value:
                        found_cells.append(cell.coordinate)

        return found_cells

    def get_range_values(
        self, sheet_name: str, cell_range: str
    ) -> List[List[Union[str, int, float, None]]]:
        """Get values from a specific range of cells.

        Args:
            sheet_name (str): The name of the sheet.
            cell_range (str): Range of cells (e.g., 'A1:C5').

        Returns:
            List[List[Union[str, int, float, None]]]: 2D list of cell values.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            raise ValueError(f"Sheet {sheet_name} does not exist.")

        ws = self.wb[sheet_name]
        range_values = []

        for row in ws[cell_range]:
            row_values = []
            for cell in row:
                row_values.append(cell.value)
            range_values.append(row_values)

        return range_values

    def set_range_values(
        self,
        sheet_name: str,
        cell_range: str,
        values: List[List[Union[str, int, float, None]]],
    ) -> str:
        """Set values for a specific range of cells.

        Args:
            sheet_name (str): The name of the sheet.
            cell_range (str): Range of cells (e.g., 'A1:C5').
            values (List[List[Union[str, int, float, None]]]):
                2D list of values to set.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."

        ws = self.wb[sheet_name]

        # Get the range
        cell_range_obj = ws[cell_range]

        # If it's a single row or column, convert to 2D format
        if not isinstance(cell_range_obj[0], tuple):
            cell_range_obj = [cell_range_obj]

        for row_idx, row in enumerate(cell_range_obj):
            if row_idx < len(values):
                for col_idx, cell in enumerate(row):
                    if col_idx < len(values[row_idx]):
                        cell.value = values[row_idx][col_idx]

        self._save_workbook()
        return f"Values set for range {cell_range} in sheet {sheet_name}."

    def export_sheet_to_csv(self, sheet_name: str, csv_path: str) -> str:
        """Export a specific sheet to CSV format.

        Args:
            sheet_name (str): The name of the sheet to export.
            csv_path (str): Path where the CSV file will be saved.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")

        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."

        import pandas as pd

        # Read the specific sheet
        df = pd.read_excel(self.file_path, sheet_name=sheet_name)
        df.to_csv(csv_path, index=False)

        return f"Sheet {sheet_name} exported to CSV: {csv_path}"

    def append_row(
        self,
        sheet_name: str,
        row_data: List[Union[str, int, float, None]],
    ) -> str:
        """Append a row to the given sheet.

        Args:
            sheet_name (str): The name of the sheet.
            row_data (List[Union[str, int, float, None]]): The data to append.

        Returns:
            str: Success message.
        """
        if not self.wb:
            raise ValueError("Workbook not initialized.")
        if sheet_name not in self.wb.sheetnames:
            return f"Sheet {sheet_name} does not exist."
        ws = self.wb[sheet_name]
        ws.append(row_data)
        self._save_workbook()
        return f"Row appended to sheet {sheet_name} successfully."

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.extract_excel_content),
            FunctionTool(self.create_workbook),
            FunctionTool(self.delete_workbook),
            FunctionTool(self.create_sheet),
            FunctionTool(self.delete_sheet),
            FunctionTool(self.clear_sheet),
            FunctionTool(self.add_data_to_sheet),
            FunctionTool(self.get_rows),
            FunctionTool(self.update_row),
            FunctionTool(self.append_or_update_row),
            FunctionTool(self.delete_rows),
            FunctionTool(self.delete_columns),
            FunctionTool(self.get_cell_value),
            FunctionTool(self.set_cell_value),
            FunctionTool(self.get_column_data),
            FunctionTool(self.find_cells),
            FunctionTool(self.get_range_values),
            FunctionTool(self.set_range_values),
            FunctionTool(self.export_sheet_to_csv),
            FunctionTool(self.append_row),
        ]
