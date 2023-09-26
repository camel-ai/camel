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
from typing import Optional

import pytest

from camel.agents import (
    TaskCreationAgent,
    TaskPlannerAgent,
    TaskPrioritizationAgent,
    TaskSpecifyAgent,
)
from camel.configs import ChatGPTConfig
from camel.typing import ModelType, TaskType

parametrize = pytest.mark.parametrize('model', [
    ModelType.STUB,
    pytest.param(None, marks=pytest.mark.model_backend),
])


@parametrize
def test_task_specify_ai_society_agent(model: Optional[ModelType]):
    original_task_prompt = "Improving stage presence and performance skills"
    print(f"Original task prompt:\n{original_task_prompt}\n")
    task_specify_agent = TaskSpecifyAgent(
        model_config=ChatGPTConfig(temperature=1.0), model=model)
    specified_task_prompt = task_specify_agent.run(
        original_task_prompt, meta_dict=dict(assistant_role="Musician",
                                             user_role="Student"))
    assert ("{" and "}" not in specified_task_prompt)
    print(f"Specified task prompt:\n{specified_task_prompt}\n")


@parametrize
def test_task_specify_code_agent(model: Optional[ModelType]):
    original_task_prompt = "Modeling molecular dynamics"
    print(f"Original task prompt:\n{original_task_prompt}\n")
    task_specify_agent = TaskSpecifyAgent(
        task_type=TaskType.CODE,
        model_config=ChatGPTConfig(temperature=1.0),
        model=model,
    )
    specified_task_prompt = task_specify_agent.run(
        original_task_prompt, meta_dict=dict(domain="Chemistry",
                                             language="Python"))
    assert ("{" and "}" not in specified_task_prompt)
    print(f"Specified task prompt:\n{specified_task_prompt}\n")


@parametrize
def test_task_planner_agent(model: Optional[ModelType]):
    original_task_prompt = "Modeling molecular dynamics"
    print(f"Original task prompt:\n{original_task_prompt}\n")
    task_specify_agent = TaskSpecifyAgent(
        task_type=TaskType.CODE,
        model_config=ChatGPTConfig(temperature=1.0),
        model=model,
    )
    specified_task_prompt = task_specify_agent.run(
        original_task_prompt, meta_dict=dict(domain="Chemistry",
                                             language="Python"))
    print(f"Specified task prompt:\n{specified_task_prompt}\n")
    task_planner_agent = TaskPlannerAgent(
        model_config=ChatGPTConfig(temperature=1.0), model=model)
    planned_task_prompt = task_planner_agent.run(specified_task_prompt)
    print(f"Planned task prompt:\n{planned_task_prompt}\n")


@parametrize
def test_task_creation_agent(model: Optional[ModelType]):
    original_task_prompt = "Modeling molecular dynamics"
    task_creation_agent = TaskCreationAgent(
        model_config=ChatGPTConfig(temperature=1.0), model=model,
        objective=original_task_prompt)
    task = "Search math tools for dynamics modeling"
    task_result = "Molecular dynamics trajectories are the result of \
        molecular dynamics simulations. Trajectories are sequential \
        snapshots of simulated molecular system which represents atomic \
        coordinates at specific time periods. Based on the definition, \
        in a text format trajectory files are characterized by their \
        simplicity and uselessness. To obtain information from such files, \
        special programs and information processing techniques are applied: \
        from molecular dynamics animation to finding characteristics \
        along the trajectory (versus time). In this review, we describe \
        different programs for processing molecular dynamics trajectories. \
        The performance of these programs, usefulness for analyses of \
        molecular dynamics trajectories, strongs and weaks are discussed."

    planned_task = task_creation_agent.run(
        previous_task=task,
        task_result=task_result,
    )
    print(f"Planned task list:\n{planned_task}\n")

    assert isinstance(planned_task, list)
    task_list = ["Study the computational technology for dynamics modeling"]
    planned_task = task_creation_agent.run(
        previous_task=task,
        task_result=task_result,
        task_list=task_list,
    )
    print(f"Planned task list:\n{planned_task}\n")
    assert isinstance(planned_task, list)


@parametrize
def test_task_prioritization_agent(model: Optional[ModelType]):
    original_task_prompt = ("A high school student wants to "
                            "prove the Riemann hypothesis")

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
        model_config=ChatGPTConfig(temperature=1.0),
        model=model,
        objective=original_task_prompt,
    )

    prioritized_task = task_prioritization_agent.run(task_list=task_list)
    print(f"Prioritized task list:\n{prioritized_task}\n")
    assert isinstance(prioritized_task, list)
