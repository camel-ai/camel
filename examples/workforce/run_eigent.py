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

# Import agent factories from eigent.py
from eigent import (
    # developer_agent_factory,
    # document_agent_factory,
    # multi_modal_agent_factory,
    search_agent_factory,
)

from camel.agents.chat_agent import ChatAgent
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import (
    AgentCommunicationToolkit,
    HumanToolkit,
)
from camel.types import ModelPlatformType, ModelType

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
    # message_integration = ToolkitMessageIntegration(
    #     message_handler=send_message_to_user
    # )

    # Create a single model backend for all agents
    model_backend = ModelFactory.create(
        model_platform=ModelPlatformType.MOONSHOT,
        model_type=ModelType.MOONSHOT_KIMI_K2,
        url="https://api.moonshot.ai/v1",  # Explicitly specify Moonshot API URL
        model_config_dict={
            "stream": False,
        },
    )
    # model_backend = ModelFactory.create(
    #     model_platform=ModelPlatformType.MOONSHOT,
    #     model_type=ModelType.MOONSHOT_KIMI_K2,
    #     url="https://api.moonshot.ai/v1",  # Explicitly specify Moonshot API URL
    #     model_config_dict={
    #         "stream": False,
    #     },
    # )
    model_backend_reason = ModelFactory.create(
        model_platform=ModelPlatformType.MOONSHOT,
        model_type=ModelType.MOONSHOT_KIMI_K2,
        url="https://api.moonshot.ai/v1",  # Explicitly specify Moonshot API URL
        model_config_dict={
            "stream": False,
        },
    )
    # model_backend_reason = ModelFactory.create(
    #     model_platform=ModelPlatformType.GEMINI,
    #     model_type=ModelType.GEMINI_2_5_PRO,
    #     # url="https://api.moonshot.ai/v1",  # Explicitly specify Moonshot API URL
    #     model_config_dict={
    #         "stream": False,
    #     },
    # )

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
        enable_tool_output_cache=True,
        model=model_backend_reason,
        tools=[
            # *NoteTakingToolkit(
            #     working_directory=WORKING_DIRECTORY
            # ).get_tools(),
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
            # *NoteTakingToolkit(
            #     working_directory=WORKING_DIRECTORY
            # ).get_tools(),
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
            # *message_integration.register_toolkits(
            #     NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
            # ).get_tools(),
        ],
    )

    # Create agents using factory functions
    # search_agent_factory now returns (agent, browser_toolkit) tuple
    search_agent, browser_toolkit = search_agent_factory(
        model_backend, task_id
    )

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
        use_structured_output_handler=True,  # Use handler for Moonshot compatibility
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

    try:
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
            "log_file": log_file_path,
            "browser_toolkit": browser_toolkit,  # Return for cleanup
        }
    finally:
        # Always close browser to avoid profile directory lock
        if browser_toolkit:
            try:
                print("\n--- Closing browser to avoid profile lock ---")
                await browser_toolkit.browser_close()
                print("Browser closed successfully")
            except Exception as e:
                print(f"Warning: Failed to close browser: {e}")


async def run_loop(num_iterations: int = 3):
    """
    Run the workforce multiple times in a loop.
    This uses a single event loop to avoid hanging issues.
    Browser is automatically closed after each iteration to avoid profile lock.

    Args:
        human_task: The task to execute
        num_iterations: Number of times to run (use a large number like 999999 for "infinite")
    """
    try:
        for i in range(num_iterations):
            # names = ["Lordsorl M", "Lordsorl L", "Lordsorl K", "Lordsorl J", "Lordsorl I"]
            # emails = ["Lordsorl.m@globalmedia.com", "Lordsorl.l@globalmedia.com", "Lordsorl.k@globalmedia.com", "Lordsorl.j@globalmedia.com", "Lordsorl.i@globalmedia.com"]

            # names = ["Mack M", "Mack L", "Mack K", "Mack J", "Mack I"]
            # emails = ["Mack.m@globalmedia.com", "Mack.l@globalmedia.com", "Mack.k@globalmedia.com", "Mack.j@globalmedia.com", "Mack.i@globalmedia.com"]
            # phones = ["(415) 566-0123", "(415) 566-0124", "(415) 566-0125", "(415) 566-0126", "(415) 566-0127"]
            # addresses = ["229 Lordsorl Lane, London, England, SE22 8JF", "230 Lordsorl Lane, London, England, SE22 8JF", "231 Lordsorl Lane, London, England, SE22 8JF", "232 Lordsorl Lane, London, England, SE22 8JF", "233 Lordsorl Lane, London, England, SE22 8JF"]
            human_task = Task(
                content=(
                    """
        不要拆分任务
        要先用browser_open打开浏览器，browser_visit这个链接
        login https://energy-inspiration-9021.lightning.force.com/lightning/page/home

        user account weijie.bai-lqzb@force.com
        password wodeSalesforce@1998

The salesforce.com - 200 Widgets deal is progressing well. Move it from 'Needs Analysis' to 'Proposal' stage, and click “Mark as Current Stage’ and go  click "Contact Roles" and give me the contact name and Phone number. Back to Opportunities page edit this Next Step as “book a meeting with + the contact name and phone number.”
        如果type失败可能是因为ref发生了变化，你需要查看browser_get_page_snapshot
                    """
                ),
                id='0',
            )

            print(f"\n{'='*60}")
            print(f"Starting iteration {i+1}/{num_iterations}")
            print(f"{'='*60}\n")

            result = await run_eigent_workforce(human_task)

            print(f"\n=== Iteration {i+1} Complete ===")
            print(f"Log file saved to: {result['log_file']}")

            # Wait for browser process to fully terminate before next iteration
            if i < num_iterations - 1:  # Don't wait after last iteration
                print("Waiting 2 seconds for browser cleanup...")
                await asyncio.sleep(2)

    except KeyboardInterrupt:
        print("\n\n⚠️  Loop interrupted by user (Ctrl+C)")
        print("Exiting gracefully...")
    except Exception as e:
        print(f"\n\n❌ Error occurred: {e}")
        raise


# Example usage
if __name__ == "__main__":
    # Create a custom task

    # Run the workforce in a loop (press Ctrl+C to stop)
    # Uses a single event loop to avoid hanging
    asyncio.run(run_loop(num_iterations=5))
