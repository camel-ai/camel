<a id="camel.societies.workforce.workforce"></a>

<a id="camel.societies.workforce.workforce.WorkforceState"></a>

## WorkforceState

```python
class WorkforceState(Enum):
```

Workforce execution state for human intervention support.

<a id="camel.societies.workforce.workforce.WorkforceSnapshot"></a>

## WorkforceSnapshot

```python
class WorkforceSnapshot:
```

Snapshot of workforce state for resuming execution.

<a id="camel.societies.workforce.workforce.WorkforceSnapshot.__init__"></a>

### __init__

```python
def __init__(
    self,
    main_task: Optional[Task] = None,
    pending_tasks: Optional[Deque[Task]] = None,
    completed_tasks: Optional[List[Task]] = None,
    task_dependencies: Optional[Dict[str, List[str]]] = None,
    assignees: Optional[Dict[str, str]] = None,
    current_task_index: int = 0,
    description: str = ''
):
```

<a id="camel.societies.workforce.workforce.Workforce"></a>

## Workforce

```python
class Workforce(BaseNode):
```

A system where multiple worker nodes (agents) cooperate together
to solve tasks. It can assign tasks to worker nodes and also take
strategies such as create new worker, decompose tasks, etc. to handle
situations when the task fails.

The workforce uses three specialized ChatAgents internally:
- Coordinator Agent: Assigns tasks to workers based on their
capabilities
- Task Planner Agent: Decomposes complex tasks and composes results
- Dynamic Workers: Created at runtime when tasks fail repeatedly

**Parameters:**

- **description** (str): Description of the workforce.
- **children** (Optional[List[BaseNode]], optional): List of child nodes under this node. Each child node can be a worker node or another workforce node. (default: :obj:`None`)
- **coordinator_agent** (Optional[ChatAgent], optional): A custom coordinator agent instance for task assignment and worker creation. If provided, the workforce will create a new agent using this agent's model configuration but with the required system message and functionality. If None, a default agent will be created using DEFAULT model settings. (default: :obj:`None`)
- **task_agent** (Optional[ChatAgent], optional): A custom task planning agent instance for task decomposition and composition. If provided, the workforce will create a new agent using this agent's model configuration but with the required system message and tools (TaskPlanningToolkit). If None, a default agent will be created using DEFAULT model settings. (default: :obj:`None`)
- **new_worker_agent** (Optional[ChatAgent], optional): A template agent for workers created dynamically at runtime when existing workers cannot handle failed tasks. If None, workers will be created with default settings including SearchToolkit, CodeExecutionToolkit, and ThinkingToolkit. (default: :obj:`None`)
- **graceful_shutdown_timeout** (float, optional): The timeout in seconds for graceful shutdown when a task fails 3 times. During this period, the workforce remains active for debugging. Set to 0 for immediate shutdown. (default: :obj:`15.0`)
- **share_memory** (bool, optional): Whether to enable shared memory across SingleAgentWorker instances in the workforce. When enabled, all SingleAgentWorker instances, coordinator agent, and task planning agent will share their complete conversation history and function-calling trajectory, providing better context for task handoffs and continuity. Note: Currently only supports SingleAgentWorker instances; RolePlayingWorker and nested Workforce instances do not participate in memory sharing. (default: :obj:`False`)
- **use_structured_output_handler** (bool, optional): Whether to use the structured output handler instead of native structured output. When enabled, the workforce will use prompts with structured output instructions and regex extraction to parse responses. This ensures compatibility with agents that don't reliably support native structured output. When disabled, the workforce uses the native response_format parameter. (default: :obj:`True`)

**Note:**

When custom coordinator_agent or task_agent are provided, the workforce
will preserve the user's system message and append the required
workforce coordination or task planning instructions to it. This
ensures both the user's intent is preserved and proper workforce
functionality is maintained. All other agent configurations (model,
memory, tools, etc.) will also be preserved.

<a id="camel.societies.workforce.workforce.Workforce.__init__"></a>

### __init__

