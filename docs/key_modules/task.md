# Task

> In the CAMEL framework, a task is a specific assignment that can be delegated to an agent and resolved by that agent. Tasks represent a higher-level concept than prompts and should be managed by other modules such as the Planner and Workforce. There are two key characteristics of a task: 1. A task can be collaborative, requiring multiple agents to work together. 2. A task can be decomposed and evolved.

## Task Attributes

| Attribute | Type | Description |
| ----- | ----- | ----- |
| content | string | A clear and concise description of the task at hand. |
| id | string | An unique string identifier for the task. |
| state | Enum | The task states:  "OPEN", "RUNNING", "DONE", "FAILED", "DELETED". |
| type | string | The type of a task. (TODO) |
| parent | Task | The parent task. |
| subtasks | A list of Task | A list of sub tasks related the original Task. |
| result | string | The Task result. |

## Task Methods

| Method | Type | Description |
| ----- | ----- | ----- |
| from_message | classmethod | Load Task from Message. |
| to_message | classmethod | Convert Task to Message. |
| reset | instance | Reset Task to initial state. |
| update_result | instance | Set task result and mark the task as DONE. |
| set_id | instance | Set task id. |
| set_state | instance | Recursively set the state of the task and its subtasks. |
| add_subtask | instance | Add child task. |
| remove_subtask | instance | Delete a subtask by a giving id. |
| get_running_task | instance | Get a RUNNING task. |
| to_string | instance | Convert task to a string. |
| get_result | instance | Get task result to a string. |
| decompose | instance | Decompose a task to a list of sub-tasks. |
| compose | instance | Compose task result by the sub-tasks. |
| get_depth | instance | Get task depth while the root depth is 1. |

## Creating a Task

Creating a task involves defining its goal (content) and id:

### Example of Task definition

```python
from camel.tasks import Task

task = Task(
    content="Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?",
    id="0",
)
```

### Example of multiple Tasks with a hierarchical structure.

```python
root_task = Task(content="a start task", id="0")
sub_task_1 = Task(content="a sub task 1", id="1")
sub_task_2 = Task(content="a sub task 2", id="2")
sub_task_3 = Task(content="a sub task 3", id="3")
sub_task_2_1 = Task(content="a sub task of task 2", id="2.1")
sub_task_2_2 = Task(content="a sub task of task 2", id="2.2")
root_task.add_subtask(sub_task_1)
root_task.add_subtask(sub_task_2)
root_task.add_subtask(sub_task_3)
sub_task_2.add_subtask(sub_task_2_1)
sub_task_2.add_subtask(sub_task_2_2)
print(root_task.to_string())
"""
Task 0: a start task
  Task 1: a sub task 1
  Task 2: a sub task 2
      Task 2.1: a sub task of task 2
      Task 2.2: a sub task of task 2
  Task 3: a sub task 3
"""
```

## Decomposing and composing a Task

Decomposing or composing a task involves defining its responsible agent, prompt template and agent response parser. Here is a example:

```python
from camel.agents import ChatAgent
from camel.tasks import Task
from camel.tasks.task_prompt import (
    TASK_COMPOSE_PROMPT,
    TASK_DECOMPOSE_PROMPT,
)

# set up LLM model
agent = ...

task = Task(
    content="Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?",
    id="0",
)


new_tasks = task.decompose(agent=agent, template=TASK_DECOMPOSE_PROMPT)
for t in new_tasks:
    print(t.to_string())
"""
Task 0.1: Calculate the proportion of 51 minutes to an hour.

Task 0.2: Multiply the proportion by Weng's hourly rate to find out how much she earned for 51 minutes of babysitting.

"""

# compose task result by the sub-tasks.
task.compose(agent=agent, template=TASK_COMPOSE_PROMPT)
print(task.result)
```

## TaskManager

TaskManager is used to manage tasks.

| Method | Type | Description |
| ----- | ----- | ----- |
| topological_sort | instance | Sort a list of tasks topologically. |
| set_tasks_dependence | instance | Set relationship between root task and other tasks. Two relationships are currently supported: serial and parallel. |
| evolve | instance | Evolve a task to a new task and here it is only used for data generation. |


### Example

```python
from camel.tasks import (
    Task,
    TaskManager,
)

# set up LLM model
agent = ...


task = Task(
    content="Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?",
    id="0",
)
print(task.to_string())

task_manager = TaskManager(task)
evolved_task = task_manager.evolve(task, agent=agent)
print(evolved_task.to_string())

"""
Task 0.0: Weng earns $12 an hour for babysitting. However, her hourly rate 
increases by $2 for every additional hour worked beyond the first hour. 
Yesterday, she babysat for a total of 3 hours and 45 minutes. How much did she 
earn in total for her babysitting services?
"""
```