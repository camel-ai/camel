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
from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage

from camel.agents import ChatAgent, TaskCreationAgent, TaskPrioritizationAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies import BabyAGI
from camel.types import (
    ChatCompletion,
    ModelPlatformType,
    ModelType,
    RoleType,
    TaskType,
)

model_backend_rsp_base = ChatCompletion(
    id="mock_response_id",
    choices=[
        Choice(
            finish_reason="stop",
            index=0,
            logprobs=None,
            message=ChatCompletionMessage(
                content="Mock task specifier response",
                role="assistant",
                function_call=None,
                tool_calls=None,
            ),
        )
    ],
    created=123456789,
    model="gpt-4o-2024-05-13",
    object="chat.completion",
    usage=CompletionUsage(
        completion_tokens=32,
        prompt_tokens=15,
        total_tokens=47,
    ),
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
def test_babyagi_playing_step(model, step_call_count=3):
    task_prompt = "Develop a trading bot for the stock market"

    babyagi_playing = BabyAGI(
        assistant_role_name="Python Programmer",
        assistant_agent_kwargs=dict(model=model),
        user_role_name="Stock Trader",
        task_prompt=task_prompt,
        task_specify_agent_kwargs=dict(model=model),
        message_window_size=5,
    )

    # Mock model_backend responses
    # Initial task list when first calling babyagi_playing.step()
    task_creation_agent_model_rsp0 = deepcopy(model_backend_rsp_base)
    task_creation_agent_model_rsp0.choices[0].message.content = "1. Task 0"
    task_prioritization_agent_model_rsp0 = deepcopy(model_backend_rsp_base)
    task_prioritization_agent_model_rsp0.choices[
        0
    ].message.content = "1. Task 0"

    # Solve the highest priority (left most) task: Task 0
    assistant_agent_model_rsp1 = deepcopy(model_backend_rsp_base)
    assistant_agent_model_rsp1.choices[
        0
    ].message.content = "Solution for Task 0"

    # Task 0 is solved, remove from TaskPrioritizationAgent model response
    task_creation_agent_model_rsp1 = deepcopy(model_backend_rsp_base)
    task_creation_agent_model_rsp1.choices[
        0
    ].message.content = "1. \nTask 1\n\n2. Task 2\n\n3. Task 3"
    task_prioritization_agent_model_rsp1 = deepcopy(model_backend_rsp_base)
    task_prioritization_agent_model_rsp1.choices[
        0
    ].message.content = "1. Task 2  \nTask 1  \n3. Task 3 "

    # Solve the highest priority (left most) task: Task 2
    assistant_agent_model_rsp2 = deepcopy(model_backend_rsp_base)
    assistant_agent_model_rsp2.choices[
        0
    ].message.content = "Solution for Task 2"

    # Task 2 is solved, remove from TaskPrioritizationAgent model response
    task_creation_agent_model_rsp2 = deepcopy(model_backend_rsp_base)
    task_creation_agent_model_rsp2.choices[
        0
    ].message.content = "1. Task 4\n\n2. Task 5"
    task_prioritization_agent_model_rsp2 = deepcopy(model_backend_rsp_base)
    task_prioritization_agent_model_rsp2.choices[
        0
    ].message.content = "1. Task 1  \nTask 3  \n3. Task 4  \n4. Task 5"

    # Solve the highest priority (left most) task: Task 1
    assistant_agent_model_rsp3 = deepcopy(model_backend_rsp_base)
    assistant_agent_model_rsp3.choices[
        0
    ].message.content = "Solution for Task 1"

    # Task 1 is solved, remove from TaskPrioritizationAgent model response
    task_creation_agent_model_rsp3 = deepcopy(model_backend_rsp_base)
    task_creation_agent_model_rsp3.choices[
        0
    ].message.content = "1. Task 6\n\n2. Task 7\n\n3. Task 8"
    task_prioritization_agent_model_rsp3 = deepcopy(model_backend_rsp_base)
    task_prioritization_agent_model_rsp3.choices[0].message.content = (
        "1. Task 6  \nTask 3  \n3. Task 4  \n"
        "4. Task 7  \n5. Task 5 \n6. Task 8"
    )

    babyagi_playing.task_creation_agent.model_backend.run = MagicMock(
        side_effect=[
            task_creation_agent_model_rsp0,
            task_creation_agent_model_rsp1,
            task_creation_agent_model_rsp2,
            task_creation_agent_model_rsp3,
        ]
    )
    babyagi_playing.task_prioritization_agent.model_backend.run = MagicMock(
        side_effect=[
            task_prioritization_agent_model_rsp0,
            task_prioritization_agent_model_rsp1,
            task_prioritization_agent_model_rsp2,
            task_prioritization_agent_model_rsp3,
        ]
    )
    babyagi_playing.assistant_agent.model_backend.run = MagicMock(
        side_effect=[
            assistant_agent_model_rsp1,
            assistant_agent_model_rsp2,
            assistant_agent_model_rsp3,
        ]
    )

    print(f"AI Assistant sys message:\n{babyagi_playing.assistant_sys_msg}\n")
    print(f"Original task prompt:\n{task_prompt}\n")
    print(f"Specified task prompt:\n{babyagi_playing.specified_task_prompt}\n")

    for i in range(step_call_count):
        # Call assistant for multiple times to make test units more robust
        assistant_response = babyagi_playing.step()

        assert isinstance(
            assistant_response.msgs, list
        ), f"Error in calling round {i+1}"
        assert (
            len(assistant_response.msgs) == 1
        ), f"Error in calling round {i+1}"
        assert isinstance(
            assistant_response.msgs[0], BaseMessage
        ), f"Error in calling round {i+1}"
        assert isinstance(
            assistant_response.terminated, bool
        ), f"Error in calling round {i+1}"
        assert (
            assistant_response.terminated is False
        ), f"Error in calling round {i+1}"
        assert isinstance(
            assistant_response.info, dict
        ), f"Error in calling round {i+1}"

        assert (
            len(babyagi_playing.subtasks) > 0
        ), f"Error in calling round {i+1}"
        assert (
            len(babyagi_playing.solved_subtasks) == i + 1
        ), f"Error in calling round {i+1}"