```python
def __init__(
    self,
    description: str,
    children: Optional[List[BaseNode]] = None,
    coordinator_agent: Optional[ChatAgent] = None,
    task_agent: Optional[ChatAgent] = None,
    new_worker_agent: Optional[ChatAgent] = None,
    graceful_shutdown_timeout: float = 15.0,
    share_memory: bool = False,
    use_structured_output_handler: bool = True
):
```

<a id="camel.societies.workforce.workforce.Workforce._validate_agent_compatibility"></a>

### _validate_agent_compatibility

```python
def _validate_agent_compatibility(self, agent: ChatAgent, agent_context: str = 'agent'):
```

Validate that agent configuration is compatible with workforce
settings.

**Parameters:**

- **agent** (ChatAgent): The agent to validate.
- **agent_context** (str): Context description for error messages.

<a id="camel.societies.workforce.workforce.Workforce._attach_pause_event_to_agent"></a>

### _attach_pause_event_to_agent

```python
def _attach_pause_event_to_agent(self, agent: ChatAgent):
```

Ensure the given ChatAgent shares this workforce's pause_event.

If the agent already has a different pause_event we overwrite it and
emit a debug log (it is unlikely an agent needs multiple independent
pause controls once managed by this workforce).

<a id="camel.societies.workforce.workforce.Workforce._ensure_pause_event_in_kwargs"></a>

### _ensure_pause_event_in_kwargs

```python
def _ensure_pause_event_in_kwargs(self, kwargs: Optional[Dict]):
```

Insert pause_event into kwargs dict for ChatAgent construction.

<a id="camel.societies.workforce.workforce.Workforce.__repr__"></a>

### __repr__

```python
def __repr__(self):
```

<a id="camel.societies.workforce.workforce.Workforce._collect_shared_memory"></a>

### _collect_shared_memory

```python
def _collect_shared_memory(self):
```

**Returns:**

  Dict[str, List]: A dictionary mapping agent types to their memory
records. Contains entries for 'coordinator', 'task_agent',
and 'workers'.

<a id="camel.societies.workforce.workforce.Workforce._share_memory_with_agents"></a>

### _share_memory_with_agents

```python
def _share_memory_with_agents(self, shared_memory: Dict[str, List]):
```

Share collected memory with coordinator, task agent, and
SingleAgentWorker instances.

**Parameters:**

- **shared_memory** (Dict[str, List]): Memory records collected from all agents to be shared.

<a id="camel.societies.workforce.workforce.Workforce._sync_shared_memory"></a>

### _sync_shared_memory

```python
def _sync_shared_memory(self):
```

Synchronize memory across all agents by collecting and sharing.

<a id="camel.societies.workforce.workforce.Workforce._update_dependencies_for_decomposition"></a>

### _update_dependencies_for_decomposition

```python
def _update_dependencies_for_decomposition(self, original_task: Task, subtasks: List[Task]):
```

Update dependency tracking when a task is decomposed into subtasks.
Tasks that depended on the original task should now depend on all
subtasks. The last subtask inherits the original task's dependencies.

<a id="camel.societies.workforce.workforce.Workforce._increment_in_flight_tasks"></a>

### _increment_in_flight_tasks

```python
def _increment_in_flight_tasks(self, task_id: str):
```

Safely increment the in-flight tasks counter with logging.

<a id="camel.societies.workforce.workforce.Workforce._decrement_in_flight_tasks"></a>

### _decrement_in_flight_tasks

```python
def _decrement_in_flight_tasks(self, task_id: str, context: str = ''):
```

Safely decrement the in-flight tasks counter with safety checks.

<a id="camel.societies.workforce.workforce.Workforce._cleanup_task_tracking"></a>

### _cleanup_task_tracking

```python
def _cleanup_task_tracking(self, task_id: str):
```

Clean up tracking data for a task to prevent memory leaks.

**Parameters:**

- **task_id** (str): The ID of the task to clean up.

<a id="camel.societies.workforce.workforce.Workforce._decompose_task"></a>

### _decompose_task

```python
def _decompose_task(self, task: Task):
```

