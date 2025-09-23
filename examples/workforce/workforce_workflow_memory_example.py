#!/usr/bin/env python3
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


import os

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType
from dotenv import load_dotenv
load_dotenv()

def create_math_agent() -> ChatAgent:
    """Create a math agent with math tools."""
    math_msg = BaseMessage.make_assistant_message(
        role_name="Math Expert",
        content=(
            "You are a math expert specialized in solving mathematical problems. "
            "You can perform calculations, solve equations, and work with various "
            "mathematical concepts. Use the math tools available to you."
        ),
    )
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_5_MINI,
        model_config_dict=ChatGPTConfig().as_dict(),
    )
    return ChatAgent(
        system_message=math_msg,
        model=model,
        tools=MathToolkit().get_tools(),
    )


def create_writer_agent() -> ChatAgent:
    """Create a writer agent without tools."""
    writer_msg = BaseMessage.make_assistant_message(
        role_name="Content Writer",
        content=(
            "You are a skilled content writer who specializes in creating "
            "clear, engaging, and well-structured written content. You excel "
            "at storytelling, technical writing, and adapting your tone to "
            "different audiences."
        ),
    )
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_5_MINI,
        model_config_dict=ChatGPTConfig().as_dict(),
    )
    return ChatAgent(system_message=writer_msg, model=model)


def demonstrate_first_session():
    """Demonstrate first workforce session with workflow saving."""
    # Create workforce with two specialized agents
    workforce = Workforce("Simple Demo Team")

    # Add math agent with math tools
    math_agent = create_math_agent()
    workforce.add_single_agent_worker(
        description="math_expert",
        worker=math_agent,
    )

    # Add writer agent without tools
    writer_agent = create_writer_agent()
    workforce.add_single_agent_worker(
        description="content_writer",
        worker=writer_agent,
    )

    # Assign one task to each agent
    tasks = [
        Task(
            content="Calculate the compound interest on $1000 invested at 5% annual rate for 3 years",
            id="math_task",
        ),
        Task(
            content="Write a short creative story about a robot learning to paint",
            id="writing_task",
        ),
    ]

    for task in tasks:
        try:
            workforce.process_task(task)
        except Exception:
            pass

    # Save workflows after completing tasks
    saved_workflows = workforce.save_workflows()

    return saved_workflows


def demonstrate_second_session():
    """Demonstrate second workforce session with workflow loading."""
    # Create new workforce (simulating new session/process)
    workforce = Workforce("Simple Demo Team - Session 2")

    # Add workers with same descriptive names as before
    math_agent = create_math_agent()
    workforce.add_single_agent_worker(
        description="math_expert",  # Same description = loads matching workflow
        worker=math_agent,
    )

    writer_agent = create_writer_agent()
    workforce.add_single_agent_worker(
        description="content_writer",  # Same description = loads matching workflow
        worker=writer_agent,
    )

    # Load previous workflows
    loaded_workflows = workforce.load_workflows()

    # Process new tasks with loaded workflow context
    new_tasks = [
        Task(
            content="Calculate the area of a circle with radius 7.5 meters",
            id="new_math_task",
        ),
        Task(
            content="Write a brief technical explanation of machine learning for beginners",
            id="new_writing_task",
        ),
    ]

    for task in new_tasks:
        try:
            workforce.process_task(task)
        except Exception:
            pass

    return loaded_workflows


def demonstrate_workflow_file_management():
    """Demonstrate workflow file management and inspection."""
    # Show where workflow files are stored
    pass


def main():
    """Main demonstration function."""
    try:
        # Demonstrate first session with workflow saving
        demonstrate_first_session()

        # Demonstrate second session with workflow loading
        demonstrate_second_session()

        # Show file management information
        demonstrate_workflow_file_management()

    except Exception as e:
        print(e)
        pass


if __name__ == "__main__":
    main()
