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


import asyncio
import os

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

load_dotenv()

logger = get_logger(__name__)


def create_math_agent() -> ChatAgent:
    r"""Create a math agent with math tools.

    Returns:
        ChatAgent: A configured math expert agent with MathToolkit tools.
    """
    math_msg = BaseMessage.make_assistant_message(
        role_name="Math Expert",
        content=(
            "You are a math expert specialized in solving "
            "mathematical problems.You can perform calculations, "
            "solve equations, and work with various "
            "mathematical concepts. Use the math tools available to you."
        ),
    )
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.DEFAULT,
        model_config_dict=ChatGPTConfig().as_dict(),
    )
    return ChatAgent(
        system_message=math_msg,
        model=model,
        tools=MathToolkit().get_tools(),
    )


def create_writer_agent() -> ChatAgent:
    r"""Create a writer agent without tools.

    Returns:
        ChatAgent: A configured content writer agent without additional tools.
    """
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
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict=ChatGPTConfig().as_dict(),
    )
    return ChatAgent(system_message=writer_msg, model=model)


async def demonstrate_first_session():
    r"""Demonstrate first workforce session with workflow saving.

    Creates a workforce with math and writer agents, processes tasks,
    and saves the resulting workflows for future use using async parallel
    summarization.

    Returns:
        Dict[str, str]: Results of the workflow saving operation.
    """
    # Create workforce with two specialized agents
    workforce = Workforce("Simple Demo Team")

    # Add math agent with math tools
    math_agent = create_math_agent()
    workforce.add_single_agent_worker(
        description="math_expert",
        worker=math_agent,
        enable_workflow_memory=True,  # Enable to save workflows later
    )

    # Add writer agent without tools
    writer_agent = create_writer_agent()
    workforce.add_single_agent_worker(
        description="content_writer",
        worker=writer_agent,
        enable_workflow_memory=True,  # Enable to save workflows later
    )

    # Assign one task to each agent
    tasks = [
        Task(
            content="Calculate the compound interest on $1000 invested at 5% "
            "annual rate for 3 years",
            id="math_task",
        ),
        Task(
            content="Write a one-paragraph creative story about a robot "
            "learning to paint",
            id="writing_task",
        ),
    ]

    for task in tasks:
        try:
            await workforce.process_task_async(task)
        except Exception as e:
            logger.warning(f"Failed to process task {task.id}: {e}")

    # Save workflows after completing tasks using async parallel version
    saved_workflows = await workforce.save_workflow_memories_async()

    return saved_workflows


async def demonstrate_second_session():
    r"""Demonstrate second workforce session with workflow loading.

    Creates a new workforce instance, loads previously saved workflows,
    and processes new tasks with the loaded workflow context.

    Returns:
        Dict[str, bool]: Results of the workflow loading operation.
    """
    # Create new workforce (simulating new session/process)
    workforce = Workforce("Simple Demo Team - Session 2")

    # Add workers with same descriptive names as before
    math_agent = create_math_agent()
    workforce.add_single_agent_worker(
        description="math_expert",  # Same description = loads matching
        # workflow
        worker=math_agent,
        enable_workflow_memory=False,  # Not saving in this session
    )

    writer_agent = create_writer_agent()
    workforce.add_single_agent_worker(
        description="content_writer",  # Same description = loads
        # matching workflow
        worker=writer_agent,
        enable_workflow_memory=False,  # Not saving in this session
    )

    # Load previous workflows
    loaded_workflows = workforce.load_workflow_memories()

    # Process new tasks with loaded workflow context
    new_tasks = [
        Task(
            content="Calculate the area of a circle with radius 7.5 meters",
            id="new_math_task",
        ),
        Task(
            content="Write a brief technical explanation of machine "
            "learning for beginners",
            id="new_writing_task",
        ),
    ]

    for task in new_tasks:
        try:
            await workforce.process_task_async(task)
        except Exception as e:
            logger.warning(f"Failed to process task {task.id}: {e}")

    return loaded_workflows


