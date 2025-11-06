<a id="camel.societies.workforce.worker"></a>

<a id="camel.societies.workforce.worker.Worker"></a>

## Worker

```python
class Worker(BaseNode, ABC):
```

A worker node that works on tasks. It is the basic unit of task
processing in the workforce system.

**Parameters:**

- **description** (str): Description of the node.
- **node_id** (Optional[str]): ID of the node. If not provided, it will be generated automatically. (default: :obj:`None`)

<a id="camel.societies.workforce.worker.Worker.__init__"></a>

### __init__

```python
def __init__(self, description: str, node_id: Optional[str] = None):
```

<a id="camel.societies.workforce.worker.Worker.__repr__"></a>

### __repr__

```python
def __repr__(self):
```

<a id="camel.societies.workforce.worker.Worker._get_dep_tasks_info"></a>

### _get_dep_tasks_info

```python
def _get_dep_tasks_info(dependencies: List[Task]):
```

<a id="camel.societies.workforce.worker.Worker.set_channel"></a>

### set_channel

```python
def set_channel(self, channel: TaskChannel):
```

<a id="camel.societies.workforce.worker.Worker.stop"></a>

### stop

```python
def stop(self):
```

Stop the worker.
