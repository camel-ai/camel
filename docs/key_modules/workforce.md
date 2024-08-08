# Workforce

> *Workforce is a system where multiple agents/role-playing systems work together to solve tasks. By using Workforce, users can quickly set up a multi-agent task solving system with customized configurations. In this section, we will give a brief view on the architecture of workforce, and how you can configure and utilize it to solve problems.*

## Architecture

Workforce follows a tree-shaped architecture, with one or more managers (internal nodes) managing multiple fine-tuned workers with different roles (leaf nodes). A manager is responsible of managing and coordinating its child nodes and can also be a child of another manager; a worker, on the other hand, must be a child node of a manager.

> For now, CAMEL only supports the mode with one manager as root and multiple workers as direct leaf nodes of the root.

All manager and worker nodes share a single channel, where they can post and receive tasks, broadcast task results, etc.

## Workflow

In this section we are going to talk about how workforce works under the hood, briefly.

As mentioned above, workforce is a system to solve tasks. Based on this, intrinsically, we make the initial input to a workforce as be a `Task` instance describing the main task that should be solved. This task will then be passed into the root of the workforce as the initial task of it.

After starting up, the first thing that the root manager will do is decomposing the main task into multiple subtasks, so that it can be solved step by step.

Afterwards, the manager will assign each of them to a worker that is most capable of doing this task, according to the global information it has, such as the description of each worker it manages. The subtasks are not posted all in a time. Instead, due to the dependency relationships, it will only post tasks with all the dependencies (also tasks) completed.

Each worker will take the assigned tasks and try to complete it. If the task is successfully done, the worker will update the result of the task and notify the manager, so that the manager can post new tasks that depends on it.

However, task can fail. We don’t want to see this happen, but things go wrong. Fortunately, managers can fix this. When a task fails, the worker will report the failure to the manager, and manager can take one of the following actions:

1. decompose the task into smaller ones and assign them again
2. create a new worker that is capable of doing the task

For now, if the task has already been decomposed a lot of times, the manager will take the new worker creation action; if not, the manager will simply take the decomposition action.

When all the subtasks are finished, their results will be composed into a single, comprehensive result and then get updated into the main task instance and returned to the user.

## A Full Demo of Workforce

Below is a comprehensive example of the using of workforce.

```python
from camel.agents.chat_agent import ChatAgent
from camel.configs.openai_config import ChatGPTConfig
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.tasks.task import Task
from camel.toolkits import MAP_FUNCS, SEARCH_FUNCS, WEATHER_FUNCS
from camel.types import ModelPlatformType, ModelType
from camel.workforce.manager_node import ManagerNode
from camel.workforce.role_playing_node import RolePlayingNode
from camel.workforce.single_agent_node import SingleAgentNode
from camel.workforce.workforce import Workforce

def main():
    guide_sysmsg = BaseMessage.make_assistant_message(
        role_name="tour guide",
        content="You have to lead everyone to have fun",
    )

    planner_sysmsg = BaseMessage.make_assistant_message(
        role_name="planner",
        content="good at tour plan.",
    )

    guide_agent = ChatAgent(guide_sysmsg)
    planner_agent = ChatAgent(planner_sysmsg)

    guide_worker_node = SingleAgentNode('tour guide', guide_agent)
    planner_worker_node = SingleAgentNode('planner', planner_agent)

    function_list = [
        *SEARCH_FUNCS,
        *WEATHER_FUNCS,
        *MAP_FUNCS,
    ]
    user_model_config = ChatGPTConfig(temperature=0.0)
    assistant_model_config = ChatGPTConfig(
        tools=function_list,
        temperature=0.0,
    )
    model_platform = ModelPlatformType.OPENAI
    model_type = ModelType.GPT_3_5_TURBO
    assistant_role_name = "Searcher"
    user_role_name = "Professor"
    assistant_agent_kwargs = dict(
        model=ModelFactory.create(
            model_platform=model_platform,
            model_type=model_type,
            model_config_dict=assistant_model_config.__dict__,
        ),
        tools=function_list,
    )
    user_agent_kwargs = dict(
        model=ModelFactory.create(
            model_platform=model_platform,
            model_type=model_type,
            model_config_dict=user_model_config.__dict__,
        ),
    )
    research_rp_worker_node = RolePlayingNode(
        'research Group',
        assistant_role_name,
        user_role_name,
        assistant_agent_kwargs,
        user_agent_kwargs,
        1,
    )

    human_task = Task(
        content="research history of Paris and plan a tour.",
        id='0',
    )

    root_node = ManagerNode(
        description='a travel group',
        children=[
            guide_worker_node,
            planner_worker_node,
            research_rp_worker_node,
        ],
    )

    workforce = Workforce(root_node)
    task = workforce.process_task(human_task)

    print('Final Result of Origin task:\n', task.result)

if __name__ == "__main__":
    main()
```