def demonstrate_workflow_file_management() -> None:
    r"""Demonstrate workflow file management and inspection.

    Shows information about where workflow files are stored and how
    to inspect the saved workflow data.
    """

    # Get the base directory for workforce workflows
    camel_workdir = os.environ.get("CAMEL_WORKDIR")
    if camel_workdir:
        base_dir = os.path.join(camel_workdir, "workforce_workflows")
    else:
        base_dir = "workforce_workflows"

    logger.info(f"Workforce workflows are stored in: {base_dir}")

    # Show how to check for existing workflow files
    if os.path.exists(base_dir):
        session_dirs = [
            d
            for d in os.listdir(base_dir)
            if os.path.isdir(os.path.join(base_dir, d))
        ]
        logger.info(f"Found {len(session_dirs)} session directories")

        for session_dir in session_dirs[:3]:  # Show first 3 sessions
            session_path = os.path.join(base_dir, session_dir)
            workflow_files = [
                f for f in os.listdir(session_path) if f.endswith('.md')
            ]
            logger.info(
                f"Session {session_dir}: {len(workflow_files)} workflow files"
            )
    else:
        logger.info("No workflow directory found yet")


async def main() -> None:
    try:
        # First session to execute tasks and save workflows
        saved_results = await demonstrate_first_session()
        print(f"Workflow save results: {saved_results}")

        # Second session to load workflows and execute new tasks
        loaded_results = await demonstrate_second_session()
        print(f"Workflow load results: {loaded_results}")

    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

"""
===============================================================================
Workflows saved: 
workforce_workflows/session_20250925_150330_302341/content_writer_workflow.md
workforce_workflows/session_20250925_150330_302341/math_expert_workflow.md

Saved workflow in math_expert_workflow.md
<MARKDOWN CONTENT>
## Metadata

- session_id: session_20250925_150330_302341
- working_directory: .../camel/workforce_workflows/
  session_20250925_150330_302341
- created_at: ...
- base_directory: .../Codebase/camel/workforce_workflows
- agent_id: 687b2e57-11ce-4138-9990-4d5ab58d2acc
- message_count: 3

## WorkflowSummary

### Task Title
Calculate compound interest

### Task Description
Calculate the future value of $1000 at 5% annual interest compounded
once per year for 3 years, and produce a plain-text result containing:
the compound interest formula with symbol definitions and numeric
substitution, balances at end of Years 1-3, the final amount,
total interest earned (all rounded to 2 decimals), and a final
one-line JSON object with numeric values to two decimals.


### Tools
[Bullet point list of tools used]

### Steps
1. Identify the required formula: A = P*(1 + r)^n.
2. Substitute given values into the formula: P = 1000, r = 0.05, n = 3.
3. Compute the sum inside parentheses: calculate 1 + r = 1.05.
4. Compute the exponentiation: calculate 1.05^3 = 1.157625.
5. Multiply by principal: compute A = 1000 * 1.157625 = 1157.625 (unrounded).
6. Compute total interest unrounded: Interest = A - P = 
   1157.625 - 1000 = 157.625.
7. Round results to 2 decimals and format as USD: A → $1157.63;
   Interest → $157.63.
8. Return deliverables: formula, each arithmetic step with numbers substituted,
   unrounded A, rounded A in USD, and rounded interest in USD.

### Failure And Recovery Strategies
(No failure and recovery strategies recorded)

### Notes And Observations
No errors encountered.
</MARKDOWN CONTENT>

System message of math agent after loading workflow:
You are a math expert specialized in solving mathematical problems. 
You can perform calculations, solve equations, and work with various
mathematical concepts. 
Use the math tools available to you.

--- Workflow Memory ---
The following is the context from a previous session or workflow which might be
useful for to the current task. This information might help you understand the
background, choose which tools to use, and plan your next steps.

## WorkflowSummary
[The Workflow Summary from the above]
"""
