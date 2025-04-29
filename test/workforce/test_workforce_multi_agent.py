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
from camel.prompts import TextPrompt
from camel.societies.workforce import Workforce
from camel.tasks import Task
from camel.types import ModelPlatformType


def test_workforce_multi_agent():
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OLLAMA,
        model_type="qwen2.5",
        url="http://localhost:11434/v1",  # Optional
        model_config_dict={"temperature": 1.0},
    )

    strict_model = ModelFactory.create(
        model_platform=ModelPlatformType.OLLAMA,
        model_type="qwen2.5",
        url="http://localhost:11434/v1",  # Optional
        model_config_dict={"temperature": 0.1},
    )

    workforce = Workforce("Break down learning objectives over a period of time",
                          coordinator_agent_kwargs={"model": strict_model},
                          task_agent_kwargs={"model": strict_model},
                          new_worker_agent_kwargs={"model": strict_model},
                          )

    workforce.add_single_agent_worker(
        "Create monthly learning plan based on learning objectives",
        worker=ChatAgent(
            system_message=TextPrompt(
                "You are a learning plan expert who creates monthly learning plans based on learning objectives"
            ),
            model=model,
        ),
    ).add_single_agent_worker(
        "Create weekly learning plan based on monthly plan",
        worker=ChatAgent(
            system_message=TextPrompt(
                "You are a learning plan expert who creates weekly learning plans based on monthly plans"
            ),
            model=model,
        ),
    ).add_single_agent_worker(
        "Create daily learning plan and schedule based on weekly plan",
        worker=ChatAgent(
            system_message=TextPrompt(
                "You are a learning plan expert who creates daily learning plans and schedules based on weekly plans"
            ),
            model=model,
        ),
    )

    task = Task(
        content="Learn Python programming in 3 months, master Python basic syntax, and be able to write Python programs",
        id="1",
    )
    task = workforce.process_task(task)

    print(task.result)
