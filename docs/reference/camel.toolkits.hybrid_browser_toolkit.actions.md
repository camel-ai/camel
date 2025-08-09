<a id="camel.toolkits.hybrid_browser_toolkit.actions"></a>

<a id="camel.toolkits.hybrid_browser_toolkit.actions.ActionExecutor"></a>

## ActionExecutor

```python
class ActionExecutor:
```

Executes high-level actions (click, type …) on a Playwright Page.

<a id="camel.toolkits.hybrid_browser_toolkit.actions.ActionExecutor.__init__"></a>

### __init__

```python
def __init__(
    self,
    page: 'Page',
    session: Optional[Any] = None,
    default_timeout: Optional[int] = None,
    short_timeout: Optional[int] = None,
    max_scroll_amount: Optional[int] = None
):
```

<a id="camel.toolkits.hybrid_browser_toolkit.actions.ActionExecutor.should_update_snapshot"></a>

### should_update_snapshot

```python
def should_update_snapshot(action: Dict[str, Any]):
```

Determine if an action requires a snapshot update.
