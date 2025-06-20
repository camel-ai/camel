<a id="camel.toolkits.file_write_toolkit"></a>

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit"></a>

## FileWriteToolkit

```python
class FileWriteToolkit(BaseToolkit):
```

A toolkit for creating, writing, and modifying text in files.

This class provides cross-platform (macOS, Linux, Windows) support for
writing to various file formats (Markdown, DOCX, PDF, and plaintext),
replacing text in existing files, automatic backups, custom encoding,
and enhanced formatting options for specialized formats.

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    output_dir: str = './',
    timeout: Optional[float] = None,
    default_encoding: str = 'utf-8',
    backup_enabled: bool = True
):
```

Initialize the FileWriteToolkit.

**Parameters:**

- **output_dir** (str): The default directory for output files. Defaults to the current working directory.
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

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._create_backup"></a>

### _create_backup

```python
def _create_backup(self, file_path: Path):
```

Create a backup of the file if it exists and backup is enabled.

**Parameters:**

- **file_path** (Path): Path to the file to backup.

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
    content: str,
    use_latex: bool = False
):
```

Write text content to a PDF file with default formatting.

**Parameters:**

- **file_path** (Path): The target file path.
- **content** (str): The text content to write.
- **use_latex** (bool): Whether to use LaTeX for rendering. (requires LaTeX toolchain). If False, uses FPDF for simpler PDF generation. (default: :obj:`False`)

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

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._write_yaml_file"></a>

### _write_yaml_file

```python
def _write_yaml_file(
    self,
    file_path: Path,
    content: str,
    encoding: str = 'utf-8'
):
```

Write YAML content to a file.

**Parameters:**

- **file_path** (Path): The target file path.
- **content** (str): The YAML content as a string.
- **encoding** (str): Character encoding to use. (default: :obj:`utf-8`) (default: utf-8)

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._write_html_file"></a>

### _write_html_file

```python
def _write_html_file(
    self,
    file_path: Path,
    content: str,
    encoding: str = 'utf-8'
):
```

Write text content to an HTML file.

**Parameters:**

- **file_path** (Path): The target file path.
- **content** (str): The HTML content to write.
- **encoding** (str): Character encoding to use. (default: :obj:`utf-8`) (default: utf-8)

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit._write_markdown_file"></a>

### _write_markdown_file

```python
def _write_markdown_file(
    self,
    file_path: Path,
    content: str,
    encoding: str = 'utf-8'
):
```

Write text content to a Markdown file.

**Parameters:**

- **file_path** (Path): The target file path.
- **content** (str): The Markdown content to write.
- **encoding** (str): Character encoding to use. (default: :obj:`utf-8`) (default: utf-8)

<a id="camel.toolkits.file_write_toolkit.FileWriteToolkit.write_to_file"></a>

### write_to_file

```python
def write_to_file(
    self,
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

- **content** (Union[str, List[List[str]]]): The content to write to the file. Content format varies by file type: - Text formats (txt, md, html, yaml): string - CSV: string or list of lists - JSON: string or serializable object
- **filename** (str): The name or path of the file. If a relative path is supplied, it is resolved to self.output_dir.
- **encoding** (Optional[str]): The character encoding to use. (default: :obj: `None`)
- **use_latex** (bool): For PDF files, whether to use LaTeX rendering (True) or simple FPDF rendering (False). (default: :obj: `False`)

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
