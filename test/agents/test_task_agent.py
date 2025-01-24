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

from camel.agents import (
    TaskCreationAgent,
    TaskPlannerAgent,
    TaskPrioritizationAgent,
    TaskSpecifyAgent,
)
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType, TaskType

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
def test_task_specify_ai_society_agent(model):
    original_task_prompt = "Improving stage presence and performance skills"
    print(f"Original task prompt:\n{original_task_prompt}\n")
    task_specify_agent = TaskSpecifyAgent(model=model)
    specified_task_prompt = task_specify_agent.run(
        original_task_prompt,
        meta_dict=dict(assistant_role="Musician", user_role="Student"),
    )
    assert "{" and "}" not in specified_task_prompt
    print(f"Specified task prompt:\n{specified_task_prompt}\n")


@parametrize
def test_task_specify_code_agent(model):
    original_task_prompt = "Modeling molecular dynamics"
    print(f"Original task prompt:\n{original_task_prompt}\n")
    task_specify_agent = TaskSpecifyAgent(model=model, task_type=TaskType.CODE)
    specified_task_prompt = task_specify_agent.run(
        original_task_prompt,
        meta_dict=dict(domain="Chemistry", language="Python"),
    )
    assert "{" and "}" not in specified_task_prompt
    print(f"Specified task prompt:\n{specified_task_prompt}\n")


@parametrize
def test_task_planner_agent(model):
    original_task_prompt = "Modeling molecular dynamics"
    print(f"Original task prompt:\n{original_task_prompt}\n")
    task_specify_agent = TaskSpecifyAgent(
        model=model,
        task_type=TaskType.CODE,
    )
    specified_task_prompt = task_specify_agent.run(
        original_task_prompt,
        meta_dict=dict(domain="Chemistry", language="Python"),
    )
    print(f"Specified task prompt:\n{specified_task_prompt}\n")
    task_planner_agent = TaskPlannerAgent()
    planned_task_prompt = task_planner_agent.run(specified_task_prompt)
    print(f"Planned task prompt:\n{planned_task_prompt}\n")


@parametrize
def test_task_creation_agent(model):
    original_task_prompt = "Modeling molecular dynamics"
    task_creation_agent = TaskCreationAgent(
        model=model,
        role_name="PhD in molecular biology",
        objective=original_task_prompt,
    )
    task_list = ["Study the computational technology for dynamics modeling"]
    planned_task = task_creation_agent.run(
        task_list=task_list,
    )
    print(f"Planned task list:\n{planned_task}\n")
    assert isinstance(planned_task, list)


@parametrize
def test_task_prioritization_agent(model):
    original_task_prompt = (
        "A high school student wants to " "prove the Riemann hypothesis"
    )

    task_list = [
        "Drop out of high school",
        "Start a tech company",
        "Become a billionaire",
        "Buy a yacht",
        "Obtain a bachelor degree in mathematics",
        "Obtain a PhD degree in mathematics",
        "Become a professor of mathematics",
    ]

    task_prioritization_agent = TaskPrioritizationAgent(
        objective=original_task_prompt,
        model=model,
    )

    prioritized_task = task_prioritization_agent.run(task_list=task_list)
    print(f"Prioritized task list:\n{prioritized_task}\n")
    assert isinstance(prioritized_task, list)
