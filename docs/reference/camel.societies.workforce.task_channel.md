<a id="camel.societies.workforce.task_channel"></a>

<a id="camel.societies.workforce.task_channel.PacketStatus"></a>

## PacketStatus

```python
class PacketStatus(Enum):
```

The status of a packet. The packet can be in one of the following
states:

- `__INLINE_CODE_0__`: The packet has been sent to a worker.
- `__INLINE_CODE_1__`: The packet has been claimed by a worker and is being
processed.
- `__INLINE_CODE_2__`: The packet has been returned by the worker, meaning that
the status of the task inside has been updated.
- `__INLINE_CODE_3__`: The packet has been archived, meaning that the content of
the task inside will not be changed. The task is considered
as a dependency.

<a id="camel.societies.workforce.task_channel.Packet"></a>

## Packet

```python
class Packet:
```

The basic element inside the channel. A task is wrapped inside a
packet. The packet will contain the task, along with the task's assignee,
and the task's status.

**Parameters:**

- **task** (Task): The task that is wrapped inside the packet.
- **publisher_id** (str): The ID of the workforce that published the task.
- **assignee_id** (Optional[str], optional): The ID of the workforce that is assigned to the task. Would be None if the task is a dependency. Defaults to None.
- **status** (PacketStatus): The status of the task.

<a id="camel.societies.workforce.task_channel.Packet.__init__"></a>

### __init__

```python
def __init__(
    self,
    task: Task,
    publisher_id: str,
    assignee_id: Optional[str] = None,
    status: PacketStatus = PacketStatus.SENT
):
```

<a id="camel.societies.workforce.task_channel.Packet.__repr__"></a>

### __repr__

```python
def __repr__(self):
```

<a id="camel.societies.workforce.task_channel.TaskChannel"></a>

## TaskChannel

```python
class TaskChannel:
```

An internal class used by Workforce to manage tasks.

<a id="camel.societies.workforce.task_channel.TaskChannel.__init__"></a>

### __init__

```python
def __init__(self):
```
