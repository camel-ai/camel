# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import pytest

from camel.agents import BabyAGIAgent
from camel.configs import ChatGPTConfig
from camel.typing import ModelType

parametrize = pytest.mark.parametrize('model', [
    ModelType.STUB,
    pytest.param(ModelType.GPT_3_5_TURBO, marks=pytest.mark.model_backend),
    pytest.param(ModelType.GPT_4, marks=pytest.mark.model_backend),
])


@parametrize
def test_babyagi_agent(model: ModelType):
    model_config = ChatGPTConfig()
    objective = "Solve world hunger."
    first_task = {"task_id": 1, "task_name": "Develop a task list."}
    babyagi = BabyAGIAgent(objective, model=model, model_config=model_config)
    babyagi.reset(first_task)
    assert babyagi.tasks_storage.is_empty() is False

    task = babyagi.tasks_storage.popleft()
    assert babyagi.tasks_storage.is_empty() is True

    result = babyagi.execution_agent(objective, task["task_name"])
    assert isinstance(result, str)

    result_id = f"result_{task['task_id']}"
    babyagi.results_storage.add(task, result, result_id)

    enriched_result = {"data": result}
    new_tasks = babyagi.task_creation_agent(
        objective,
        enriched_result,
        task["task_name"],
        babyagi.tasks_storage.get_task_names(),
    )
    assert isinstance(new_tasks, list)
    assert len(new_tasks) > 0
    assert isinstance(new_tasks[0], dict)

    for new_task in new_tasks:
        new_task.update({"task_id": babyagi.tasks_storage.next_task_id()})
        babyagi.tasks_storage.append(new_task)

    prioritized_tasks = babyagi.prioritization_agent()
    assert isinstance(prioritized_tasks, list)
    assert len(prioritized_tasks) > 0
    assert isinstance(prioritized_tasks[0], dict)
    """
    # this test is to check if new prioritized tasks and old tasks are
    # different only in the task ordering. But they may differ slightly.
    # because the prioritized tasks are generated from openai api
    # based on old tasks. Some words may change.
    old_number_tasks = list(babyagi.tasks_storage.tasks)
    old_number_tasks_names = [task['task_name'] for task in old_number_tasks]
    if prioritized_tasks:
        babyagi.tasks_storage.replace(prioritized_tasks)
    new_number_tasks = list(babyagi.tasks_storage.tasks)
    new_number_tasks_names = [task['task_name'] for task in new_number_tasks]
    for task in old_number_tasks_names:
        assert task in new_number_tasks_names
    for task in new_number_tasks_names:
        assert task in old_number_tasks_names
    """
