<a id="camel.toolkits.google_drive_mcp_toolkit"></a>

<a id="camel.toolkits.google_drive_mcp_toolkit.GoogleDriveMCPToolkit"></a>

## GoogleDriveMCPToolkit

```python
class GoogleDriveMCPToolkit(BaseToolkit):
```

GoogleDriveMCPToolkit provides an interface for interacting with
Google Drive using the Google Drive MCP server.

**Parameters:**

- **timeout** (Optional[float]): Connection timeout in seconds. (default: :obj:`None`)

<a id="camel.toolkits.google_drive_mcp_toolkit.GoogleDriveMCPToolkit.__init__"></a>

### __init__

```python
def __init__(
    self,
    timeout: Optional[float] = None,
    credentials_path: Optional[str] = None
):
```

Initializes the GoogleDriveMCPToolkit.

**Parameters:**

- **timeout** (Optional[float]): Connection timeout in seconds. (default: :obj:`None`)
- **credentials_path** (Optional[str]): Path to the Google Drive credentials file. (default: :obj:`None`)

<a id="camel.toolkits.google_drive_mcp_toolkit.GoogleDriveMCPToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: List of available tools.
