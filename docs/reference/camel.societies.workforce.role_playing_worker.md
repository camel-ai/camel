<a id="camel.societies.workforce.role_playing_worker"></a>

<a id="camel.societies.workforce.role_playing_worker.RolePlayingWorker"></a>

## RolePlayingWorker

```python
class RolePlayingWorker(Worker):
```

A worker node that contains a role playing.

**Parameters:**

- **description** (str): Description of the node.
- **assistant_role_name** (str): The role name of the assistant agent.
- **user_role_name** (str): The role name of the user agent.
- **assistant_agent_kwargs** (Optional[Dict]): The keyword arguments to initialize the assistant agent in the role playing, like the model name, etc. (default: :obj:`None`)
- **user_agent_kwargs** (Optional[Dict]): The keyword arguments to initialize the user agent in the role playing, like the model name, etc. (default: :obj:`None`)
- **summarize_agent_kwargs** (Optional[Dict]): The keyword arguments to initialize the summarize agent, like the model name, etc. (default: :obj:`None`)
- **chat_turn_limit** (int): The maximum number of chat turns in the role playing. (default: :obj:`20`)
- **use_structured_output_handler** (bool, optional): Whether to use the structured output handler instead of native structured output. When enabled, the workforce will use prompts with structured output instructions and regex extraction to parse responses. This ensures compatibility with agents that don't reliably support native structured output. When disabled, the workforce uses the native response_format parameter. (default: :obj:`True`)

<a id="camel.societies.workforce.role_playing_worker.RolePlayingWorker.__init__"></a>

### __init__

```python
def __init__(
    self,
    description: str,
    assistant_role_name: str,
    user_role_name: str,
    assistant_agent_kwargs: Optional[Dict] = None,
    user_agent_kwargs: Optional[Dict] = None,
    summarize_agent_kwargs: Optional[Dict] = None,
    chat_turn_limit: int = 20,
    use_structured_output_handler: bool = True
):
```