Yes, it’s a long example. No worries though! We will take the whole process apart and explain these one by one. It’s not that complicated as it looks.

## Demo Explanation: Step by Step

### Configuration of Worker Nodes

A lot of the chores lie in the configurations of the worker nodes: we leave the full configuration freedom of each worker node to users, and we believe this is necessary to meet the desired performance and flexibility.

Therefore, inevitably there would be a lot of configurations that need to be done - and it takes up about 80 percent of the code. From this example, we can see that we first created two agents taking different roles

```python
guide_sysmsg = BaseMessage.make_assistant_message(
    role_name="tour guide",
    content="You have to lead everyone to have fun",
)

planner_sysmsg = BaseMessage.make_assistant_message(
    role_name="planner",
    content="good at tour plan.",
)

guide_agent = ChatAgent(guide_sysmsg)
planner_agent = ChatAgent(planner_sysmsg)
```

Then we wrapped them as two worker nodes with descriptions

```python
guide_worker_node = SingleAgentNode('tour guide', guide_agent)
planner_worker_node = SingleAgentNode('planner', planner_agent)
```

Similarly, we also created some configurations for a `RolePlaying`.

```python
function_list = [
    *SEARCH_FUNCS,
    *WEATHER_FUNCS,
    *MAP_FUNCS,
]
user_model_config = ChatGPTConfig(temperature=0.0)
assistant_model_config = ChatGPTConfig(
    tools=function_list,
    temperature=0.0,
)
model_platform = ModelPlatformType.OPENAI
model_type = ModelType.GPT_3_5_TURBO
assistant_role_name = "Searcher"
user_role_name = "Professor"
assistant_agent_kwargs = dict(
    model=ModelFactory.create(
        model_platform=model_platform,
        model_type=model_type,
        model_config_dict=assistant_model_config.__dict__,
    ),
    tools=function_list,
)
user_agent_kwargs = dict(
    model=ModelFactory.create(
        model_platform=model_platform,
        model_type=model_type,
        model_config_dict=user_model_config.__dict__,
    ),
)
```

And send these configurations into a worker node that uses `RolePlaying`.

```python
research_rp_worker_node = RolePlayingNode(
    'research Group',
    assistant_role_name,
    user_role_name,
    assistant_agent_kwargs,
    user_agent_kwargs,
    1,
)
```

> Note here, we didn’t directly create a `RolePlaying` instance and wrap it inside a worker node but passed its configurations into a worker node. This is because `RolePlaying` is designed to be recreated for each task, therefore the instantiation will be managed by the worker node itself, which is different from the `SingleAgentNode`.

If you make it here, congratulations! You have finished the configuration, and it’s the first and biggest step. Finishing this means you are almost done.

### Create Task

The task is what a workforce will solve. To create a task, simply pass in the content and the initial id.

```python
human_task = Task(
    content="research history of Paris and plan a tour.",
    id='0',
)
```

### Create Manager Node

To make these worker nodes collaborate with each other, we need to create a manager node to coordinate them by passing in these worker nodes as the `children`.

```python
root_node = ManagerNode(
    description='a travel group',
    children=[
        guide_worker_node,
        planner_worker_node,
        research_rp_worker_node,
    ],
)
```

> Note that, inside the manager node there will also be two agents, `coordinator_agent` and `task_planner` who will help on the coordination. To configure these, pass  `coordinator_agent_kwargs` and `task_agent_kwargs` into `ManagerNode`. Check the API docs for more information.

### Create Workforce & Process Task

Because we only have one layer in the current design of the workforce, this manager node also works as the root of the workforce.

We can create a workforce by passing the root node, and then call `process_task()` to start the workforce to work on the task.

```python
workforce = Workforce(root_node)
task = workforce.process_task(human_task)
```

Finally, we can get the result of the task by checking `task.result`.

```python
print('Final Result of Origin task:\n', task.result)
```