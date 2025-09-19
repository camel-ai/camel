---
title: "Tasks"
icon: list-check
---

For more detailed usage information, please refer to our cookbook: [Task Generation Cookbook](../cookbooks/multi_agent_society/task_generation.ipynb)

<Card title="What is a Task in CAMEL?" icon="clipboard-list">
A <b>task</b> in CAMEL is a structured assignment that can be given to one or more agents. Tasks are higher-level than prompts and managed by modules like the Planner and Workforce. 
<b>Key ideas:</b><br/>
- Tasks can be <b>collaborative</b>, requiring multiple agents.<br/>
- Tasks can be <b>decomposed</b> into subtasks or evolved over time.<br/>
</Card>

## Task Attributes

| Attribute | Type | Description |
| ----- | ----- | ----- |
| content | string | A clear and concise description of the task at hand. |
| id | string | A unique string identifier for the task. |
| state | Enum | The task states: "OPEN", "RUNNING", "DONE", "FAILED", "DELETED". |
| type | string | The type of a task. (TODO) |
| parent | Task | The parent task. |
| subtasks | A list of Task | Subtasks related to the original Task. |
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
| add_subtask | instance | Add a child task. |
| remove_subtask | instance | Delete a subtask by id. |
| get_running_task | instance | Get a RUNNING task. |
| to_string | instance | Convert task to a string. |
| get_result | instance | Get task result as a string. |
| decompose | instance | Decompose a task to a list of subtasks. |
| compose | instance | Compose task result by subtasks. |
| get_depth | instance | Get task depth; root depth is 1. |

<Card title="Getting Started: Creating Tasks" icon="bolt">
Defining a task is simple: specify its content and a unique ID.

<CodeGroup>
```python task_example.py
from camel.tasks import Task

task = Task(
    content="Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?",
    id="0",
)
```
</CodeGroup>
</Card>

<Card title="Hierarchical Tasks Example" icon="sitemap">
You can build nested, hierarchical tasks using subtasks. Here’s an example:

<CodeGroup>
```python tasks_hierarchical.py
# Creating the root task
root_task = Task(content="Prepare a meal", id="0")

# Creating subtasks for the root task
sub_task_1 = Task(content="Shop for ingredients", id="1")
sub_task_2 = Task(content="Cook the meal", id="2")
sub_task_3 = Task(content="Set the table", id="3")

# Creating subtasks under "Cook the meal"
sub_task_2_1 = Task(content="Chop vegetables", id="2.1")
sub_task_2_2 = Task(content="Cook rice", id="2.2")

# Adding subtasks to their respective parent tasks
root_task.add_subtask(sub_task_1)
root_task.add_subtask(sub_task_2)
root_task.add_subtask(sub_task_3)

sub_task_2.add_subtask(sub_task_2_1)
sub_task_2.add_subtask(sub_task_2_2)

# Printing the hierarchical task structure
print(root_task.to_string())
```
```markdown output
>>>
    Task 0: Prepare a meal
    Task 1: Shop for ingredients
    Task 2: Cook the meal
        Task 2.1: Chop vegetables
        Task 2.2: Cook rice
    Task 3: Set the table
```
</CodeGroup>
</Card>

## Decomposing and Composing a Task

You can break down (decompose) a task into smaller subtasks, or compose the results from subtasks. Typically, you define an agent, prompt template, and response parser.

<CodeGroup>
```python task_decompose.py
from camel.agents import ChatAgent
from camel.tasks import Task
from camel.tasks.task_prompt import (
    TASK_COMPOSE_PROMPT,
    TASK_DECOMPOSE_PROMPT,
)
from camel.messages import BaseMessage

sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant", content="You're a helpful assistant"
)
# Set up an agent
agent = ChatAgent(system_message=sys_msg)

task = Task(
    content="Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?",
    id="0",
)

new_tasks = task.decompose(agent=agent)
for t in new_tasks:
    print(t.to_string())
```
```markdown output
>>>
Task 0.0: Convert 51 minutes into hours.
Task 0.1: Calculate Weng's earnings for the converted hours at the rate of $12 per hour.
Task 0.2: Provide the final earnings amount based on the calculation.
```
</CodeGroup>

<CodeGroup>
```python task_compose.py
# Compose task result by the sub-tasks.
task.compose(agent=agent, template=TASK_COMPOSE_PROMPT)
print(task.result)
```
</CodeGroup>

## TaskManager

<Card title="TaskManager Overview" icon="list-check">
The <b>TaskManager</b> class helps you manage, sort, and evolve tasks—handling dependencies and progression automatically.
</Card>

| Method | Type | Description |
| ----- | ----- | ----- |
| topological_sort | instance | Sort a list of tasks topologically. |
| set_tasks_dependence | instance | Set relationship between root task and other tasks (serial or parallel). |
| evolve | instance | Evolve a task to a new task; used for data generation. |

<CodeGroup>
```python task_manager_example.py
from camel.tasks import (
    Task,
    TaskManager,
)
from camel.agents import ChatAgent

sys_msg = "You're a helpful assistant"
agent = ChatAgent(system_message=sys_msg)

task = Task(
    content="Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?",
    id="0",
)
print(task.to_string())
```
```markdown output
>>>Task 0: Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?
```
</CodeGroup>

<CodeGroup>
```python task_manager_evolve.py
task_manager = TaskManager(task)
evolved_task = task_manager.evolve(task, agent=agent)
print(evolved_task.to_string())
```
```markdown output
>>>Task 0.0: Weng earns $12 an hour for babysitting. Yesterday, she babysat for 1 hour and 45 minutes. If she also received a $5 bonus for exceptional service, how much did she earn in total for that day?
```
</CodeGroup>

<Card title="Conclusion" icon="trophy">
CAMEL offers a powerful, structured approach to task management. With support for task decomposition, composition, and deep hierarchies, you can automate everything from simple workflows to complex, multi-agent projects. Efficient, collaborative, and easy to integrate—this is next-level task orchestration for AI.
</Card>
