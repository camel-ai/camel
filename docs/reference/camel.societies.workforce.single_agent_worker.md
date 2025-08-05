<a id="camel.societies.workforce.single_agent_worker"></a>

<a id="camel.societies.workforce.single_agent_worker.AgentPool"></a>

## AgentPool

```python
class AgentPool:
```

A pool of agent instances for efficient reuse.

This pool manages a collection of pre-cloned agents. It supports
auto-scaling based ondemand and intelligent reuse of existing agents.

**Parameters:**

- **base_agent** (ChatAgent): The base agent to clone from.
- **initial_size** (int): Initial number of agents in the pool. (default: :obj:`1`)
- **max_size** (int): Maximum number of agents in the pool. (default: :obj:`10`)
- **auto_scale** (bool): Whether to automatically scale the pool size. (default: :obj:`True`)
- **idle_timeout** (float): Time in seconds after which idle agents are removed. (default: :obj:`180.0`)

<a id="camel.societies.workforce.single_agent_worker.AgentPool.__init__"></a>

### __init__

```python
def __init__(
    self,
    base_agent: ChatAgent,
    initial_size: int = 1,
    max_size: int = 10,
    auto_scale: bool = True,
    idle_timeout: float = 180.0
):
```

<a id="camel.societies.workforce.single_agent_worker.AgentPool._initialize_pool"></a>

### _initialize_pool

```python
def _initialize_pool(self, size: int):
```

Initialize the pool with the specified number of agents.

<a id="camel.societies.workforce.single_agent_worker.AgentPool._create_fresh_agent"></a>

### _create_fresh_agent

```python
def _create_fresh_agent(self):
```

Create a fresh agent instance.

<a id="camel.societies.workforce.single_agent_worker.AgentPool.get_stats"></a>

### get_stats

```python
def get_stats(self):
```

Get pool statistics.

<a id="camel.societies.workforce.single_agent_worker.SingleAgentWorker"></a>

## SingleAgentWorker

```python
class SingleAgentWorker(Worker):
```

A worker node that consists of a single agent.

**Parameters:**

- **description** (str): Description of the node.
- **worker** (ChatAgent): Worker of the node. A single agent.
- **use_agent_pool** (bool): Whether to use agent pool for efficiency. (default: :obj:`True`)
- **pool_initial_size** (int): Initial size of the agent pool. (default: :obj:`1`)
- **pool_max_size** (int): Maximum size of the agent pool. (default: :obj:`10`)
- **auto_scale_pool** (bool): Whether to auto-scale the agent pool. (default: :obj:`True`)
- **use_structured_output_handler** (bool, optional): Whether to use the structured output handler instead of native structured output. When enabled, the workforce will use prompts with structured output instructions and regex extraction to parse responses. This ensures compatibility with agents that don't reliably support native structured output. When disabled, the workforce uses the native response_format parameter. (default: :obj:`True`)

<a id="camel.societies.workforce.single_agent_worker.SingleAgentWorker.__init__"></a>

### __init__

```python
def __init__(
    self,
    description: str,
    worker: ChatAgent,
    use_agent_pool: bool = True,
    pool_initial_size: int = 1,
    pool_max_size: int = 10,
    auto_scale_pool: bool = True,
    use_structured_output_handler: bool = True
):
```

<a id="camel.societies.workforce.single_agent_worker.SingleAgentWorker.reset"></a>

### reset

```python
def reset(self):
```

Resets the worker to its initial state.

<a id="camel.societies.workforce.single_agent_worker.SingleAgentWorker.get_pool_stats"></a>

### get_pool_stats

```python
def get_pool_stats(self):
```

Get agent pool statistics if pool is enabled.
