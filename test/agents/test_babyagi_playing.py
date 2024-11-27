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
import pytest

from camel.agents import ChatAgent, TaskCreationAgent, TaskPrioritizationAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies import BabyAGI
from camel.types import (
    ModelPlatformType,
    ModelType,
    RoleType,
    TaskType,
)

parametrize = pytest.mark.parametrize(
    'model',
    [
        ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.STUB,
        ),
        pytest.param(None, marks=pytest.mark.model_backend),
    ],
)


@parametrize
def test_babyagi_playing_init(model):
    task_prompt = "Develop a trading bot for the stock market"

    babyagi_playing = BabyAGI(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="Stock Trader",
        task_prompt=task_prompt,
        task_specify_agent_kwargs=dict(model=model),
        message_window_size=5,
    )

    assert babyagi_playing.task_type == TaskType.AI_SOCIETY
    assert babyagi_playing.specified_task_prompt is not None

    assert isinstance(babyagi_playing.assistant_sys_msg, BaseMessage)
    assert babyagi_playing.assistant_sys_msg.role_type == RoleType.ASSISTANT

    assert isinstance(babyagi_playing.assistant_agent, ChatAgent)
    assert isinstance(babyagi_playing.task_creation_agent, TaskCreationAgent)
    assert isinstance(
        babyagi_playing.task_prioritization_agent, TaskPrioritizationAgent
    )

    assert len(babyagi_playing.subtasks) == 0
    assert len(babyagi_playing.solved_subtasks) == 0


@parametrize
def test_babyagi_playing_step(model):
    task_prompt = "Develop a trading bot for the stock market"

    babyagi_playing = BabyAGI(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="Stock Trader",
        task_prompt=task_prompt,
        task_specify_agent_kwargs=dict(model=model),
        message_window_size=5,
    )

    print(f"AI Assistant sys message:\n{babyagi_playing.assistant_sys_msg}\n")
    print(f"Original task prompt:\n{task_prompt}\n")
    print(f"Specified task prompt:\n{babyagi_playing.specified_task_prompt}\n")

    assistant_response = babyagi_playing.step()

    assert isinstance(assistant_response.msgs, list)
    assert len(assistant_response.msgs) == 1
    assert isinstance(assistant_response.msgs[0], BaseMessage)
    assert isinstance(assistant_response.terminated, bool)
    assert assistant_response.terminated is False
    assert isinstance(assistant_response.info, dict)

    assert len(babyagi_playing.subtasks) > 0
    assert len(babyagi_playing.solved_subtasks) == 1
