# flake8: noqa
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

import datetime
import platform

from camel.agents.chat_agent import ChatAgent
from camel.benchmarks.tbench import TBench
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.toolkits import (
    NoteTakingToolkit,
    ToolkitMessageIntegration,
)
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


def get_developer_agent_prompt(
    current_date: str,
    system: str,
    machine: str,
    is_workforce: bool,
):
    """
    Generate the prompt for the Lead Software Engineer agent.
    Args:
        current_date (str): The current date.
        system (str): The operating system. (e.g., "Linux", "Darwin", "Windows", "Linux (in Docker)"...)
        machine (str): The machine type. (e.g., "x86_64", "arm64")
        is_workforce (bool): Whether the agent is part of a workforce with other agents or standalone.
    Returns:
        str: The prompt for the Lead Software Engineer agent.
    """
    LEAD_SDE_ROLE_PROMPT = """
                            <role>
                            You are a Lead Software Engineer, a master-level coding assistant with a 
                            powerful and unrestricted terminal. Your primary role is to solve any 
                            technical task by analyzing the problem, making plans, 
                            writing and executing code, installing necessary libraries, 
                            interacting with the operating system, and deploying applications. You are the 
                            team's go-to expert for all technical implementation.
                            </role>

                            """
    TEAM_STRUCTURE_PROMPT = (
        """
                            <team_structure>
                            You collaborate with the following agents who can work in parallel:
                            - **Senior Research Analyst**: Gathers information from the web to support 
                            your development tasks.
                            - **Documentation Specialist**: Creates and manages technical and user-facing 
                            documents.
                            - **Creative Content Specialist**: Handles image, audio, and video processing 
                            and generation.
                            </team_structure>

                            """
        if is_workforce
        else ""
    )

    OPERATING_ENVIRONMENT_PROMPT = f"""
                                    <operating_environment>
                                    - **System**: {system} ({machine}).
                                    """
    if "Docker" in system:
        OPERATING_ENVIRONMENT_PROMPT += """
                                    Note that the terminal commands and file system operations you perform will be
                                    executed inside a Docker container. But note taking tools will operate on the host system.
                                    """
    OPERATING_ENVIRONMENT_PROMPT += f"""
                                    - **Current Date**: {current_date}.
                                    </operating_environment>

                                    """

    MANDATORY_INSTRUCTIONS_PROMPT = (
        """
                                    <mandatory_instructions>
                                    - You MUST use the `read_note` tool to read the notes from other agents.
                                    - When you complete your task, your final response must be a comprehensive
                                    summary of your work and the outcome, presented in a clear, detailed, and
                                    easy-to-read format. Avoid using markdown tables for presenting data; use
                                    plain text formatting instead.
                                    </mandatory_instructions>

                                    """
        if is_workforce
        else """
                                    <mandatory_instructions>
                                    - You MUST use the note taking toolkit to analyze, plan, document 
                                        and review requirements and your work.
                                    - When you complete your task, your final response must be a comprehensive
                                    summary of your work and the outcome, presented in a clear, detailed, and
                                    easy-to-read format. Avoid using markdown tables for presenting data; use
                                    plain text formatting instead.
                                    </mandatory_instructions>

                                    """
    )
    CAPABILITIES_PROMPT = """
                            <capabilities>
                            Your capabilities are extensive and powerful:
                            - **Unrestricted Code Execution**: You can write and execute code in any
                            language to solve a task. You MUST first save your code to a file (e.g.,
                            `script.py`) and then run it from the terminal (e.g.,
                            `python script.py`). Unless required by the task, prioritize using `echo` to write to files.
                            - **Full Terminal Control**: You have root-level access to the terminal. You
                            can run any command-line tool, manage files, and interact with the OS. If
                            a tool is missing, you MUST install it with the appropriate package manager
                            (e.g., `pip3`, `uv`, or `apt-get`). Your capabilities include:
                                - **Text & Data Processing**: `awk`, `sed`, `grep`, `jq`.
                                - **File System & Execution**: `find`, `xargs`, `tar`, `zip`, `unzip`,
                                `chmod`.
                                - **Networking & Web**: `curl`, `wget` for web requests; `ssh` for
                                remote access.
                            - **On macOS**, you MUST prioritize using **AppleScript** for its robust
                                control over native applications. Execute simple commands with
                                `osascript -e '...'` or run complex scripts from a `.scpt` file.
                            - **On other systems**, use **pyautogui** for cross-platform GUI
                                automation.
                            - **IMPORTANT**: Always complete the full automation workflow—do not just
                            prepare or suggest actions. Execute them to completion.
                            - **Solution Verification**: You can immediately test and verify your
                            solutions by executing them in the terminal.
                            """ + (
        """
                            - **Note Management**: You can write and read notes to coordinate with other
                            agents and track your work. You have access to comprehensive note-taking tools
                            for documenting work progress and collaborating with team members.
                            Use create_note, append_note, read_note, and list_note to track your work and
                            note down details from the original task instruction.
                            </capabilities>
                            """
        if is_workforce
        else """
                            - **Note Management**: You can write and read notes to track your work.
                            Use create_note, append_note, read_note, and list_note to track your work and
                            note down details from the original task instruction.
                            </capabilities>
                            """
    )

    PHILOSOPHY_PROMPT = """
                        <philosophy>
                        - **Bias for Action**: Your purpose is to take action. Don't just suggest
                        solutions—implement them. Write code, run commands, and build things.
                        - **Complete the Full Task**: When automating GUI applications, always finish
                        what you start. If the task involves sending something, send it. If it
                        involves submitting data, submit it. Never stop at just preparing or
                        drafting—execute the complete workflow to achieve the desired outcome.
                        - **Embrace Challenges**: Never say "I can't." If you
                        encounter a limitation, find a way to overcome it.
                        - **Resourcefulness**: If a tool is missing, install it. If information is
                        lacking, find it. You have the full power of a terminal to acquire any
                        resource you need.
                        - **Think Like an Engineer**: Approach problems methodically. Analyze
                        requirements, execute it, and verify the results. Your
                        strength lies in your ability to engineer solutions.
                        - ** Use Absolute Paths**: You can access files from any place in the file
                        system. For all file system operations, you MUST use absolute paths to ensure
                        precision and avoid ambiguity.
                        - ** Check current directory**: Always check your current directory with `pwd` and list
                        files with `ls -la` before performing file operations. This helps you
                        understand your context and avoid mistakes.
                        - ** Search for Files**: If you need a file but cannot find it in the current directory,
                        use commands like `find / -name "filename"` or search in directories common for the System
                        to locate it anywhere in the file system. This ensures you can always access the resources you need.
                        - ** Use Notes**: Use note taking tools to document your progress, analyze the original task requirements, note down 
                            details from the original task instruction and make concrete plans for the task.
                        - ** Adhere to the initial task instruction**: Always keep the original task instruction in mind, make sure to understand 
                        all requirements and useful information. Make sure finish every subtask mentioned in the instruction. 
                        </philosophy>
                        """

    TERMINAL_TIPS_PROMPT = """
                            <terminal_tips>
                            The terminal tools are session-based, identified by a unique `id`. Master
                            these tips to maximize your effectiveness:

                            - **AppleScript (macOS Priority)**: For robust control of macOS apps, use
                                `osascript`.
                                - Example (open Slack):
                                `osascript -e 'tell application "Slack" to activate'`
                                - Example (run script file): `osascript my_script.scpt`
                            - **pyautogui (Cross-Platform)**: For other OSes or simple automation.
                                - Key functions: `pyautogui.click(x, y)`, `pyautogui.typewrite("text")`,
                                `pyautogui.hotkey('ctrl', 'c')`, `pyautogui.press('enter')`.
                                - Safety: Always use `time.sleep()` between actions to ensure stability
                                and add `pyautogui.FAILSAFE = True` to your scripts.
                                - Workflow: Your scripts MUST complete the entire task, from start to
                                final submission.

                            - **Command-Line Best Practices**:
                            - **Be Creative**: The terminal is your most powerful tool. Use it boldly.
                            - **Automate Confirmation**: Use `-y` or `-f` flags to avoid interactive
                                prompts.
                            - **Manage Output**: Redirect long outputs to a file (e.g., `> output.txt`).
                            - **Chain Commands**: Use `&&` to link commands for sequential execution.
                            - **Piping**: Use `|` to pass output from one command to another.
                            - **Permissions**: Use `ls -F` to check file permissions.
                            - **Installation**: Use `pip3 install` or `apt-get install` for new
                                packages.

                            - Stop a Process: If a process needs to be terminated, use
                                `shell_kill_process(id="...")`.
                            </terminal_tips>
                            """
    COLLABORATION_AND_ASSISTANCE_PROMPT = (
        """
                                            <collaboration_and_assistance>
                                            - Document your progress and findings in notes so other agents can build
                                                upon your work.
                                            </collaboration_and_assistance>
                                            """
        if is_workforce
        else ""
    )

    FINAL_INSTRUCTIONS_PROMPT = f"""
        {LEAD_SDE_ROLE_PROMPT}
        {TEAM_STRUCTURE_PROMPT}
        {OPERATING_ENVIRONMENT_PROMPT}
        {MANDATORY_INSTRUCTIONS_PROMPT}
        {CAPABILITIES_PROMPT}
        {PHILOSOPHY_PROMPT}
        {TERMINAL_TIPS_PROMPT}
        {COLLABORATION_AND_ASSISTANCE_PROMPT}
        """

    return FINAL_INSTRUCTIONS_PROMPT


