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
import json
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
    # NoteTakingToolkit,
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


def load_tasks_from_jsonl(jsonl_path: str, start_index: int = 0, end_index: int = None):
    """
    Load tasks from a JSONL file.

    Args:
        jsonl_path (str): Path to the JSONL file.
        start_index (int): Starting index (inclusive).
        end_index (int): Ending index (inclusive). If None, load all tasks from start_index.

    Returns:
        list: A list of task dictionaries.
    """
    tasks = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < start_index:
                continue
            if end_index is not None and i > end_index:
                break
            tasks.append(json.loads(line.strip()))
    return tasks


async def verify_result_with_agent(task_content: str, result: dict, model_backend: BaseModelBackend):
    """
    Verify the workforce result using a chat agent.

    Args:
        task_content (str): The original task content.
        result (dict): The result from the workforce.
        model_backend (BaseModelBackend): The model backend to use.

    Returns:
        dict: A dictionary with 'success' (bool) and 'reasoning' (str).
    """
    verifier_agent = ChatAgent(
        system_message=(
            "You are a task verification expert. Your job is to analyze whether "
            "a task was completed successfully based on the task description and "
            "the execution result. You should output your verification in JSON format "
            "with two fields: 'success' (true/false) and 'reasoning' (explanation)."
        ),
        model=model_backend,
    )

    verification_prompt = f"""
Task Description:
{task_content}

Execution Result:
{json.dumps(result, indent=2)}

Please verify if the task was completed successfully. Consider:
1. Did the workforce complete the task objectives?
2. Are there any errors or failures in the logs?
3. Does the result align with the task requirements?

Output your verification in JSON format:
{{
    "success": true/false,
    "reasoning": "your explanation here"
}}
"""

    response = verifier_agent.step(BaseMessage.make_user_message(
        role_name="Verifier",
        content=verification_prompt
    ))

    try:
        # Try to parse JSON from the response
        content = response.msg.content
        # Find JSON in the content
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = content[start_idx:end_idx]
            verification_result = json.loads(json_str)
        else:
            # Fallback if no JSON found
            verification_result = {
                "success": False,
                "reasoning": "Failed to parse verification response"
            }
    except Exception as e:
        verification_result = {
            "success": False,
            "reasoning": f"Error parsing verification: {str(e)}"
        }

    return verification_result


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
    import argparse

    parser = argparse.ArgumentParser(description='Run eigent workforce on WebVoyager tasks')
    parser.add_argument('--start', type=int, default=0, help='Start index (inclusive)')
    parser.add_argument('--end', type=int, default=None, help='End index (inclusive)')
    parser.add_argument('--jsonl', type=str, default='/Users/puzhen/Downloads/WebVoyager_data.jsonl',
                        help='Path to JSONL file')
    args = parser.parse_args()

    # Load tasks from JSONL file
    tasks = load_tasks_from_jsonl(args.jsonl, args.start, args.end)
    print(f"Loaded {len(tasks)} tasks (index {args.start} to {args.end if args.end else 'end'})")

    # Create model backend for verification
    verifier_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1,
        model_config_dict={
            "stream": False,
        },
    )

    # Store all results
    all_results = []

    async def process_all_tasks():
        for idx, task_data in enumerate(tasks):
            actual_idx = args.start + idx
            print(f"\n{'='*80}")
            print(f"Processing Task {actual_idx}: {task_data.get('id', 'unknown')}")
            print(f"{'='*80}")

            # Combine ques and web fields
            task_content = f"{task_data['ques']} in \"{task_data['web']}\""

            # Create a custom task
            human_task = Task(
                content=task_content,
                id=task_data.get('id', str(actual_idx)),
            )

            try:
                # Run the workforce
                result = await run_eigent_workforce(human_task)

                print("\n--- Verifying Result with Agent ---")
                # Verify the result
                verification = await verify_result_with_agent(task_content, result, verifier_model)

                print(f"\nVerification Result:")
                print(f"  Success: {verification['success']}")
                print(f"  Reasoning: {verification['reasoning']}")

                # Store complete result
                task_result = {
                    "task_index": actual_idx,
                    "task_id": task_data.get('id', str(actual_idx)),
                    "task_content": task_content,
                    "workforce_result": result,
                    "verification": verification
                }
                all_results.append(task_result)

                # Save intermediate results
                results_file = f"all_results_{args.start}_{args.end if args.end else 'end'}.json"
                with open(results_file, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, indent=2, ensure_ascii=False)

                print(f"\n=== Task {actual_idx} Complete ===")
                print(f"Log file saved to: {result['log_file']}")
                print(f"Results saved to: {results_file}")

            except Exception as e:
                print(f"\n!!! Error processing task {actual_idx}: {str(e)}")
                error_result = {
                    "task_index": actual_idx,
                    "task_id": task_data.get('id', str(actual_idx)),
                    "task_content": task_content,
                    "error": str(e),
                    "verification": {
                        "success": False,
                        "reasoning": f"Exception occurred: {str(e)}"
                    }
                }
                all_results.append(error_result)

    # Run all tasks
    asyncio.run(process_all_tasks())

    print(f"\n{'='*80}")
    print("=== All Tasks Complete ===")
    print(f"{'='*80}")
    print(f"Processed {len(tasks)} tasks")
    print(f"Results saved to: all_results_{args.start}_{args.end if args.end else 'end'}.json")
