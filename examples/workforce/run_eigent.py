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
import datetime
import os
import platform
import uuid

from camel.agents.chat_agent import ChatAgent
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import (
    AgentCommunicationToolkit,
    HumanToolkit,
    NoteTakingToolkit,
    ToolkitMessageIntegration,
)
from camel.types import ModelPlatformType, ModelType

# Import agent factories from eigent.py
from eigent import (
    # developer_agent_factory,
    # document_agent_factory,
    # multi_modal_agent_factory,
    search_agent_factory,
    send_message_to_user,
)

logger = get_logger(__name__)

WORKING_DIRECTORY = os.environ.get("CAMEL_WORKDIR") or os.path.abspath(
    "working_dir/"
)


async def run_eigent_workforce(human_task: Task):
    """
    Run the eigent workforce with a custom task.

    Args:
        human_task (Task): The task to be processed by the workforce.

    Returns:
        dict: A dictionary containing workforce KPIs and log information.
    """
    # Ensure working directory exists
    os.makedirs(WORKING_DIRECTORY, exist_ok=True)

    # Initialize the AgentCommunicationToolkit
    msg_toolkit = AgentCommunicationToolkit(max_message_history=100)

    # Initialize message integration for use in coordinator and task agents
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Create a single model backend for all agents
    model_backend = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1,
        model_config_dict={
            "stream": False,
        },
    )

    model_backend_reason = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1,
        model_config_dict={
            "stream": False,
        },
    )

    task_id = 'workforce_task'

    # Create custom agents for the workforce
    coordinator_agent = ChatAgent(
        system_message=(
            f""""
You are a helpful coordinator.
- You are now working in system {platform.system()} with architecture
{platform.machine()} at working directory `{WORKING_DIRECTORY}`. All local
file operations must occur here, but you can access files from any place in
the file system. For all file system operations, you MUST use absolute paths
to ensure precision and avoid ambiguity.
The current date is {datetime.date.today()}. For any date-related tasks, you
MUST use this as the current date.

- If a task assigned to another agent fails, you should re-assign it to the
`Developer_Agent`. The `Developer_Agent` is a powerful agent with terminal
access and can resolve a wide range of issues.
            """
        ),
        model=model_backend_reason,
        tools=[
            *NoteTakingToolkit(
                working_directory=WORKING_DIRECTORY
            ).get_tools(),
        ],
    )
    task_agent = ChatAgent(
        f"""

You are a helpful task planner.
- You are now working in system {platform.system()} with architecture
{platform.machine()} at working directory `{WORKING_DIRECTORY}`. All local
file operations must occur here, but you can access files from any place in
the file system. For all file system operations, you MUST use absolute paths
to ensure precision and avoid ambiguity.
The current date is {datetime.date.today()}. For any date-related tasks, you
MUST use this as the current date.
        """,
        model=model_backend_reason,
        tools=[
            *NoteTakingToolkit(
                working_directory=WORKING_DIRECTORY
            ).get_tools(),
        ],
    )
    new_worker_agent = ChatAgent(
        f"You are a helpful worker. When you complete your task, your "
        "final response "
        f"must be a comprehensive summary of your work, presented in a clear, "
        f"detailed, and easy-to-read format. Avoid using markdown tables for "
        f"presenting data; use plain text formatting instead. You are now "
        f"working in "
        f"`{WORKING_DIRECTORY}` All local file operations must occur here, "
        f"but you can access files from any place in the file system. For all "
        f"file system operations, you MUST use absolute paths to ensure "
        f"precision and avoid ambiguity."
        "directory. You can also communicate with other agents "
        "using messaging tools - use `list_available_agents` to see "
        "available team members and `send_message` to coordinate work "
        "and ask for help when needed. "
        "### Note-Taking: You have access to comprehensive note-taking tools "
        "for documenting work progress and collaborating with team members. "
        "Use create_note, append_note, read_note, and list_note to track "
        "your work, share findings, and access information from other agents. "
        "Create notes for work progress, discoveries, and collaboration "
        "points.",
        model=model_backend,
        tools=[
            HumanToolkit().ask_human_via_console,
            *message_integration.register_toolkits(
                NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
            ).get_tools(),
        ],
    )

    # Create agents using factory functions
    search_agent = search_agent_factory(model_backend, task_id)

    # document_agent = document_agent_factory(
    #     model_backend_reason,
    #     task_id,
    # )
    # multi_modal_agent = multi_modal_agent_factory(model_backend, task_id)

    # Register all agents with the communication toolkit
    msg_toolkit.register_agent("Worker", new_worker_agent)
    msg_toolkit.register_agent("Search_Agent", search_agent)
    # msg_toolkit.register_agent("Developer_Agent", developer_agent)
    # msg_toolkit.register_agent("Document_Agent", document_agent)
    # msg_toolkit.register_agent("Multi_Modal_Agent", multi_modal_agent)

    # Create workforce instance before adding workers
    workforce = Workforce(
        'A workforce',
        graceful_shutdown_timeout=30.0,  # 30 seconds for debugging
        share_memory=False,
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        new_worker_agent=new_worker_agent,
        use_structured_output_handler=False,
        task_timeout_seconds=900.0,
    )

    workforce.add_single_agent_worker(
        "Search Agent: An expert web researcher that can browse websites, "
        "perform searches, and extract information to support other agents.",
        worker=search_agent,
    # ).add_single_agent_worker(
    #     "Developer Agent: A master-level coding assistant with a powerful "
    #     "terminal. It can write and execute code, manage files, automate "
    #     "desktop tasks, and deploy web applications to solve complex "
    #     "technical challenges.",
    #     worker=developer_agent,
    # ).add_single_agent_worker(
    #     "Document Agent: A document processing assistant skilled in creating "
    #     "and modifying a wide range of file formats. It can generate "
    #     "text-based files (Markdown, JSON, YAML, HTML), office documents "
    #     "(Word, PDF), presentations (PowerPoint), and data files "
    #     "(Excel, CSV).",
    #     worker=document_agent,
    )

    # Use the async version directly to avoid hanging with async tools
    await workforce.process_task_async(human_task)

    # Test WorkforceLogger features
    print("\n--- Workforce Log Tree ---")
    print(workforce.get_workforce_log_tree())

    print("\n--- Workforce KPIs ---")
    kpis = workforce.get_workforce_kpis()
    for key, value in kpis.items():
        print(f"{key}: {value}")

    log_file_path = f"eigent_logs_{human_task.id}.json"
    print(f"\n--- Dumping Workforce Logs to {log_file_path} ---")
    workforce.dump_workforce_logs(log_file_path)
    print(f"Logs dumped. Please check the file: {log_file_path}")

    return {
        "kpis": kpis,
        "log_tree": workforce.get_workforce_log_tree(),
        "log_file": log_file_path
    }