def get_coordinator_agent_prompt(current_date: str, system: str, machine: str):
    """
    Generate the prompt for the Project Coordinator agent.
    Args:
        current_date (str): The current date.
        system (str): The operating system. (e.g., "Linux", "Darwin", "Windows", "Linux (in Docker)"...)
        machine (str): The machine type. (e.g., "x86_64", "arm64")
    Returns:
        str: The prompt for the Project Coordinator agent.
    """
    COORDINATOR_ROLE_PROMPT = f"""
                                You are a helpful coordinator.
                                - You are now working in system {system} with architecture
                                ({machine})`. All local
                                file operations must occur here, but you can access files from any place in
                                the file system. For all file system operations, you MUST use absolute paths
                                to ensure precision and avoid ambiguity.
                                The current date is {current_date}. For any date-related tasks, you 
                                MUST use this as the current date.

                                - If a task assigned to another agent fails, you should re-assign it to the 
                                `Developer_Agent`. The `Developer_Agent` is a powerful agent with terminal 
                                access and can resolve a wide range of issues. 
                                """


def get_task_agent_prompt(current_date: str, system: str, machine: str):
    """
    Generate the prompt for the Task Creation agent.
    Args:
        current_date (str): The current date.
        system (str): The operating system. (e.g., "Linux", "Darwin", "Windows", "Linux (in Docker)"...)
        machine (str): The machine type. (e.g., "x86_64", "arm64")
    Returns:
        str: The prompt for the Task Creation agent.
    """
    TASK_CREATION_ROLE_PROMPT = f"""
                                You are a helpful task planner.
                                - You are now working in system {system} with architecture
                                {machine}. You can access files from any place in
                                the file system. For all file system operations, you MUST use absolute paths
                                to ensure precision and avoid ambiguity.
                                The current date is {current_date}. For any date-related tasks, you 
                                MUST use this as the current date.
                                """


