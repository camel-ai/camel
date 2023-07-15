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
from camel.messages import BaseMessage
from camel.agents import BabyAGIAgent
from camel.configs import ChatGPTConfig
from camel.generators import SystemMessageGenerator
from camel.typing import ModelType, RoleType, TaskType
from camel.agents.chat_agent import ChatAgentResponse

parametrize = pytest.mark.parametrize('model', [
    ModelType.STUB,
    pytest.param(ModelType.GPT_3_5_TURBO, marks=pytest.mark.model_backend),
    pytest.param(ModelType.GPT_4, marks=pytest.mark.model_backend),
])


@parametrize
def test_babyagi_agent(model: ModelType):

    model_config = ChatGPTConfig()
    system_msg = SystemMessageGenerator(
        task_type=TaskType.AI_SOCIETY).from_dict(
            dict(assistant_role="doctor"),
            role_tuple=("doctor", RoleType.ASSISTANT),
        )
    objective = "Solve gastric cancel."

    babyagi = BabyAGIAgent(system_msg, objective, model=model,
                           model_config=model_config)
    babyagi.reset()
    assert babyagi.tasks_storage.is_empty() is True
    babyagi.tasks_storage.append({'task_name': objective})
    task = babyagi.tasks_storage.popleft()
    assert babyagi.tasks_storage.is_empty() is True
    prompt = 'Instruction: ' + task['task_name']
    user_msg = BaseMessage(role_name="Patient", role_type=RoleType.USER,
                           meta_dict=dict(), content=prompt)
    response = babyagi.step(user_msg)
    assert isinstance(response.msgs, list)
    assert len(response.msgs) > 0
    assert isinstance(response.terminated, bool)
    assert response.terminated is False
    assert isinstance(response.info, dict)
    assert response.info['id'] is not None
    assert babyagi.tasks_storage.is_empty() is False

    task = babyagi.tasks_storage.popleft()
    prompt = 'Instruction: ' + task['task_name']
    user_msg = BaseMessage(role_name="Patient", role_type=RoleType.USER,
                           meta_dict=dict(), content=prompt)
    result, result_content = babyagi.execution_agent(user_msg)
    assert isinstance(result, ChatAgentResponse)
    assert isinstance(result_content, str)

    enriched_result = {"data": result_content}
    new_tasks = babyagi.task_creation_agent(
        babyagi.objective,
        enriched_result,
        prompt,
        babyagi.tasks_storage.get_task_names(),
    )
    assert isinstance(new_tasks, list)
    assert len(new_tasks) > 0
    assert isinstance(new_tasks[0], dict)

    for new_task in new_tasks:
        babyagi.tasks_storage.append(new_task)

    prioritized_tasks = babyagi.prioritization_agent()
    assert isinstance(prioritized_tasks, list)
    assert len(prioritized_tasks) > 0
    assert isinstance(prioritized_tasks[0], dict)
