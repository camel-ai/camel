# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.tasks import (
    Task,
    TaskManager,
)
from camel.types import (
    ModelPlatformType,
    ModelType,
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# set up agent
assistant_sys_msg = "You are a personal math tutor and programmer."
agent = ChatAgent(assistant_sys_msg, model)
agent.reset()

task = Task(
    content="Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?",
    id="0",
)
print(task.to_string())


task_manager = TaskManager(task)

evolved_task = task_manager.evolve(task, agent=agent)
if evolved_task is not None:
    print(evolved_task.to_string())
else:
    print("Evolved task is None.")


new_tasks = task.decompose(agent=agent)
for t in new_tasks:
    print(t.to_string())

# ruff: noqa: E501
"""
===============================================================================
Task 0: Weng earns $12 an hour for babysitting. Yesterday, she just did 51 
minutes of babysitting. How much did she earn?

Task 0.0: Weng earns $12 an hour for babysitting. However, her hourly rate 
increases by $2 for every additional hour worked beyond the first hour. 
Yesterday, she babysat for a total of 3 hours and 45 minutes. How much did she 
earn in total for her babysitting services?

Task 0.0: Convert 51 minutes to hours.

Task 0.1: Calculate the proportion of 51 minutes to an hour.

Task 0.2: Multiply the proportion by Weng's hourly rate to find out how much 
she earned for 51 minutes of babysitting.
===============================================================================
"""
