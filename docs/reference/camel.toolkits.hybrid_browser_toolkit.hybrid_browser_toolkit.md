<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit"></a>

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit"></a>

## HybridBrowserToolkit

```python
class HybridBrowserToolkit(BaseToolkit):
```

A hybrid browser toolkit that combines non-visual, DOM-based browser
automation with visual, screenshot-based capabilities.

This toolkit exposes a set of actions as CAMEL FunctionTools for agents
to interact with web pages. It can operate in headless mode and supports
both programmatic control of browser actions (like clicking and typing)
and visual analysis of the page layout through screenshots with marked
interactive elements.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.__init__"></a>

### __init__

```python
def __init__(self):
```

Initialize the HybridBrowserToolkit.

**Parameters:**

- **headless** (bool): Whether to run the browser in headless mode. Defaults to `True`.
- **user_data_dir** (Optional[str]): Path to a directory for storing browser data like cookies and local storage. Useful for maintaining sessions across runs. Defaults to `None` (a temporary directory is used).
- **web_agent_model** (Optional[BaseModelBackend]): The language model backend to use for the high-level `solve_task` agent. This is required only if you plan to use `solve_task`. Defaults to `None`.
- **cache_dir** (str): The directory to store cached files, such as screenshots. Defaults to `"tmp/"`.
- **enabled_tools** (Optional[List[str]]): List of tool names to enable. If None, uses DEFAULT_TOOLS. Available tools: open_browser, close_browser, visit_page, get_page_snapshot, get_som_screenshot, get_page_links, click, type, select, scroll, enter, wait_user, solve_task. Defaults to `None`.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.__del__"></a>

### __del__

```python
def __del__(self):
```

Cleanup browser resources on garbage collection.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit._load_unified_analyzer"></a>

### _load_unified_analyzer

```python
def _load_unified_analyzer(self):
```

Load the unified analyzer JavaScript script.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit._validate_ref"></a>

### _validate_ref

```python
def _validate_ref(self, ref: str, method_name: str):
```

Validate ref parameter.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit._convert_analysis_to_rects"></a>

### _convert_analysis_to_rects

```python
def _convert_analysis_to_rects(self, analysis_data: Dict[str, Any]):
```

Convert analysis data to rect format for visual marking.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit._add_set_of_mark"></a>

### _add_set_of_mark

```python
def _add_set_of_mark(self, image, rects):
```

Add visual marks to the image.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit._format_snapshot_from_analysis"></a>

### _format_snapshot_from_analysis

```python
def _format_snapshot_from_analysis(self, analysis_data: Dict[str, Any]):
```

Format analysis data into snapshot string.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit._ensure_agent"></a>

### _ensure_agent

```python
def _ensure_agent(self):
```

Create PlaywrightLLMAgent on first use.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

Get available function tools
based on enabled_tools configuration.
