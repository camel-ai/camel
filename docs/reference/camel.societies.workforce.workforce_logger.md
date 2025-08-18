<a id="camel.societies.workforce.workforce_logger"></a>

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger"></a>

## WorkforceLogger

```python
class WorkforceLogger:
```

Logs events and metrics for a Workforce instance.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.__init__"></a>

### __init__

```python
def __init__(self, workforce_id: str):
```

Initializes the WorkforceLogger.

**Parameters:**

- **workforce_id** (str): The unique identifier for the workforce.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger._log_event"></a>

### _log_event

```python
def _log_event(self, event_type: str, **kwargs: Any):
```

Internal method to create and store a log entry.

**Parameters:**

- **event_type** (str): The type of event being logged. **kwargs: Additional data associated with the event.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.log_task_created"></a>

### log_task_created

```python
def log_task_created(
    self,
    task_id: str,
    description: str,
    parent_task_id: Optional[str] = None,
    task_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
```

Logs the creation of a new task.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.log_task_decomposed"></a>

### log_task_decomposed

```python
def log_task_decomposed(
    self,
    parent_task_id: str,
    subtask_ids: List[str],
    metadata: Optional[Dict[str, Any]] = None
):
```

Logs the decomposition of a task into subtasks.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.log_task_assigned"></a>

### log_task_assigned

```python
def log_task_assigned(
    self,
    task_id: str,
    worker_id: str,
    queue_time_seconds: Optional[float] = None,
    dependencies: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
```

Logs the assignment of a task to a worker.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.log_task_started"></a>

### log_task_started

```python
def log_task_started(
    self,
    task_id: str,
    worker_id: str,
    metadata: Optional[Dict[str, Any]] = None
):
```

Logs when a worker starts processing a task.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.log_task_completed"></a>

### log_task_completed

```python
def log_task_completed(
    self,
    task_id: str,
    worker_id: str,
    result_summary: Optional[str] = None,
    processing_time_seconds: Optional[float] = None,
    token_usage: Optional[Dict[str, int]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
```

Logs the successful completion of a task.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.log_task_failed"></a>

### log_task_failed

```python
def log_task_failed(
    self,
    task_id: str,
    error_message: str,
    worker_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
```

Logs the failure of a task.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.log_worker_created"></a>

### log_worker_created

```python
def log_worker_created(
    self,
    worker_id: str,
    worker_type: str,
    role: str,
    metadata: Optional[Dict[str, Any]] = None
):
```

Logs the creation of a new worker.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.log_worker_deleted"></a>

### log_worker_deleted

```python
def log_worker_deleted(
    self,
    worker_id: str,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
```

Logs the deletion of a worker.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.reset_task_data"></a>

### reset_task_data

```python
def reset_task_data(self):
```

Resets logs and data related to tasks, preserving worker
information.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.log_queue_status"></a>

### log_queue_status

```python
def log_queue_status(
    self,
    queue_name: str,
    length: int,
    pending_task_ids: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
```

Logs the status of a task queue.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.dump_to_json"></a>

### dump_to_json

```python
def dump_to_json(self, file_path: str):
```

Dumps all log entries to a JSON file.

**Parameters:**

- **file_path** (str): The path to the JSON file.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger._get_all_tasks_in_hierarchy"></a>

### _get_all_tasks_in_hierarchy

```python
def _get_all_tasks_in_hierarchy(self, task_id: str):
```

Recursively collect all tasks in the hierarchy starting from
task_id.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger._get_task_tree_string"></a>

### _get_task_tree_string

```python
def _get_task_tree_string(
    self,
    task_id: str,
    prefix: str = '',
    is_last: bool = True
):
```

Generate a string representation of the task tree.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.get_ascii_tree_representation"></a>

### get_ascii_tree_representation

```python
def get_ascii_tree_representation(self):
```

Generates an ASCII tree representation of the current task
hierarchy and worker status.

<a id="camel.societies.workforce.workforce_logger.WorkforceLogger.get_kpis"></a>

### get_kpis

```python
def get_kpis(self):
```

Calculates and returns key performance indicators from the logs.
