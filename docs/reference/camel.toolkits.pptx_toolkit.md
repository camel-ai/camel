<a id="camel.toolkits.pptx_toolkit"></a>

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit"></a>

## PPTXToolkit

```python
class PPTXToolkit(BaseToolkit):
```

A toolkit for creating and writing PowerPoint presentations (PPTX
files).

This class provides cross-platform support for creating PPTX files with
title slides, content slides, text formatting, and image embedding.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    working_directory: Optional[str] = None,
    timeout: Optional[float] = None
):
```

Initialize the PPTXToolkit.

**Parameters:**

- **working_directory** (str, optional): The default directory for output files. If not provided, it will be determined by the `CAMEL_WORKDIR` environment variable (if set). If the environment variable is not set, it defaults to `camel_working_dir`.
- **timeout** (Optional[float]): The timeout for the toolkit. (default: :obj:`None`)

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._resolve_filepath"></a>

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

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._sanitize_filename"></a>

### _sanitize_filename

```python
def _sanitize_filename(self, filename: str):
```

Sanitize a filename by replacing special characters and spaces.

**Parameters:**

- **filename** (str): The filename to sanitize.

**Returns:**

  str: The sanitized filename.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._format_text"></a>

### _format_text

```python
def _format_text(
    self,
    frame_paragraph,
    text: str,
    set_color_to_white = False
):
```

Apply bold and italic formatting while preserving the original
word order.

**Parameters:**

- **frame_paragraph**: The paragraph to format.
- **text** (str): The text to format.
- **set_color_to_white** (bool): Whether to set the color to white. (default: :obj:`False`)

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._add_bulleted_items"></a>

### _add_bulleted_items

```python
def _add_bulleted_items(
    self,
    text_frame: 'TextFrame',
    flat_items_list: List[Tuple[str, int]],
    set_color_to_white: bool = False
):
```

Add a list of texts as bullet points and apply formatting.

**Parameters:**

- **text_frame** (TextFrame): The text frame where text is to be displayed.
- **flat_items_list** (List[Tuple[str, int]]): The list of items to be displayed.
- **set_color_to_white** (bool): Whether to set the font color to white. (default: :obj:`False`)

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._get_flat_list_of_contents"></a>

### _get_flat_list_of_contents

```python
def _get_flat_list_of_contents(self, items: List[Union[str, List[Any]]], level: int):
```

Flatten a hierarchical list of bullet points to a single list.

**Parameters:**

- **items** (List[Union[str, List[Any]]]): A bullet point (string or list).
- **level** (int): The current level of hierarchy.

**Returns:**

  List[Tuple[str, int]]: A list of (bullet item text, hierarchical
level) tuples.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._get_slide_width_height_inches"></a>

### _get_slide_width_height_inches

```python
def _get_slide_width_height_inches(self, presentation: 'presentation.Presentation'):
```

Get the dimensions of a slide in inches.

**Parameters:**

- **presentation** (presentation.Presentation): The presentation object.

**Returns:**

  Tuple[float, float]: The width and height in inches.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._write_pptx_file"></a>

### _write_pptx_file

```python
def _write_pptx_file(
    self,
    file_path: Path,
    content: List[Dict[str, Any]],
    template: Optional[str] = None
):
```

Write text content to a PPTX file with enhanced formatting.

**Parameters:**

- **file_path** (Path): The target file path.
- **content** (List[Dict[str, Any]]): The content to write to the PPTX file. Must be a list of dictionaries where: - First element: Title slide with keys 'title' and 'subtitle' - Subsequent elements: Content slides with keys 'title', 'text'
- **template** (Optional[str]): The name of the template to use. If not provided, the default template will be used. (default: :obj: `None`)

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit.create_presentation"></a>

### create_presentation

```python
def create_presentation(
    self,
    content: str,
    filename: str,
    template: Optional[str] = None
):
```

Create a PowerPoint presentation (PPTX) file.

**Parameters:**

- **content** (str): The content to write to the PPTX file as a JSON string. Must represent a list of dictionaries with the following structure: - First dict: title slide `{"title": str, "subtitle": str}` - Other dicts: content slides, which can be one of: * Bullet/step slides: `{"heading": str, "bullet_points": list of str or nested lists, "img_keywords": str (optional)}` - If any bullet point starts with '&gt;> ', it will be rendered as a step-by-step process. - "img_keywords" can be a URL or search keywords for an image (optional). * Table slides: `{"heading": str, "table": {"headers": list of str, "rows": list of list of str}}`
- **filename** (str): The name or path of the file. If a relative path is supplied, it is resolved to self.working_directory.
- **template** (Optional[str]): The path to the template PPTX file. Initializes a presentation from a given template file Or PPTX file. (default: :obj:`None`)

**Returns:**

  str: A success message indicating the file was created.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._handle_default_display"></a>

### _handle_default_display

```python
def _handle_default_display(
    self,
    presentation: 'presentation.Presentation',
    slide_json: Dict[str, Any]
):
```

Display a list of text in a slide.

**Parameters:**

- **presentation** (presentation.Presentation): The presentation object.
- **slide_json** (Dict[str, Any]): The content of the slide as JSON data.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._handle_display_image__in_foreground"></a>

### _handle_display_image__in_foreground

```python
def _handle_display_image__in_foreground(
    self,
    presentation: 'presentation.Presentation',
    slide_json: Dict[str, Any]
):
```

Create a slide with text and image using a picture placeholder
layout.

**Parameters:**

- **presentation** (presentation.Presentation): The presentation object.
- **slide_json** (Dict[str, Any]): The content of the slide as JSON data.

**Returns:**

  bool: True if the slide has been processed.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._handle_table"></a>

### _handle_table

```python
def _handle_table(
    self,
    presentation: 'presentation.Presentation',
    slide_json: Dict[str, Any]
):
```

Add a table to a slide.

**Parameters:**

- **presentation** (presentation.Presentation): The presentation object.
- **slide_json** (Dict[str, Any]): The content of the slide as JSON data.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._handle_step_by_step_process"></a>

### _handle_step_by_step_process

```python
def _handle_step_by_step_process(
    self,
    presentation: 'presentation.Presentation',
    slide_json: Dict[str, Any],
    slide_width_inch: float,
    slide_height_inch: float
):
```

Add shapes to display a step-by-step process in the slide.

**Parameters:**

- **presentation** (presentation.Presentation): The presentation object.
- **slide_json** (Dict[str, Any]): The content of the slide as JSON data.
- **slide_width_inch** (float): The width of the slide in inches.
- **slide_height_inch** (float): The height of the slide in inches.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._remove_slide_number_from_heading"></a>

### _remove_slide_number_from_heading

```python
def _remove_slide_number_from_heading(self, header: str):
```

Remove the slide number from a given slide header.

**Parameters:**

- **header** (str): The header of a slide.

**Returns:**

  str: The header without slide number.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit._get_slide_placeholders"></a>

### _get_slide_placeholders

```python
def _get_slide_placeholders(self, slide: 'Slide'):
```

Return the index and name of all placeholders present in a slide.

**Parameters:**

- **slide** (Slide): The slide.

**Returns:**

  List[Tuple[int, str]]: A list containing placeholders (idx, name)
tuples.

<a id="camel.toolkits.pptx_toolkit.PPTXToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects
representing the functions in the toolkit.