**Returns:**

  Union[List[Task], Generator[List[Task], None, None]]:
The subtasks or generator of subtasks.

<a id="camel.societies.workforce.workforce.Workforce._analyze_failure"></a>

### _analyze_failure

```python
def _analyze_failure(self, task: Task, error_message: str):
```

Analyze a task failure and decide on the best recovery strategy.

**Parameters:**

- **task** (Task): The failed task
- **error_message** (str): The error message from the failure

**Returns:**

  RecoveryDecision: The decided recovery strategy with reasoning

<a id="camel.societies.workforce.workforce.Workforce.pause"></a>

### pause

```python
def pause(self):
```

Pause the workforce execution.
If the internal event-loop is already running we schedule the
asynchronous pause coroutine onto it.  When the loop has not yet
been created (e.g. the caller presses the hot-key immediately after
workforce start-up) we fall back to a synchronous state change so
that no tasks will be scheduled until the loop is ready.

<a id="camel.societies.workforce.workforce.Workforce.resume"></a>

### resume

```python
def resume(self):
```

Resume execution after a manual pause.

<a id="camel.societies.workforce.workforce.Workforce.stop_gracefully"></a>

### stop_gracefully

```python
def stop_gracefully(self):
```

Request workforce to finish current in-flight work then halt.

Works both when the internal event-loop is alive and when it has not
yet been started.  In the latter case we simply mark the stop flag so
that the loop (when it eventually starts) will exit immediately after
initialisation.

<a id="camel.societies.workforce.workforce.Workforce.save_snapshot"></a>

### save_snapshot

```python
def save_snapshot(self, description: str = ''):
```

Save current state as a snapshot.

<a id="camel.societies.workforce.workforce.Workforce.list_snapshots"></a>

### list_snapshots

```python
def list_snapshots(self):
```

List all available snapshots.

<a id="camel.societies.workforce.workforce.Workforce.get_pending_tasks"></a>

### get_pending_tasks

```python
def get_pending_tasks(self):
```

Get current pending tasks for human review.

<a id="camel.societies.workforce.workforce.Workforce.get_completed_tasks"></a>

### get_completed_tasks

```python
def get_completed_tasks(self):
```

Get completed tasks.

<a id="camel.societies.workforce.workforce.Workforce.modify_task_content"></a>

### modify_task_content

```python
def modify_task_content(self, task_id: str, new_content: str):
```

Modify the content of a pending task.

<a id="camel.societies.workforce.workforce.Workforce.add_task"></a>

### add_task

```python
def add_task(
    self,
    content: str,
    task_id: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None,
    insert_position: int = -1
):
```

Add a new task to the pending queue.

<a id="camel.societies.workforce.workforce.Workforce.remove_task"></a>

### remove_task

```python
def remove_task(self, task_id: str):
```

Remove a task from the pending queue.

<a id="camel.societies.workforce.workforce.Workforce.reorder_tasks"></a>

### reorder_tasks

```python
def reorder_tasks(self, task_ids: List[str]):
```

Reorder pending tasks according to the provided task IDs list.

<a id="camel.societies.workforce.workforce.Workforce.resume_from_task"></a>

### resume_from_task

```python
def resume_from_task(self, task_id: str):
```

Resume execution from a specific task.

<a id="camel.societies.workforce.workforce.Workforce.restore_from_snapshot"></a>

### restore_from_snapshot

```python
def restore_from_snapshot(self, snapshot_index: int):
```

Restore workforce state from a snapshot.

<a id="camel.societies.workforce.workforce.Workforce.get_workforce_status"></a>

### get_workforce_status

```python
def get_workforce_status(self):
```

Get current workforce status for human review.

<a id="camel.societies.workforce.workforce.Workforce.process_task"></a>

### process_task

```python
def process_task(self, task: Task):
```

Synchronous wrapper for process_task that handles async operations
internally.

**Parameters:**

- **task** (Task): The task to be processed.

**Returns:**

  Task: The updated task.

<a id="camel.societies.workforce.workforce.Workforce._process_task_with_intervention"></a>

### _process_task_with_intervention

