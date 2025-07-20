<a id="camel.toolkits.file_write_toolkit"></a>

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit"></a>

## FileWriteToolkit

```python
class FileWriteToolkit(BaseToolkit):
```

A toolkit for creating, writing, and modifying text in files.

This class provides cross-platform (macOS, Linux, Windows) support for
writing to various file formats (Markdown, DOCX, PDF, and plaintext),
replacing text in existing files, automatic filename uniquification to
prevent overwrites, custom encoding and enhanced formatting options for
specialized formats.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    working_directory: Optional[str] = None,
    timeout: Optional[float] = None,
    default_encoding: str = 'utf-8',
    backup_enabled: bool = True
):
```

Initialize the FileWriteToolkit.

**Parameters:**

- **working_directory** (str, optional): The default directory for output files. If not provided, it will be determined by the `CAMEL_WORKDIR` environment variable (if set). If the environment variable is not set, it defaults to `camel_working_dir`.
- **timeout** (Optional[float]): The timeout for the toolkit. (default: :obj:`None`)
- **default_encoding** (str): Default character encoding for text operations. (default: :obj:`utf-8`)
- **backup_enabled** (bool): Whether to create backups of existing files before overwriting. (default: :obj:`True`)

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._resolve_filepath"></a>

### _resolve_filepath

```python
def _resolve_filepath(self, file_path: str):
```

Convert the given string path to a Path object.

If the provided path is not absolute, it is made relative to the
default output directory. The filename part is sanitized to replace
spaces and special characters with underscores, ensuring safe usage
in downstream processing.

**Parameters:**

- **file_path** (str): The file path to resolve.

**Returns:**

  Path: A fully resolved (absolute) and sanitized Path object.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._sanitize_filename"></a>

### _sanitize_filename

```python
def _sanitize_filename(self, filename: str):
```

Sanitize a filename by replacing any character that is not
alphanumeric, a dot (.), hyphen (-), or underscore (_) with an
underscore (_).

**Parameters:**

- **filename** (str): The original filename which may contain spaces or special characters.

**Returns:**

  str: The sanitized filename with disallowed characters replaced by
underscores.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._write_text_file"></a>

### _write_text_file

```python
def _write_text_file(
    self,
    file_path: Path,
    content: str,
    encoding: str = 'utf-8'
):
```

Write text content to a plaintext file.

**Parameters:**

- **file_path** (Path): The target file path.
- **content** (str): The text content to write.
- **encoding** (str): Character encoding to use. (default: :obj:`utf-8`) (default: utf-8)

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._generate_unique_filename"></a>

### _generate_unique_filename

```python
def _generate_unique_filename(self, file_path: Path):
```

Generate a unique filename if the target file already exists.

**Parameters:**

- **file_path** (Path): The original file path.

**Returns:**

  Path: A unique file path that doesn't exist yet.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._write_docx_file"></a>

### _write_docx_file

```python
def _write_docx_file(self, file_path: Path, content: str):
```

Write text content to a DOCX file with default formatting.

**Parameters:**

- **file_path** (Path): The target file path.
- **content** (str): The text content to write.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._write_pdf_file"></a>

### _write_pdf_file

```python
def _write_pdf_file(
    self,
    file_path: Path,
    title: str,
    content: Union[str, List[List[str]]],
    use_latex: bool = False
):
```

Write text content to a PDF file with LaTeX and table support.

**Parameters:**

- **file_path** (Path): The target file path.
- **title** (str): The document title.
- **content** (Union[str, List[List[str]]]): The content to write. Can
- **be**: - String: Supports Markdown-style tables and LaTeX math expressions - List[List[str]]: Table data as list of rows for direct table rendering
- **use_latex** (bool): Whether to use LaTeX for math rendering. (default: :obj:`False`)

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._process_text_content"></a>

### _process_text_content

```python
def _process_text_content(
    self,
    story,
    content: str,
    heading_style,
    body_style
):
```

Process text content and add to story.

**Parameters:**

- **story**: The reportlab story list to append to
- **content** (str): The text content to process
- **heading_style**: Style for headings
- **body_style**: Style for body text

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._find_table_line_ranges"></a>

### _find_table_line_ranges

```python
def _find_table_line_ranges(self, lines: List[str]):
```

Find line ranges that contain markdown tables.

**Parameters:**

- **lines** (List[str]): List of lines to analyze.

**Returns:**

  List[Tuple[int, int]]: List of (start_line, end_line) tuples
for table ranges.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._register_chinese_font"></a>

### _register_chinese_font

```python
def _register_chinese_font(self):
```

**Returns:**

  str: The font name to use for Chinese text.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._parse_markdown_table"></a>

### _parse_markdown_table

```python
def _parse_markdown_table(self, lines: List[str]):
```

Parse markdown-style tables from a list of lines.

**Parameters:**

- **lines** (List[str]): List of text lines that may contain tables.

**Returns:**

  List[List[List[str]]]: List of tables, where each table is a list
of rows, and each row is a list of cells.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._is_table_row"></a>

### _is_table_row

```python
def _is_table_row(self, line: str):
```

Check if a line appears to be a table row.

**Parameters:**

- **line** (str): The line to check.

**Returns:**

  bool: True if the line looks like a table row.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._is_table_separator"></a>

### _is_table_separator

```python
def _is_table_separator(self, line: str):
```

Check if a line is a table separator (e.g., |---|---|).

**Parameters:**

- **line** (str): The line to check.

**Returns:**

  bool: True if the line is a table separator.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._parse_table_row"></a>

### _parse_table_row

```python
def _parse_table_row(self, line: str):
```

Parse a single table row into cells.

**Parameters:**

- **line** (str): The table row line.

**Returns:**

  List[str]: List of cell contents.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._create_pdf_table"></a>

### _create_pdf_table

```python
def _create_pdf_table(self, table_data: List[List[str]]):
```

Create a formatted table for PDF.

**Parameters:**

- **table_data** (List[List[str]]): Table data as list of rows.

**Returns:**

  Table: A formatted reportlab Table object.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._convert_markdown_to_html"></a>

### _convert_markdown_to_html

```python
def _convert_markdown_to_html(self, text: str):
```

Convert basic markdown formatting to HTML for PDF rendering.

**Parameters:**

- **text** (str): Text with markdown formatting.

**Returns:**

  str: Text with HTML formatting.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._write_csv_file"></a>

### _write_csv_file

```python
def _write_csv_file(
    self,
    file_path: Path,
    content: Union[str, List[List]],
    encoding: str = 'utf-8'
):
```

Write CSV content to a file.

**Parameters:**

- **file_path** (Path): The target file path.
- **content** (Union[str, List[List]]): The CSV content as a string or list of lists.
- **encoding** (str): Character encoding to use. (default: :obj:`utf-8`) (default: utf-8)

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._write_json_file"></a>

### _write_json_file

```python
def _write_json_file(
    self,
    file_path: Path,
    content: str,
    encoding: str = 'utf-8'
):
```

Write JSON content to a file.

**Parameters:**

- **file_path** (Path): The target file path.
- **content** (str): The JSON content as a string.
- **encoding** (str): Character encoding to use. (default: :obj:`utf-8`) (default: utf-8)

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._write_simple_text_file"></a>

### _write_simple_text_file

```python
def _write_simple_text_file(
    self,
    file_path: Path,
    content: str,
    encoding: str = 'utf-8'
):
```

Write text content to a file (used for HTML, Markdown, YAML, etc.).

**Parameters:**

- **file_path** (Path): The target file path.
- **content** (str): The content to write.
- **encoding** (str): Character encoding to use. (default: :obj:`utf-8`) (default: utf-8)

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit.write_to_file"></a>

### write_to_file

```python
def write_to_file(
    self,
    title: str,
    content: Union[str, List[List[str]]],
    filename: str,
    encoding: Optional[str] = None,
    use_latex: bool = False
):
```

Write the given content to a file.

If the file exists, it will be overwritten. Supports multiple formats:
Markdown (.md, .markdown, default), Plaintext (.txt), CSV (.csv),
DOC/DOCX (.doc, .docx), PDF (.pdf), JSON (.json), YAML (.yml, .yaml),
and HTML (.html, .htm).

**Parameters:**

- **title** (str): The title of the document.
- **content** (Union[str, List[List[str]]]): The content to write to the file. Content format varies by file type: - Text formats (txt, md, html, yaml): string - CSV: string or list of lists - JSON: string or serializable object
- **filename** (str): The name or path of the file. If a relative path is supplied, it is resolved to self.working_directory.
- **encoding** (Optional[str]): The character encoding to use. (default: :obj: `None`)
- **use_latex** (bool): Whether to use LaTeX for math rendering. (default: :obj:`False`)

**Returns:**

  str: A message indicating success or error details.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects representing
the available functions in this toolkit.
