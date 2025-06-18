<a id="camel.societies.workforce.single_agent_worker"></a>

<a id="camel.societies.workforce.single_agent_worker.SingleAgentWorker"></a>

## SingleAgentWorker

```python
class SingleAgentWorker(Worker):
```

A worker node that consists of a single agent.

**Parameters:**

- **description** (str): Description of the node.
- **worker** (ChatAgent): Worker of the node. A single agent.
- **max_concurrent_tasks** (int): Maximum number of tasks this worker can process concurrently. (default: :obj:`10`)

<a id="camel.societies.workforce.single_agent_worker.SingleAgentWorker.__init__"></a>

### __init__

```python
def __init__(
    self,
    description: str,
    worker: ChatAgent,
    max_concurrent_tasks: int = 10
):
```

<a id="camel.societies.workforce.single_agent_worker.SingleAgentWorker.reset"></a>

### reset

```python
def reset(self):
```

Resets the worker to its initial state.
