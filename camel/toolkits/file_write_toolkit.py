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
import glob
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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

    @dependencies_required('pylatex', 'fpdf')
    def _write_pdf_file(
        self, file_path: Path, content: str, use_latex: bool = False
    ) -> None:
        r"""Write text content to a PDF file with default formatting.

        Args:
            file_path (Path): The target file path.
            content (str): The text content to write.
            use_latex (bool): Whether to use LaTeX for rendering. (requires
                LaTeX toolchain). If False, uses FPDF for simpler PDF
                generation. (default: :obj: `False`)

        Raises:
            RuntimeError: If the 'pylatex' or 'fpdf' library is not installed
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
                    # Remove leading whitespace
                    stripped_line = line.strip()
                    # Check if the line is intended as a standalone math
                    # expression
                    if (
                        stripped_line.startswith('$')
                        and stripped_line.endswith('$')
                        and len(stripped_line) > 1
                    ):
                        # Extract content between the '$' delimiters
                        math_data = stripped_line[1:-1]
                        doc.append(Math(data=math_data))
                    else:
                        doc.append(NoEscape(line))
                    doc.append(NoEscape(r'\par'))

            doc.generate_pdf(str(file_path), clean_tex=False)

            logger.info(f"Wrote PDF (with LaTeX) to {file_path}")
        else:
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

    def read_from_file(
        self,
        filename: str,
        encoding: Optional[str] = None,
    ) -> Union[str, List[List[str]], dict]:
        r"""Read content from a file.

        Supports multiple formats: Markdown (.md, .markdown), Plaintext (.txt),
        CSV (.csv), JSON (.json), YAML (.yml, .yaml), and HTML (.html, .htm)
        etc.

        Args:
            filename (str): The name or path of the file to read. If a relative
                path is supplied, it is resolved to self.output_dir.
            encoding (Optional[str]): The character encoding to use. (default:
                :obj: `None`)

        Returns:
            Union[str, List[List[str]], dict]: The content of the file. The
                return type depends on the file format:
                - Text formats (txt, md, html, yaml): string
                - CSV: list of lists
                - JSON: dict or list

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file format is not supported or the content
                cannot be parsed.
        """
        file_path = self._resolve_filepath(filename)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Get encoding or use default
        file_encoding = encoding or self.default_encoding
        extension = file_path.suffix.lower()

        try:
            if extension == ".csv":
                import csv

                with file_path.open(
                    "r", encoding=file_encoding, newline=''
                ) as f:
                    reader = csv.reader(f)
                    return list(reader)

            elif extension == ".json":
                import json

                with file_path.open("r", encoding=file_encoding) as f:
                    return json.load(f)

            elif extension in [".yml", ".yaml"]:
                import yaml

                with file_path.open("r", encoding=file_encoding) as f:
                    return yaml.safe_load(f)

            else:
                # For all other formats (txt, md, html, etc.), read as text
                with file_path.open("r", encoding=file_encoding) as f:
                    return f.read()

        except Exception as e:
            error_msg = f"Error reading file {file_path}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def read_file_content(
        self,
        filename: str,
        encoding: Optional[str] = None,
        max_lines: Optional[int] = None,
        start_line: int = 1,
    ) -> str:
        r"""Read file content with optional line range control.

        Use for checking file contents, analyzing logs, or reading
        configuration files.

        Args:
            filename (str): The name or path of the file to read.
            encoding (Optional[str]): The character encoding to use. (default:
                :obj: `None`)
            max_lines (Optional[int]): Maximum number of lines to read. If
                None, reads entire file. (default: :obj: `None`)
            start_line (int): Line number to start reading from (1-indexed).
                (default: :obj: `1`)

        Returns:
            str: The content of the file or specified line range.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If start_line is less than 1 or max_lines is less than
                1.
        """
        if start_line < 1:
            raise ValueError("start_line must be 1 or greater")
        if max_lines is not None and max_lines < 1:
            raise ValueError("max_lines must be 1 or greater")

        file_path = self._resolve_filepath(filename)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_encoding = encoding or self.default_encoding

        try:
            with file_path.open("r", encoding=file_encoding) as f:
                lines = f.readlines()

                # Apply line range filtering
                if start_line > len(lines):
                    return ""

                end_line = len(lines)
                if max_lines is not None:
                    end_line = min(start_line + max_lines - 1, len(lines))

                selected_lines = lines[start_line - 1 : end_line]
                content = ''.join(selected_lines)

                logger.debug(
                    f"Read {len(selected_lines)} lines from {file_path}"
                )
                return content

        except Exception as e:
            error_msg = f"Error reading file content from {file_path}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def replace_in_file(
        self,
        filename: str,
        old_text: str,
        new_text: str,
        count: int = -1,
        encoding: Optional[str] = None,
        case_sensitive: bool = True,
    ) -> str:
        r"""Replace specified string in a file.

        Use for updating specific content in files or fixing errors in code.

        Args:
            filename (str): The name or path of the file to modify.
            old_text (str): The text to search for and replace.
            new_text (str): The text to replace with.
            count (int): Maximum number of replacements to make. If -1, replace
                all occurrences. (default: :obj: `-1`)
            encoding (Optional[str]): The character encoding to use. (default:
                :obj: `None`)
            case_sensitive (bool): Whether the search should be case-sensitive.
                (default: :obj: `True`)

        Returns:
            str: A message indicating the number of replacements made.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If an error occurs during the replacement operation.
        """
        file_path = self._resolve_filepath(filename)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_encoding = encoding or self.default_encoding

        try:
            # Create backup if enabled
            self._create_backup(file_path)

            # Read the file content
            with file_path.open("r", encoding=file_encoding) as f:
                content = f.read()

            # Perform replacement
            if case_sensitive:
                if count == -1:
                    new_content = content.replace(old_text, new_text)
                    replacements = content.count(old_text)
                else:
                    new_content = content.replace(old_text, new_text, count)
                    # Count actual replacements made
                    replacements = min(content.count(old_text), count)
            else:
                # Case-insensitive replacement using regex
                import re

                pattern = re.escape(old_text)
                if count == -1:
                    new_content, replacements = re.subn(
                        pattern, new_text, content, flags=re.IGNORECASE
                    )
                else:
                    new_content, replacements = re.subn(
                        pattern,
                        new_text,
                        content,
                        count=count,
                        flags=re.IGNORECASE,
                    )

            # Write the modified content back to the file
            with file_path.open("w", encoding=file_encoding) as f:
                f.write(new_content)

            msg = (
                f"Replaced {replacements} occurrence(s) of '{old_text}' in "
                f"{file_path}"
            )
            logger.info(msg)
            return msg

        except Exception as e:
            error_msg = f"Error replacing text in file {file_path}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def search_in_file(
        self,
        filename: str,
        search_pattern: str,
        case_sensitive: bool = True,
        use_regex: bool = False,
        context_lines: int = 0,
        encoding: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Search for matching text within file content.

        Use for finding specific content or patterns in files.

        Args:
            filename (str): The name or path of the file to search in.
            search_pattern (str): The text or regex pattern to search for.
            case_sensitive (bool): Whether the search should be case-sensitive.
                (default: :obj: `True`)
            use_regex (bool): Whether to treat search_pattern as a regular
                expression. (default: :obj: `False`)
            context_lines (int): Number of lines before and after each match
                to include in results. (default: :obj: `0`)
            encoding (Optional[str]): The character encoding to use. (default:
                :obj: `None`)

        Returns:
            Dict[str, Any]: A dictionary containing search results with keys:
                - 'matches': List of match information
                - 'total_matches': Total number of matches found
                - 'file_path': Path of the searched file

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If an error occurs during the search operation.
        """
        file_path = self._resolve_filepath(filename)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_encoding = encoding or self.default_encoding

        try:
            with file_path.open("r", encoding=file_encoding) as f:
                lines = f.readlines()

            matches = []
            flags = 0 if case_sensitive else re.IGNORECASE

            for line_num, line in enumerate(lines, 1):
                line_content = line.rstrip('\n\r')

                if use_regex:
                    # Use regex search
                    pattern_matches = list(
                        re.finditer(search_pattern, line_content, flags)
                    )
                    for match in pattern_matches:
                        match_info = {
                            'line_number': line_num,
                            'line_content': line_content,
                            'match_text': match.group(),
                            'start_pos': match.start(),
                            'end_pos': match.end(),
                        }

                        # Add context lines if requested
                        if context_lines > 0:
                            start_context = max(
                                0, line_num - context_lines - 1
                            )
                            end_context = min(
                                len(lines), line_num + context_lines
                            )
                            context = [
                                f"{i+1}: {lines[i].rstrip()}"
                                for i in range(start_context, end_context)
                            ]
                            match_info['context'] = context

                        matches.append(match_info)
                else:
                    # Simple string search
                    search_text = (
                        search_pattern
                        if case_sensitive
                        else search_pattern.lower()
                    )
                    search_line = (
                        line_content
                        if case_sensitive
                        else line_content.lower()
                    )

                    start_pos = 0
                    while True:
                        pos = search_line.find(search_text, start_pos)
                        if pos == -1:
                            break

                        match_info = {
                            'line_number': line_num,
                            'line_content': line_content,
                            'match_text': line_content[
                                pos : pos + len(search_pattern)
                            ],
                            'start_pos': pos,
                            'end_pos': pos + len(search_pattern),
                        }

                        # Add context lines if requested
                        if context_lines > 0:
                            start_context = max(
                                0, line_num - context_lines - 1
                            )
                            end_context = min(
                                len(lines), line_num + context_lines
                            )
                            context = [
                                f"{i+1}: {lines[i].rstrip()}"
                                for i in range(start_context, end_context)
                            ]
                            match_info['context'] = context

                        matches.append(match_info)
                        start_pos = pos + 1

            result = {
                'matches': matches,
                'total_matches': len(matches),
                'file_path': str(file_path),
                'search_pattern': search_pattern,
                'case_sensitive': case_sensitive,
                'use_regex': use_regex,
            }

            logger.debug(
                f"Found {len(matches)} matches for '{search_pattern}' in "
                f"{file_path}"
            )
            return result

        except Exception as e:
            error_msg = f"Error searching in file {file_path}: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def find_files(
        self,
        pattern: str,
        directory: Optional[str] = None,
        recursive: bool = True,
        case_sensitive: bool = True,
        include_hidden: bool = False,
    ) -> List[str]:
        r"""Find files by name pattern in specified directory.

        Use for locating files with specific naming patterns.

        Args:
            pattern (str): File name pattern to search for. Supports wildcards
                (* and ?). Examples: "*.txt", "config*.json", "test_*.py"
            directory (Optional[str]): Directory to search in. If None, uses
                the toolkit's output directory. (default: :obj: `None`)
            recursive (bool): Whether to search subdirectories recursively.
                (default: :obj: `True`)
            case_sensitive (bool): Whether the pattern matching should be
                case-sensitive. (default: :obj: `True`)
            include_hidden (bool): Whether to include hidden files (starting
                with .) in results. (default: :obj: `False`)

        Returns:
            List[str]: List of file paths matching the pattern.

        Raises:
            FileNotFoundError: If the specified directory does not exist.
            ValueError: If an error occurs during the search operation.
        """
        if directory is None:
            search_dir = self.output_dir
        else:
            search_dir = Path(directory).resolve()

        if not search_dir.exists():
            raise FileNotFoundError(f"Directory not found: {search_dir}")

        if not search_dir.is_dir():
            raise ValueError(f"Path is not a directory: {search_dir}")

        try:
            matches = []

            # Prepare for case-insensitive matching
            if not case_sensitive:
                # For case-insensitive matching, we'll handle it manually
                # since glob doesn't have a direct case-insensitive option
                pass

            if recursive:
                # Use ** for recursive search
                if '/' in pattern or '\\' in pattern:
                    # Pattern includes path separators
                    glob_pattern = str(search_dir / pattern)
                else:
                    # Simple filename pattern
                    glob_pattern = str(search_dir / "**" / pattern)

                file_paths = glob.glob(glob_pattern, recursive=True)
            else:
                # Search only in the specified directory
                glob_pattern = str(search_dir / pattern)
                file_paths = glob.glob(glob_pattern, recursive=False)

            # Filter results
            for file_path in file_paths:
                path_obj = Path(file_path)

                # Skip directories (only return files)
                if not path_obj.is_file():
                    continue

                # Handle hidden files
                if not include_hidden and path_obj.name.startswith('.'):
                    continue

                # Handle case sensitivity for systems that don't support it
                # natively
                if not case_sensitive:
                    # Re-check the filename with case-insensitive matching
                    import fnmatch

                    filename = path_obj.name
                    if not fnmatch.fnmatch(filename.lower(), pattern.lower()):
                        continue

                matches.append(str(path_obj))

            # Sort results for consistent output
            matches.sort()

            logger.debug(
                f"Found {len(matches)} files matching pattern '{pattern}' in "
                f"{search_dir}"
            )
            return matches

        except Exception as e:
            error_msg = (
                f"Error finding files with \
                pattern '{pattern}' in {search_dir}:"
                f"{e}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

    def get_tools(self) -> List[FunctionTool]:
        r"""Return a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the available functions in this toolkit.
        """
        return [
            FunctionTool(self.write_to_file),
            FunctionTool(self.read_from_file),
            FunctionTool(self.read_file_content),
            FunctionTool(self.replace_in_file),
            FunctionTool(self.search_in_file),
            FunctionTool(self.find_files),
        ]