```python
def _process_task_with_intervention(self, task: Task):
```

Process task with human intervention support. This creates and
manages its own event loop to allow for pausing/resuming functionality.

**Parameters:**

- **task** (Task): The task to be processed.

**Returns:**

  Task: The updated task.

<a id="camel.societies.workforce.workforce.Workforce.continue_from_pause"></a>

### continue_from_pause

```python
def continue_from_pause(self):
```

**Returns:**

  Optional[Task]: The completed task if execution finishes, None if
still running/paused.

<a id="camel.societies.workforce.workforce.Workforce._start_child_node_when_paused"></a>

### _start_child_node_when_paused

```python
def _start_child_node_when_paused(self, start_coroutine: Coroutine):
```

Helper to start a child node when workforce is paused.

**Parameters:**

- **start_coroutine**: The coroutine to start (e.g., worker_node.start())

<a id="camel.societies.workforce.workforce.Workforce.add_single_agent_worker"></a>

### add_single_agent_worker

```python
def add_single_agent_worker(
    self,
    description: str,
    worker: ChatAgent,
    pool_max_size: int = DEFAULT_WORKER_POOL_SIZE
):
```

Add a worker node to the workforce that uses a single agent.
Can be called when workforce is paused to dynamically add workers.

**Parameters:**

- **description** (str): Description of the worker node.
- **worker** (ChatAgent): The agent to be added.
- **pool_max_size** (int): Maximum size of the agent pool. (default: :obj:`10`)

**Returns:**

  Workforce: The workforce node itself.

<a id="camel.societies.workforce.workforce.Workforce.add_role_playing_worker"></a>

### add_role_playing_worker

```python
def add_role_playing_worker(
    self,
    description: str,
    assistant_role_name: str,
    user_role_name: str,
    assistant_agent_kwargs: Optional[Dict] = None,
    user_agent_kwargs: Optional[Dict] = None,
    summarize_agent_kwargs: Optional[Dict] = None,
    chat_turn_limit: int = 3
):
```

Add a worker node to the workforce that uses `RolePlaying` system.
Can be called when workforce is paused to dynamically add workers.

**Parameters:**

- **description** (str): Description of the node.
- **assistant_role_name** (str): The role name of the assistant agent.
- **user_role_name** (str): The role name of the user agent.
- **assistant_agent_kwargs** (Optional[Dict]): The keyword arguments to initialize the assistant agent in the role playing, like the model name, etc. (default: :obj:`None`)
- **user_agent_kwargs** (Optional[Dict]): The keyword arguments to initialize the user agent in the role playing, like the model name, etc. (default: :obj:`None`)
- **summarize_agent_kwargs** (Optional[Dict]): The keyword arguments to initialize the summarize agent, like the model name, etc. (default: :obj:`None`)
- **chat_turn_limit** (int): The maximum number of chat turns in the role playing. (default: :obj:`3`)

**Returns:**

  Workforce: The workforce node itself.

<a id="camel.societies.workforce.workforce.Workforce.add_workforce"></a>

### add_workforce

```python
def add_workforce(self, workforce: Workforce):
```

Add a workforce node to the workforce.
Can be called when workforce is paused to dynamically add workers.

**Parameters:**

- **workforce** (Workforce): The workforce node to be added.

**Returns:**

  Workforce: The workforce node itself.

<a id="camel.societies.workforce.workforce.Workforce.reset"></a>

### reset

```python
def reset(self):
```

Reset the workforce and all the child nodes under it. Can only
be called when the workforce is not running.

<a id="camel.societies.workforce.workforce.Workforce.set_channel"></a>

### set_channel

```python
def set_channel(self, channel: TaskChannel):
```

Set the channel for the node and all the child nodes under it.

<a id="camel.societies.workforce.workforce.Workforce._get_child_nodes_info"></a>

### _get_child_nodes_info

```python
def _get_child_nodes_info(self):
```

Get the information of all the child nodes under this node.

<a id="camel.societies.workforce.workforce.Workforce._get_valid_worker_ids"></a>

