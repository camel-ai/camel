<a id="camel.toolkits.hybrid_browser_toolkit.browser_session"></a>

<a id="camel.toolkits.hybrid_browser_toolkit.browser_session.HybridBrowserSession"></a>

## HybridBrowserSession

```python
class HybridBrowserSession:
```

Lightweight wrapper around Playwright for
browsing with multi-tab support.

It provides multiple *Page* instances plus helper utilities (snapshot &
executor).  Multiple toolkits or agents can reuse this class without
duplicating Playwright setup code.

This class is a singleton per event-loop and session-id combination.

<a id="camel.toolkits.hybrid_browser_toolkit.browser_session.HybridBrowserSession.__new__"></a>

### __new__

```python
def __new__(cls):
```

<a id="camel.toolkits.hybrid_browser_toolkit.browser_session.HybridBrowserSession.__init__"></a>

### __init__

```python
def __init__(self):
```

<a id="camel.toolkits.hybrid_browser_toolkit.browser_session.HybridBrowserSession._load_stealth_script"></a>

### _load_stealth_script

```python
def _load_stealth_script(self):
```

Load the stealth JavaScript script from file.