# Example usage
if __name__ == "__main__":
    # Create a custom task
    human_task = Task(
        content=(
            """
            不要拆分任务！所有任务由一个search agent完成
            
            用浏览器打开https://my426318.s4hana.cloud.sap/ui?sap-language=EN&help-mixedLanguages=false&help-autoStartTour=PR_28A0E50CC77DAF91#Shell-home，这是sap平台，帮我执行下面的任务：
  点击 'Procurement'
        然后
        点击 'Manage Purchase Orders'
        you click 'create' button
        在'Purchasing Doc. Type:'中
        选中输入Standard PO (NB)
        在'Currency'输入
        United States Dollar (USD)
        在'Purchasing Group:'中
        输入Group 001 (001)
        在 'Company Code:'中输入
        Velotics Inc. (1710)
        在 'Purchasing Organization:'输入
        Purch. Org. 1710 (1710)
	
	Supplier是AdvertOne (USSU-TRL03)
然后在items表中点击add from document, 点击Go button 后, 在purchase order checkbox中点击第一个，然后点击add items确认
        然后点击order即可
注意：如果遇到leave tour按钮，那么先点击这个按钮
注意：如果多个输入框在同一个页面你都看到了，那么就用browser_type([{ref:...,text:...},{ref,text}...])这样一次输入多个输入框
            """
        ),
        id='0',
    )

    # Run the workforce
    result = asyncio.run(run_eigent_workforce(human_task))

    print("\n=== Execution Complete ===")
    print(f"Log file saved to: {result['log_file']}")
