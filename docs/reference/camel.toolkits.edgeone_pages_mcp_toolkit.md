<a id="camel.toolkits.edgeone_pages_mcp_toolkit"></a>

<a id="camel.toolkits.edgeone_pages_mcp_toolkit.EdgeOnePagesMCPToolkit"></a>

## EdgeOnePagesMCPToolkit

```python
class EdgeOnePagesMCPToolkit(BaseToolkit):
```

EdgeOnePagesMCPToolkit provides an interface for interacting with
EdgeOne pages using the EdgeOne Pages MCP server.

**Parameters:**

- **timeout** (Optional[float]): Connection timeout in seconds. (default: :obj:`None`)

<a id="camel.toolkits.edgeone_pages_mcp_toolkit.EdgeOnePagesMCPToolkit.__init__"></a>

### __init__

```python
def __init__(self, timeout: Optional[float] = None):
```

Initializes the EdgeOnePagesMCPToolkit.

**Parameters:**

- **timeout** (Optional[float]): Connection timeout in seconds. (default: :obj:`None`)

<a id="camel.toolkits.edgeone_pages_mcp_toolkit.EdgeOnePagesMCPToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

**Returns:**

  List[FunctionTool]: List of available tools.