### _get_valid_worker_ids

```python
def _get_valid_worker_ids(self):
```

**Returns:**

  set: Set of valid worker IDs that can be assigned tasks.

<a id="camel.societies.workforce.workforce.Workforce._call_coordinator_for_assignment"></a>

### _call_coordinator_for_assignment

```python
def _call_coordinator_for_assignment(self, tasks: List[Task], invalid_ids: Optional[List[str]] = None):
```

Call coordinator agent to assign tasks with optional validation
feedback in the case of invalid worker IDs.

**Parameters:**

- **tasks** (List[Task]): Tasks to assign.
- **invalid_ids** (List[str], optional): Invalid worker IDs from previous attempt (if any).

**Returns:**

  TaskAssignResult: Assignment result from coordinator.

<a id="camel.societies.workforce.workforce.Workforce._validate_assignments"></a>

### _validate_assignments

```python
def _validate_assignments(self, assignments: List[TaskAssignment], valid_ids: Set[str]):
```

Validate task assignments against valid worker IDs.

**Parameters:**

- **assignments** (List[TaskAssignment]): Assignments to validate.
- **valid_ids** (Set[str]): Set of valid worker IDs.

**Returns:**

  Tuple[List[TaskAssignment], List[TaskAssignment]]:
(valid_assignments, invalid_assignments)

<a id="camel.societies.workforce.workforce.Workforce.get_workforce_log_tree"></a>

### get_workforce_log_tree

```python
def get_workforce_log_tree(self):
```

Returns an ASCII tree representation of the task hierarchy and
worker status.

<a id="camel.societies.workforce.workforce.Workforce.get_workforce_kpis"></a>

### get_workforce_kpis

```python
def get_workforce_kpis(self):
```

Returns a dictionary of key performance indicators.

<a id="camel.societies.workforce.workforce.Workforce.dump_workforce_logs"></a>

### dump_workforce_logs

```python
def dump_workforce_logs(self, file_path: str):
```

Dumps all collected logs to a JSON file.

**Parameters:**

- **file_path** (str): The path to the JSON file.

<a id="camel.societies.workforce.workforce.Workforce._submit_coro_to_loop"></a>

### _submit_coro_to_loop

```python
def _submit_coro_to_loop(self, coro: 'Coroutine'):
```

Thread-safe submission of coroutine to the workforce loop.

<a id="camel.societies.workforce.workforce.Workforce.stop"></a>

### stop

```python
def stop(self):
```

Stop all the child nodes under it. The node itself will be stopped
by its parent node.

<a id="camel.societies.workforce.workforce.Workforce.clone"></a>

### clone

```python
def clone(self, with_memory: bool = False):
```

Creates a new instance of Workforce with the same configuration.

**Parameters:**

- **with_memory** (bool, optional): Whether to copy the memory (conversation history) to the new instance. If True, the new instance will have the same conversation history. If False, the new instance will have a fresh memory. (default: :obj:`False`)

**Returns:**

  Workforce: A new instance of Workforce with the same configuration.

<a id="camel.societies.workforce.workforce.Workforce.to_mcp"></a>

### to_mcp

```python
def to_mcp(
    self,
    name: str = 'CAMEL-Workforce',
    description: str = 'A workforce system using the CAMEL AI framework for multi-agent collaboration.',
    dependencies: Optional[List[str]] = None,
    host: str = 'localhost',
    port: int = 8001
):
```

Expose this Workforce as an MCP server.

**Parameters:**

- **name** (str): Name of the MCP server. (default: :obj:`CAMEL-Workforce`)
- **description** (str): Description of the workforce. If None, a generic description is used. (default: :obj:`A workforce system using the CAMEL AI framework for multi-agent collaboration.`)
- **dependencies** (Optional[List[str]]): Additional dependencies for the MCP server. (default: :obj:`None`)
- **host** (str): Host to bind to for HTTP transport. (default: :obj:`localhost`)
- **port** (int): Port to bind to for HTTP transport. (default: :obj:`8001`)

**Returns:**

  FastMCP: An MCP server instance that can be run.
