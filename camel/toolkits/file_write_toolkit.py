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
from camel.utils import MCPServer, dependencies_required

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
                (default: :obj:`None`)
            default_encoding (str): Default character encoding for text
                operations. (default: :obj:`utf-8`)
            backup_enabled (bool): Whether to create backups of existing files
                before overwriting. (default: :obj:`True`)
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
            encoding (str): Character encoding to use. (default: :obj:`utf-8`)
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

    @dependencies_required('pylatex', 'reportlab')
    def _write_pdf_file(
        self, file_path: Path, content: str, use_latex: bool = False
    ) -> None:
        r"""Write text content to a PDF file with default formatting.

        Args:
            file_path (Path): The target file path.
            content (str): The text content to write.
            use_latex (bool): Whether to use LaTeX for rendering. (requires
                LaTeX toolchain). If False, uses ReportLab for simpler PDF
                generation. (default: :obj:`False`)

        Raises:
            RuntimeError: If the 'pylatex' is not installed
            when use_latex=True.
        """
        if use_latex:
            from pylatex import (
                Command,
                Document,
                Math,
                Section,
            )
            from pylatex.utils import (
                NoEscape,
            )

            doc = Document(documentclass="article")
            doc.packages.append(Command('usepackage', 'amsmath'))
            with doc.create(Section('Generated Content')):
                for line in content.split('\n'):
                    stripped_line = line.strip()

                    # Skip empty lines
                    if not stripped_line:
                        continue

                    # Convert Markdown-like headers
                    if stripped_line.startswith('## '):
                        header = stripped_line[3:]
                        doc.append(NoEscape(r'\subsection*{%s}' % header))
                        continue
                    elif stripped_line.startswith('# '):
                        header = stripped_line[2:]
                        doc.append(NoEscape(r'\section*{%s}' % header))
                        continue
                    elif stripped_line.strip() == '---':
                        doc.append(NoEscape(r'\hrule'))
                        continue

                    # Detect standalone math expressions like $...$
                    if (
                        stripped_line.startswith('$')
                        and stripped_line.endswith('$')
                        and len(stripped_line) > 1
                    ):
                        math_data = stripped_line[1:-1]
                        doc.append(Math(data=math_data))
                    else:
                        doc.append(NoEscape(stripped_line))
                    doc.append(NoEscape(r'\par'))

                doc.generate_pdf(str(file_path), clean_tex=True)

            logger.info(f"Wrote PDF (with LaTeX) to {file_path}")
        else:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import (
                A4,
            )
            from reportlab.lib.styles import (
                ParagraphStyle,
                getSampleStyleSheet,
            )
            from reportlab.lib.units import (
                inch,
            )
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )

            def to_pdf(content):
                # Initialize PDF document
                doc = SimpleDocTemplate(
                    str(file_path),
                    pagesize=A4,
                    leftMargin=36,
                    rightMargin=36,
                    topMargin=36,
                    bottomMargin=36,
                )

                # Set up styles
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(
                    'DocumentTitle',
                    parent=styles['Heading1'],
                    alignment=1,  # Center alignment
                    spaceAfter=12,
                    fontSize=16,
                    leading=20,
                )

                heading2_style = ParagraphStyle(
                    'Heading2',
                    parent=styles['Heading2'],
                    fontSize=14,
                    leading=18,
                    spaceAfter=10,
                )

                normal_style = ParagraphStyle(
                    'BodyText',
                    parent=styles['Normal'],
                    fontSize=10,
                    leading=14,
                    spaceAfter=6,
                )

                # Create a paragraph style for table cells with word wrap
                table_cell_style = ParagraphStyle(
                    'TableCell',
                    parent=normal_style,
                    fontSize=9,
                    leading=12,
                    wordWrap='CJK',  # Ensures proper wrapping
                    alignment=4,  # Justified alignment
                )

                # Create a paragraph style for table headers
                table_header_style = ParagraphStyle(
                    'TableHeader',
                    parent=normal_style,
                    fontSize=10,
                    leading=14,
                    wordWrap='CJK',
                    alignment=1,  # Center alignment
                    fontName='Helvetica-Bold',
                )

                # Parse markdown content
                lines = content.strip().split('\n')
                document_title = "Document"  # Default title

                # Extract document title (if first line is a heading)
                if lines and lines[0].strip().startswith('# '):
                    document_title = lines[0].strip()[2:].strip()
                    lines = lines[1:]

                elements = []

                # Add title
                elements.append(Paragraph(document_title, title_style))
                elements.append(Spacer(1, 0.25 * inch))

                # Split document into sections
                sections = []
                current_lines = []
                table_lines = []
                in_table = False
                section_title = None

                for line in lines:
                    # Start of a new section
                    if line.strip().startswith(
                        '# '
                    ) or line.strip().startswith('## '):
                        # Save previous section if exists
                        if current_lines:
                            sections.append(
                                {
                                    "title": section_title,
                                    "content": current_lines,
                                    "is_table": False,
                                }
                            )
                            current_lines = []

                        # Start new section
                        if line.strip().startswith('# '):
                            section_title = line.strip()[2:].strip()
                        else:
                            section_title = line.strip()[3:].strip()

                        continue

                    # Check for table lines
                    if line.strip().startswith('|') and line.strip().endswith(
                        '|'
                    ):
                        if not in_table:
                            in_table = True
                            # If we were collecting text, finalize that section
                            if current_lines:
                                sections.append(
                                    {
                                        "title": section_title,
                                        "content": current_lines,
                                        "is_table": False,
                                    }
                                )
                                current_lines = []
                                section_title = None
                            table_lines = [line]
                        else:
                            table_lines.append(line)
                    else:
                        if in_table:
                            in_table = False
                            # Process completed table
                            if table_lines:
                                sections.append(
                                    {
                                        "title": None,
                                        "content": table_lines,
                                        "is_table": True,
                                    }
                                )
                                table_lines = []
                            current_lines = [line]
                        else:
                            current_lines.append(line)

                # Add final section
                if in_table and table_lines:
                    sections.append(
                        {
                            "title": None,
                            "content": table_lines,
                            "is_table": True,
                        }
                    )
                elif current_lines:
                    sections.append(
                        {
                            "title": section_title,
                            "content": current_lines,
                            "is_table": False,
                        }
                    )

                # Process each section
                for section in sections:
                    # Add section title if present
                    if section["title"]:
                        elements.append(
                            Paragraph(section["title"], heading2_style)
                        )
                        elements.append(Spacer(1, 0.1 * inch))

                    if section["is_table"]:
                        # Process table content
                        table_data = []
                        header_row_found = False
                        separator_row_idx = None

                        # First identify the separator row (if any)
                        for i, line in enumerate(section["content"]):
                            if line.strip().startswith(
                                '|'
                            ) and line.strip().endswith('|'):
                                cells = [
                                    cell.strip()
                                    for cell in line.strip()[1:-1].split('|')
                                ]
                                # Check for separator row with dashes
                                if any('-' * 3 in cell for cell in cells):
                                    separator_row_idx = i
                                    break

                        # If separator found, the row before it is header
                        if (
                            separator_row_idx is not None
                            and separator_row_idx > 0
                        ):
                            header_row_idx = separator_row_idx - 1
                            header_row_found = True
                        else:
                            header_row_idx = (
                                0  # Assume first row is header if no separator
                            )
                            header_row_found = True

                        # Process table rows
                        for i, line in enumerate(section["content"]):
                            if line.strip().startswith(
                                '|'
                            ) and line.strip().endswith('|'):
                                cells = [
                                    cell.strip()
                                    for cell in line.strip()[1:-1].split('|')
                                ]

                                # Skip separator row with dashes
                                if i == separator_row_idx:
                                    continue

                                # Make sure all cells are wrapped properly
                                formatted_cells = []
                                for cell in cells:
                                    # Headers get special formatting
                                    if (
                                        i == header_row_idx
                                        and header_row_found
                                    ):
                                        formatted_cells.append(
                                            Paragraph(cell, table_header_style)
                                        )
                                    else:
                                        formatted_cells.append(
                                            Paragraph(cell, table_cell_style)
                                        )

                                # Ensure consistent column count
                                if table_data and len(formatted_cells) < len(
                                    table_data[0]
                                ):
                                    formatted_cells.extend(
                                        [Paragraph('', table_cell_style)]
                                        * (
                                            len(table_data[0])
                                            - len(formatted_cells)
                                        )
                                    )

                                table_data.append(formatted_cells)

                        if table_data:
                            try:
                                # Standardize column count
                                max_cols = max(len(row) for row in table_data)
                                for row in table_data:
                                    while len(row) < max_cols:
                                        row.append(
                                            Paragraph('', table_cell_style)
                                        )

                                # Calculate dynamic column widths
                                available_width = doc.width

                                # Start with equal column widths
                                col_widths = [
                                    available_width / max_cols
                                ] * max_cols

                                # Adjust based on content length
                                content_lengths = [0] * max_cols
                                for row in table_data:
                                    for i, cell in enumerate(row):
                                        if hasattr(cell, 'text'):
                                            content_lengths[i] = max(
                                                content_lengths[i],
                                                min(len(cell.text), 50),
                                            )  # Cap max influence

                                # Calculate weighted widths with minimum size
                                if sum(content_lengths) > 0:
                                    total_content = sum(content_lengths)
                                    col_widths = [
                                        max(
                                            (
                                                length
                                                / total_content
                                                * available_width
                                            ),
                                            available_width / max_cols / 2,
                                        )
                                        for length in content_lengths
                                    ]

                                    if sum(col_widths) > available_width:
                                        scale = available_width / sum(
                                            col_widths
                                        )
                                        col_widths = [
                                            w * scale for w in col_widths
                                        ]

                                # Create and style table
                                table = Table(
                                    table_data,
                                    colWidths=col_widths,
                                    repeatRows=1 if header_row_found else 0,
                                )

                                table_style = TableStyle(
                                    [
                                        # Header styling
                                        (
                                            'BACKGROUND',
                                            (0, 0),
                                            (-1, 0),
                                            colors.lightgrey
                                            if header_row_found
                                            else colors.white,
                                        ),
                                        (
                                            'TEXTCOLOR',
                                            (0, 0),
                                            (-1, 0),
                                            colors.black,
                                        ),
                                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                                        (
                                            'FONTNAME',
                                            (0, 0),
                                            (-1, 0),
                                            'Helvetica-Bold'
                                            if header_row_found
                                            else 'Helvetica',
                                        ),
                                        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                                        # Body styling
                                        (
                                            'BACKGROUND',
                                            (0, 1),
                                            (-1, -1),
                                            colors.white,
                                        ),
                                        (
                                            'GRID',
                                            (0, 0),
                                            (-1, -1),
                                            1,
                                            colors.black,
                                        ),
                                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                                    ]
                                )

                                table.setStyle(table_style)
                                elements.append(table)
                                elements.append(Spacer(1, 0.3 * inch))
                            except Exception as e:
                                logger.warning(
                                    f"Table formatting failed: {e}. "
                                    "Using plain text."
                                )
                                for line in section["content"]:
                                    elements.append(
                                        Paragraph(line.strip(), normal_style)
                                    )
                                    elements.append(Spacer(1, 0.05 * inch))
                    else:
                        # Process regular text content
                        for line in section["content"]:
                            if line.strip():
                                elements.append(
                                    Paragraph(line.strip(), normal_style)
                                )
                                elements.append(Spacer(1, 0.05 * inch))
                # Try to build the PDF, with fallback options
                try:
                    doc.build(elements)
                except Exception as e:
                    # If complex formatting fails, try a simpler approach
                    logger.warning(
                        f"Complex PDF rendering failed: {e}. "
                        "Falling back to simpler format."
                    )
                    elements = [
                        Paragraph(document_title, title_style),
                        Spacer(1, 0.25 * inch),
                    ]

                    # Add all content in simpler format
                    for line in content.strip().split('\n'):
                        if line.strip():
                            if line.strip().startswith('# '):
                                elements.append(
                                    Paragraph(
                                        line.strip()[2:], styles['Heading1']
                                    )
                                )
                            elif line.strip().startswith('## '):
                                elements.append(
                                    Paragraph(
                                        line.strip()[3:], styles['Heading2']
                                    )
                                )
                            else:
                                elements.append(
                                    Paragraph(line.strip(), styles['Normal'])
                                )
                            elements.append(Spacer(1, 0.05 * inch))

                    doc.build(elements)

            to_pdf(content)

            logger.debug(f"Wrote PDF to {file_path} with ReportLab formatting")

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
            encoding (str): Character encoding to use. (default: :obj:`utf-8`)
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
            encoding (str): Character encoding to use. (default: :obj:`utf-8`)
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
            encoding (str): Character encoding to use. (default: :obj:`utf-8`)
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
            encoding (str): Character encoding to use. (default: :obj:`utf-8`)
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
            encoding (str): Character encoding to use. (default: :obj:`utf-8`)
        """
        with file_path.open("w", encoding=encoding) as f:
            f.write(content)
        logger.debug(f"Wrote Markdown to {file_path} with {encoding} encoding")

    def write_to_file(
        self,
        content: Union[str, List[List[str]]],
        filename: str,
        encoding: Optional[str] = None,
        use_latex: bool = False,
    ) -> str:
        r"""Write the given content to a file.

        If the file exists, it will be overwritten. Supports multiple formats:
        Markdown (.md, .markdown, default), Plaintext (.txt), CSV (.csv),
        DOC/DOCX (.doc, .docx), PDF (.pdf), JSON (.json), YAML (.yml, .yaml),
        and HTML (.html, .htm).

        Args:
            content (Union[str, List[List[str]]]): The content to write to the
                file. Content format varies by file type:
                - Text formats (txt, md, html, yaml): string
                - CSV: string or list of lists
                - JSON: string or serializable object
            filename (str): The name or path of the file. If a relative path is
                supplied, it is resolved to self.output_dir.
            encoding (Optional[str]): The character encoding to use. (default:
                :obj: `None`)
            use_latex (bool): For PDF files, whether to use LaTeX rendering
                (True) or simple FPDF rendering (False). (default: :obj:
                `False`)

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
                self._write_pdf_file(
                    file_path, str(content), use_latex=use_latex
                )
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
