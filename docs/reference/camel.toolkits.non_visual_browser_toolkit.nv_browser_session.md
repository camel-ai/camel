<a id="camel.toolkits.non_visual_browser_toolkit.nv_browser_session"></a>

<a id="camel.toolkits.non_visual_browser_toolkit.nv_browser_session.HybridBrowserSession"></a>

## HybridBrowserSession

```python
class HybridBrowserSession:
```

Lightweight wrapper around Playwright for non-visual (headless)
browsing.

It provides a single *Page* instance plus helper utilities (snapshot &
executor).  Multiple toolkits or agents can reuse this class without
duplicating Playwright setup code.

This class is a singleton per event-loop.

<a id="camel.toolkits.non_visual_browser_toolkit.nv_browser_session.HybridBrowserSession.__new__"></a>

### __new__

```python
def __new__(cls):
```

<a id="camel.toolkits.non_visual_browser_toolkit.nv_browser_session.HybridBrowserSession.__init__"></a>

### __init__

```python
def __init__(self):
```
