<a id="camel.toolkits.note_taking_toolkit"></a>

<a id="camel.toolkits.note_taking_toolkit.NoteTakingToolkit"></a>

## NoteTakingToolkit

```python
class NoteTakingToolkit(BaseToolkit):
```

A toolkit for taking notes in a Markdown file.

This toolkit allows an agent to create, append to, and update a specific
Markdown file for note-taking purposes.

<a id="camel.toolkits.note_taking_toolkit.NoteTakingToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    working_directory: Optional[str] = None,
    timeout: Optional[float] = None
):
```

Initialize the NoteTakingToolkit.

**Parameters:**

- **working_directory** (str, optional): The path to the note file. If not provided, it will be determined by the `CAMEL_WORKDIR` environment variable (if set), saving the note as `notes.md` in that directory. If the environment variable is not set, it defaults to `camel_working_dir/notes.md`.
- **timeout** (Optional[float]): The timeout for the toolkit.

<a id="camel.toolkits.note_taking_toolkit.NoteTakingToolkit.append_note"></a>

### append_note

```python
def append_note(self, content: str):
```

Appends a note to the note file.

**Parameters:**

- **content** (str): The content of the note to be appended.

**Returns:**

  str: A message indicating the result of the operation.

<a id="camel.toolkits.note_taking_toolkit.NoteTakingToolkit.read_note"></a>

### read_note

```python
def read_note(self):
```

**Returns:**

  str: The content of the note file, or an error message if the
file cannot be read.

<a id="camel.toolkits.note_taking_toolkit.NoteTakingToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: A list of FunctionTool objects.
