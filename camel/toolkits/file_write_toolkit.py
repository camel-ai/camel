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


import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)

# Default format when no extension is provided
DEFAULT_FORMAT = '.md'


@MCPServer()
class FileWriteToolkit(BaseToolkit):
    r"""A toolkit for creating, writing, and modifying text in files.

    This class provides cross-platform (macOS, Linux, Windows) support for
    writing to various file formats (Markdown, DOCX, PDF, and plaintext),
    replacing text in existing files, automatic backups, custom encoding,
    and enhanced formatting options for specialized formats.
    """

    def __init__(
        self,
        output_dir: str = "./",
        timeout: Optional[float] = None,
        default_encoding: str = "utf-8",
        backup_enabled: bool = True,
    ) -> None:
        r"""Initialize the FileWriteToolkit.

        Args:
            output_dir (str): The default directory for output files.
                Defaults to the current working directory.
            timeout (Optional[float]): The timeout for the toolkit.
                (default: :obj: `None`)
            default_encoding (str): Default character encoding for text
                operations. (default: :obj: `utf-8`)
            backup_enabled (bool): Whether to create backups of existing files
                before overwriting. (default: :obj: `True`)
        """
        super().__init__(timeout=timeout)
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.default_encoding = default_encoding
        self.backup_enabled = backup_enabled
        logger.info(
            f"FileWriteToolkit initialized with output directory"
            f": {self.output_dir}, encoding: {default_encoding}"
        )

    def _resolve_filepath(self, file_path: str) -> Path:
        r"""Convert the given string path to a Path object.

        If the provided path is not absolute, it is made relative to the
        default output directory. The filename part is sanitized to replace
        spaces and special characters with underscores, ensuring safe usage
        in downstream processing.

        Args:
            file_path (str): The file path to resolve.

        Returns:
            Path: A fully resolved (absolute) and sanitized Path object.
        """
        path_obj = Path(file_path)
        if not path_obj.is_absolute():
            path_obj = self.output_dir / path_obj

        sanitized_filename = self._sanitize_filename(path_obj.name)
        path_obj = path_obj.parent / sanitized_filename
        return path_obj.resolve()

    def _write_text_file(
        self, file_path: Path, content: str, encoding: str = "utf-8"
    ) -> None:
        r"""Write text content to a plaintext file.

        Args:
            file_path (Path): The target file path.
            content (str): The text content to write.
            encoding (str): Character encoding to use. (default: :obj: `utf-8`)
        """
        with file_path.open("w", encoding=encoding) as f:
            f.write(content)
        logger.debug(f"Wrote text to {file_path} with {encoding} encoding")

    def _create_backup(self, file_path: Path) -> None:
        r"""Create a backup of the file if it exists and backup is enabled.

        Args:
            file_path (Path): Path to the file to backup.
        """
        import shutil

        if not self.backup_enabled or not file_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.parent / f"{file_path.name}.{timestamp}.bak"
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup at {backup_path}")

    def _write_docx_file(self, file_path: Path, content: str) -> None:
        r"""Write text content to a DOCX file with default formatting.

        Args:
            file_path (Path): The target file path.
            content (str): The text content to write.
        """
        import docx

        # Use default formatting values
        font_name = 'Calibri'
        font_size = 11
        line_spacing = 1.0

        document = docx.Document()
        style = document.styles['Normal']
        style.font.name = font_name
        style.font.size = docx.shared.Pt(font_size)
        style.paragraph_format.line_spacing = line_spacing

        # Split content into paragraphs and add them
        for para_text in content.split('\n'):
            para = document.add_paragraph(para_text)
            para.style = style

        document.save(str(file_path))
        logger.debug(f"Wrote DOCX to {file_path} with default formatting")

    def _write_pdf_file(self, file_path: Path, content: str, **kwargs) -> None:
        r"""Write text content to a PDF file with default formatting.

        Args:
            file_path (Path): The target file path.
            content (str): The text content to write.

        Raises:
            RuntimeError: If the 'fpdf' library is not installed.
        """
        from fpdf import FPDF

        # Use default formatting values
        font_family = 'Arial'
        font_size = 12
        font_style = ''
        line_height = 10
        margin = 10

        pdf = FPDF()
        pdf.set_margins(margin, margin, margin)

        pdf.add_page()
        pdf.set_font(font_family, style=font_style, size=font_size)

        # Split content into paragraphs and add them
        for para in content.split('\n'):
            if para.strip():  # Skip empty paragraphs
                pdf.multi_cell(0, line_height, para)
            else:
                pdf.ln(line_height)  # Add empty line

        pdf.output(str(file_path))
        logger.debug(f"Wrote PDF to {file_path} with custom formatting")

    def _write_csv_file(
        self,
        file_path: Path,
        content: Union[str, List[List]],
        encoding: str = "utf-8",
    ) -> None:
        r"""Write CSV content to a file.

        Args:
            file_path (Path): The target file path.
            content (Union[str, List[List]]): The CSV content as a string or
                list of lists.
            encoding (str): Character encoding to use. (default: :obj: `utf-8`)
        """
        import csv

        with file_path.open("w", encoding=encoding, newline='') as f:
            if isinstance(content, str):
                f.write(content)
            else:
                writer = csv.writer(f)
                writer.writerows(content)
        logger.debug(f"Wrote CSV to {file_path} with {encoding} encoding")

    def _write_json_file(
        self,
        file_path: Path,
        content: str,
        encoding: str = "utf-8",
    ) -> None:
        r"""Write JSON content to a file.

        Args:
            file_path (Path): The target file path.
            content (str): The JSON content as a string.
            encoding (str): Character encoding to use. (default: :obj: `utf-8`)
        """
        import json

        with file_path.open("w", encoding=encoding) as f:
            if isinstance(content, str):
                try:
                    # Try parsing as JSON string first
                    data = json.loads(content)
                    json.dump(data, f, ensure_ascii=False)
                except json.JSONDecodeError:
                    # If not valid JSON string, write as is
                    f.write(content)
            else:
                # If not string, dump as JSON
                json.dump(content, f, ensure_ascii=False)
        logger.debug(f"Wrote JSON to {file_path} with {encoding} encoding")

    def _write_yaml_file(
        self,
        file_path: Path,
        content: str,
        encoding: str = "utf-8",
    ) -> None:
        r"""Write YAML content to a file.

        Args:
            file_path (Path): The target file path.
            content (str): The YAML content as a string.
            encoding (str): Character encoding to use. (default: :obj: `utf-8`)
        """
        with file_path.open("w", encoding=encoding) as f:
            f.write(content)
        logger.debug(f"Wrote YAML to {file_path} with {encoding} encoding")

    def _write_html_file(
        self, file_path: Path, content: str, encoding: str = "utf-8"
    ) -> None:
        r"""Write text content to an HTML file.

        Args:
            file_path (Path): The target file path.
            content (str): The HTML content to write.
            encoding (str): Character encoding to use. (default: :obj: `utf-8`)
        """
        with file_path.open("w", encoding=encoding) as f:
            f.write(content)
        logger.debug(f"Wrote HTML to {file_path} with {encoding} encoding")

    def _write_markdown_file(
        self, file_path: Path, content: str, encoding: str = "utf-8"
    ) -> None:
        r"""Write text content to a Markdown file.

        Args:
            file_path (Path): The target file path.
            content (str): The Markdown content to write.
            encoding (str): Character encoding to use. (default: :obj: `utf-8`)
        """
        with file_path.open("w", encoding=encoding) as f:
            f.write(content)
        logger.debug(f"Wrote Markdown to {file_path} with {encoding} encoding")

    def write_to_file(
        self,
        content: Union[str, List[List[str]]],
        filename: str,
        encoding: Optional[str] = None,
    ) -> str:
        r"""Write the given content to a file.

        If the file exists, it will be overwritten. Supports multiple formats:
        Markdown (.md, .markdown, default), Plaintext (.txt), CSV (.csv),
        DOC/DOCX (.doc, .docx), PDF (.pdf), JSON (.json), YAML (.yml, .yaml),
        and HTML (.html, .htm).

        Args:
            content (Union[str, List[List[str]]]): The content to write to the
                file. For all formats, content must be a string or list in the
                appropriate format.
            filename (str): The name or path of the file. If a relative path is
                supplied, it is resolved to self.output_dir.
            encoding (Optional[str]): The character encoding to use. (default:
                :obj: `None`)

        Returns:
            str: A message indicating success or error details.
        """
        file_path = self._resolve_filepath(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup if file exists
        self._create_backup(file_path)

        extension = file_path.suffix.lower()

        # If no extension is provided, use the default format
        if extension == "":
            file_path = file_path.with_suffix(DEFAULT_FORMAT)
            extension = DEFAULT_FORMAT

        try:
            # Get encoding or use default
            file_encoding = encoding or self.default_encoding

            if extension in [".doc", ".docx"]:
                self._write_docx_file(file_path, str(content))
            elif extension == ".pdf":
                self._write_pdf_file(file_path, str(content))
            elif extension == ".csv":
                self._write_csv_file(
                    file_path, content, encoding=file_encoding
                )
            elif extension == ".json":
                self._write_json_file(
                    file_path,
                    content,  # type: ignore[arg-type]
                    encoding=file_encoding,
                )
            elif extension in [".yml", ".yaml"]:
                self._write_yaml_file(
                    file_path, str(content), encoding=file_encoding
                )
            elif extension in [".html", ".htm"]:
                self._write_html_file(
                    file_path, str(content), encoding=file_encoding
                )
            elif extension in [".md", ".markdown"]:
                self._write_markdown_file(
                    file_path, str(content), encoding=file_encoding
                )
            else:
                # Fallback to simple text writing for unknown or .txt
                # extensions
                self._write_text_file(
                    file_path, str(content), encoding=file_encoding
                )

            msg = f"Content successfully written to file: {file_path}"
            logger.info(msg)
            return msg
        except Exception as e:
            error_msg = (
                f"Error occurred while writing to file {file_path}: {e}"
            )
            logger.error(error_msg)
            return error_msg

    def get_tools(self) -> List[FunctionTool]:
        r"""Return a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the available functions in this toolkit.
        """
        return [
            FunctionTool(self.write_to_file),
        ]

    def _sanitize_filename(self, filename: str) -> str:
        r"""Sanitize a filename by replacing any character that is not
        alphanumeric, a dot (.), hyphen (-), or underscore (_) with an
        underscore (_).

        Args:
            filename (str): The original filename which may contain spaces or
                special characters.

        Returns:
            str: The sanitized filename with disallowed characters replaced by
                underscores.
        """
        safe = re.sub(r'[^\w\-.]', '_', filename)
        return safe