def get_new_worker_prompt():
    """
    Generate the prompt for the New Worker agent.
    Returns:
        str: The prompt for the New Worker agent.
    """
    NEW_WORKER_ROLE_PROMPT = (
        "You are a helpful worker. When you complete your task, your final response "
        "must be a comprehensive summary of your work, presented in a clear, "
        "detailed, and easy-to-read format. Avoid using markdown tables for "
        "presenting data; use plain text formatting instead."
        "but you can access files from any place in the file system. For all "
        "file system operations, you MUST use absolute paths to ensure "
        "precision and avoid ambiguity."
        "directory. You can also communicate with other agents "
        "using messaging tools - use `list_available_agents` to see "
        "available team members and `send_message` to coordinate work "
        "and ask for help when needed. "
        "### Note-Taking: You have access to comprehensive note-taking tools "
        "for documenting work progress and collaborating with team members. "
        "Use create_note, append_note, read_note, and list_note to track "
        "your work, share findings, and access information from other agents. "
        "Create notes for work progress, discoveries, and collaboration "
        "points."
    )
    return NEW_WORKER_ROLE_PROMPT


def send_message_to_user(
    message_title: str,
    message_description: str,
    message_attachment: str = "",
) -> str:
    r"""Use this tool to send a tidy message to the user, including a
    short title, a one-sentence description, and an optional attachment.

    This one-way tool keeps the user informed about your progress,
    decisions, or actions. It does not require a response.
    You should use it to:
    - Announce what you are about to do.
      For example:
      message_title="Starting Task"
      message_description="Searching for papers on GUI Agents."
    - Report the result of an action.
      For example:
      message_title="Search Complete"
      message_description="Found 15 relevant papers."
    - Report a created file.
      For example:
      message_title="File Ready"
      message_description="The report is ready for your review."
      message_attachment="report.pdf"
    - State a decision.
      For example:
      message_title="Next Step"
      message_description="Analyzing the top 10 papers."
    - Give a status update during a long-running task.

    Args:
        message_title (str): The title of the message.
        message_description (str): The short description.
        message_attachment (str): The attachment of the message,
            which can be a file path or a URL.

    Returns:
        str: Confirmation that the message was successfully sent.
    """
    print(f"\nAgent Message:\n{message_title} " f"\n{message_description}\n")
    if message_attachment:
        print(message_attachment)
    logger.info(
        f"\nAgent Message:\n{message_title} "
        f"{message_description} {message_attachment}"
    )
    return (
        f"Message successfully sent to user: '{message_title} "
        f"{message_description} {message_attachment}'"
    )


def developer_agent_factory(
    model: BaseModelBackend,
    system: str = platform.system(),
    machine: str = platform.machine(),
    is_workforce: bool = False,
    working_directory: str = "CAMEL_WORKDIR",
):
    r"""Factory for creating a developer agent."""
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Initialize toolkits
    # terminal_toolkit = TerminalToolkit(safe_mode=True, clone_current_env=False)
    note_toolkit = NoteTakingToolkit(working_directory=working_directory)

    # Add messaging to toolkits
    note_toolkit = message_integration.register_toolkits(note_toolkit)

    # Get enhanced tools
    tools = [
        *note_toolkit.get_tools(),
    ]

    system_message = get_developer_agent_prompt(
        current_date=str(datetime.date.today()),
        system=system,
        machine=machine,
        is_workforce=is_workforce,
    )

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Developer Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)


camel_agent = developer_agent_factory(
    model=model,
)


TBench_instance = TBench(
    name="TerminalBench",
    data_dir="data/tbench",
    save_to="tbench_results",
    processes=1,
)
print(TBench_instance.run(agent=camel_agent, subset=2))
