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
- **stealth** (bool): Whether to run the browser in stealth mode to avoid bot detection. When enabled, hides WebDriver characteristics, spoofs navigator properties, and implements various anti-detection measures. Highly recommended for production use and when accessing sites with bot detection. Defaults to `False`.
- **web_agent_model** (Optional[BaseModelBackend]): The language model backend to use for the high-level `solve_task` agent. This is required only if you plan to use `solve_task`. Defaults to `None`.
- **cache_dir** (str): The directory to store cached files, such as screenshots. Defaults to `"tmp/"`.
- **enabled_tools** (Optional[List[str]]): List of tool names to enable. If None, uses DEFAULT_TOOLS. Available tools: open_browser, close_browser, visit_page, back, forward, get_page_snapshot, get_som_screenshot, get_page_links, click, type, select, scroll, enter, wait_user, solve_task. Defaults to `None`.
- **browser_log_to_file** (bool): Whether to save detailed browser action logs to file. When enabled, logs action inputs/outputs, execution times, and page loading times. Logs are saved to an auto-generated timestamped file. Defaults to `False`.
- **session_id** (Optional[str]): A unique identifier for this browser session. When multiple HybridBrowserToolkit instances are used concurrently, different session IDs prevent them from sharing the same browser session and causing conflicts. If None, a default session will be used. Defaults to `None`.
- **default_start_url** (str): The default URL to navigate to when open_browser() is called without a start_url parameter or with None. Defaults to `"https://google.com/"`.
- **default_timeout** (Optional[int]): Default timeout in milliseconds for browser actions. If None, uses environment variable HYBRID_BROWSER_DEFAULT_TIMEOUT or defaults to 3000ms. Defaults to `None`.
- **short_timeout** (Optional[int]): Short timeout in milliseconds for quick browser actions. If None, uses environment variable HYBRID_BROWSER_SHORT_TIMEOUT or defaults to 1000ms. Defaults to `None`.
- **navigation_timeout** (Optional[int]): Custom navigation timeout in milliseconds. If None, uses environment variable HYBRID_BROWSER_NAVIGATION_TIMEOUT or defaults to 10000ms. Defaults to `None`.
- **network_idle_timeout** (Optional[int]): Custom network idle timeout in milliseconds. If None, uses environment variable HYBRID_BROWSER_NETWORK_IDLE_TIMEOUT or defaults to 5000ms. Defaults to `None`.
- **screenshot_timeout** (Optional[int]): Custom screenshot timeout in milliseconds. If None, uses environment variable HYBRID_BROWSER_SCREENSHOT_TIMEOUT or defaults to 15000ms. Defaults to `None`.
- **page_stability_timeout** (Optional[int]): Custom page stability timeout in milliseconds. If None, uses environment variable HYBRID_BROWSER_PAGE_STABILITY_TIMEOUT or defaults to 1500ms. Defaults to `None`.
- **dom_content_loaded_timeout** (Optional[int]): Custom DOM content loaded timeout in milliseconds. If None, uses environment variable HYBRID_BROWSER_DOM_CONTENT_LOADED_TIMEOUT or defaults to 5000ms. Defaults to `None`.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.web_agent_model"></a>

### web_agent_model

```python
def web_agent_model(self):
```

Get the web agent model.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.web_agent_model"></a>

### web_agent_model

```python
def web_agent_model(self, value: Optional[BaseModelBackend]):
```

Set the web agent model.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.cache_dir"></a>

### cache_dir

```python
def cache_dir(self):
```

Get the cache directory.

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

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit._truncate_if_needed"></a>

### _truncate_if_needed

```python
def _truncate_if_needed(self, content: Any):
```

Truncate content if max_log_length is set.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.action_logger"></a>

### action_logger

```python
def action_logger(func: Callable[..., Any]):
```

Decorator to add logging to action methods.

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

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.get_log_summary"></a>

### get_log_summary

```python
def get_log_summary(self):
```

Get a summary of logged actions.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.clear_logs"></a>

### clear_logs

```python
def clear_logs(self):
```

Clear the log buffer.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```

Get available function tools
based on enabled_tools configuration.

<a id="camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit.HybridBrowserToolkit.clone_for_new_session"></a>

### clone_for_new_session

```python
def clone_for_new_session(self, new_session_id: Optional[str] = None):
```

Create a new instance of HybridBrowserToolkit with a unique
session.

**Parameters:**

- **new_session_id**: Optional new session ID. If None, a UUID will be generated.

**Returns:**

  A new HybridBrowserToolkit instance with the same configuration
but a different session.
