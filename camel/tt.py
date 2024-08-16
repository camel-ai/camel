from camel.agents import ChatAgent
from camel.tasks import Task
from camel.tasks.task_prompt import (
    TASK_COMPOSE_PROMPT,
    TASK_DECOMPOSE_PROMPT,
)
from camel.messages import BaseMessage

from camel.tasks import (
    Task,
    TaskManager,
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
# print(task.to_string())

task_manager = TaskManager(task)
evolved_task = task_manager.evolve(task, agent=agent)
print(evolved_task.to_string())