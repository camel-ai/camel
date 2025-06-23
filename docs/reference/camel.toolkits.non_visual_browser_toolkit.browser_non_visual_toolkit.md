<a id="camel.toolkits.non_visual_browser_toolkit.browser_non_visual_toolkit"></a>

<a id="camel.toolkits.non_visual_browser_toolkit.browser_non_visual_toolkit.BrowserNonVisualToolkit"></a>

## BrowserNonVisualToolkit

```python
class BrowserNonVisualToolkit(BaseToolkit):
```

A lightweight, *non-visual* browser toolkit exposing primitive
Playwright actions as CAMEL `FunctionTool`s.

<a id="camel.toolkits.non_visual_browser_toolkit.browser_non_visual_toolkit.BrowserNonVisualToolkit.__init__"></a>

### __init__

```python
def __init__(self):
```

<a id="camel.toolkits.non_visual_browser_toolkit.browser_non_visual_toolkit.BrowserNonVisualToolkit.__del__"></a>

### __del__

```python
def __del__(self):
```

Best-effort cleanup when toolkit is garbage collected.

1. We *avoid* running during the Python interpreter shutdown phase
(`sys.is_finalizing()`), because the import machinery and/or event
loop may already be torn down which leads to noisy exceptions such
as `ImportError: sys.meta_path is None` or
`RuntimeError: Event loop is closed`.
2. We protect all imports and event-loop operations with defensive
`try/except` blocks.  This ensures that, even if cleanup cannot be
carried out, we silently ignore the failure instead of polluting
stderr on program exit.

<a id="camel.toolkits.non_visual_browser_toolkit.browser_non_visual_toolkit.BrowserNonVisualToolkit._validate_ref"></a>

### _validate_ref

```python
def _validate_ref(self, ref: str, method_name: str):
```

Validate that ref parameter is a non-empty string.

<a id="camel.toolkits.non_visual_browser_toolkit.browser_non_visual_toolkit.BrowserNonVisualToolkit._ensure_agent"></a>

### _ensure_agent

```python
def _ensure_agent(self):
```

Create PlaywrightLLMAgent on first use if `web_agent_model`
provided.

<a id="camel.toolkits.non_visual_browser_toolkit.browser_non_visual_toolkit.BrowserNonVisualToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```
