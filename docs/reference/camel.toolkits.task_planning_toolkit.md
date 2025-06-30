<a id="camel.toolkits.task_planning_toolkit"></a>

<a id="camel.toolkits.task_planning_toolkit.TaskPlanningToolkit"></a>

## TaskPlanningToolkit

```python
class TaskPlanningToolkit(BaseToolkit):
```

A toolkit for task decomposition and re-planning.

<a id="camel.toolkits.task_planning_toolkit.TaskPlanningToolkit.__init__"></a>

### __init__

```python
def __init__(self, timeout: Optional[float] = None):
```

Initialize the TaskPlanningToolkit.

**Parameters:**

- **timeout** (Optional[float]): The timeout for the toolkit. (default: :obj:`None`)

<a id="camel.toolkits.task_planning_toolkit.TaskPlanningToolkit.decompose_task"></a>

### decompose_task

```python
def decompose_task(
    self,
    original_task_content: str,
    sub_task_contents: List[str],
    original_task_id: Optional[str] = None
):
```

Use the tool to decompose an original task into several sub-tasks.
It creates new Task objects from the provided original task content,
used when the original task is complex and needs to be decomposed.

**Parameters:**

- **original_task_content** (str): The content of the task to be decomposed.
- **sub_task_contents** (List[str]): A list of strings, where each string is the content for a new sub-task.
- **original_task_id** (Optional[str]): The id of the task to be decomposed. If not provided, a new id will be generated. (default: :obj:`None`)

**Returns:**

  List[Task]: A list of newly created sub-task objects.

<a id="camel.toolkits.task_planning_toolkit.TaskPlanningToolkit.replan_tasks"></a>

### replan_tasks

```python
def replan_tasks(
    self,
    original_task_content: str,
    sub_task_contents: List[str],
    original_task_id: Optional[str] = None
):
```

Use the tool to re_decompose a task into several subTasks.
It creates new Task objects from the provided original task content,
used when the decomposed tasks are not good enough to help finish
the task.

**Parameters:**

- **original_task_content** (str): The content of the task to be decomposed.
- **sub_task_contents** (List[str]): A list of strings, where each string is the content for a new sub-task.
- **original_task_id** (Optional[str]): The id of the task to be decomposed. (default: :obj:`None`)

**Returns:**

  List[Task]: Reordered or modified tasks.

<a id="camel.toolkits.task_planning_toolkit.TaskPlanningToolkit.get_tools"></a>

### get_tools

```python
def get_tools(self):
```
