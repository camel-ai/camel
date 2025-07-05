<a id="camel.toolkits.hybrid_browser_toolkit.agent"></a>

<a id="camel.toolkits.hybrid_browser_toolkit.agent.PlaywrightLLMAgent"></a>

## PlaywrightLLMAgent

```python
class PlaywrightLLMAgent:
```

High-level orchestration: snapshot ↔ LLM ↔ action executor.

<a id="camel.toolkits.hybrid_browser_toolkit.agent.PlaywrightLLMAgent.__init__"></a>

### __init__

```python
def __init__(self):
```

<a id="camel.toolkits.hybrid_browser_toolkit.agent.PlaywrightLLMAgent._get_chat_agent"></a>

### _get_chat_agent

```python
def _get_chat_agent(self):
```

Get or create the ChatAgent instance.

<a id="camel.toolkits.hybrid_browser_toolkit.agent.PlaywrightLLMAgent._safe_parse_json"></a>

### _safe_parse_json

```python
def _safe_parse_json(self, content: str):
```

Safely parse JSON from LLM response with multiple fallback
strategies.

<a id="camel.toolkits.hybrid_browser_toolkit.agent.PlaywrightLLMAgent._get_fallback_response"></a>

### _get_fallback_response

```python
def _get_fallback_response(self, error_msg: str):
```

Generate a fallback response structure.

<a id="camel.toolkits.hybrid_browser_toolkit.agent.PlaywrightLLMAgent._llm_call"></a>

### _llm_call

```python
def _llm_call(
    self,
    prompt: str,
    snapshot: str,
    is_initial: bool,
    history: Optional[List[Dict[str, Any]]] = None
):
```

Call the LLM (via CAMEL ChatAgent) to get plan & next action.
