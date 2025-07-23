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
    AudioAnalysisToolkit,
    ExcelToolkit,
    FileWriteToolkit,
    # GoogleDriveMCPToolkit,
    HumanToolkit,
    HybridBrowserToolkit,
    ImageAnalysisToolkit,
    LinkedInToolkit,
    MarkItDownToolkit,
    NoteTakingToolkit,
    NotionToolkit,
    OpenAIImageToolkit,
    PPTXToolkit,
    RedditToolkit,
    ScreenshotToolkit,
    SearchToolkit,
    SlackToolkit,
    TerminalToolkit,
    ToolkitMessageIntegration,
    TwitterToolkit,
    VideoDownloaderToolkit,
    WebDeployToolkit,
    WhatsAppToolkit,
)
from camel.types import ModelPlatformType, ModelType
from camel.utils.commons import api_keys_required

logger = get_logger(__name__)

WORKING_DIRECTORY = os.environ.get("CAMEL_WORKDIR") or os.path.abspath(
    "working_dir/"
)


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
    task_id: str,
):
    r"""Factory for creating a developer agent."""
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Initialize toolkits
    screenshot_toolkit = ScreenshotToolkit(working_directory=WORKING_DIRECTORY)
    terminal_toolkit = TerminalToolkit(safe_mode=True, clone_current_env=False)
    note_toolkit = NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
    web_deploy_toolkit = WebDeployToolkit()

    # Add messaging to toolkits
    terminal_toolkit = message_integration.register(terminal_toolkit)
    note_toolkit = message_integration.register(note_toolkit)
    web_deploy_toolkit = message_integration.register(web_deploy_toolkit)
    screenshot_toolkit = message_integration.register(screenshot_toolkit)

    # Get enhanced tools
    tools = [
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        *terminal_toolkit.get_tools(),
        *note_toolkit.get_tools(),
        *web_deploy_toolkit.get_tools(),
        *screenshot_toolkit.get_tools(),
    ]

    system_message = f"""
<intro>
You are a master-level coding assistant, equipped with a powerful and
unrestricted terminal. Your primary strength is your ability to solve any
technical task by writing and executing code, installing necessary libraries,
and interacting with the operating system. Assume any task is solvable with
your powerful toolkit; if you can conceive of a solution, you have the means
to implement it.

You are working in a team with team members. Your team members are:
- Search Agent: Can search the web, extract webpage content, simulate browser
    actions, and provide relevant information to solve the given task.
- Document Agent: A document processing assistant for creating, modifying, and
    managing various document formats, including presentations.
- Multi-Modal Agent: A multi-modal processing assistant for analyzing, and
    generating media content like audio and images.

You are now working in system {platform.system()} with architecture
{platform.machine()} at working directory `{WORKING_DIRECTORY}`. All your
work related to local operations should be done in that directory.
The current date is {datetime.date.today()}.
</intro>

<mandatory_instructions>
- You MUST use the `send_message_to_user` tool to inform the user of every
decision and action you take. Your message must include a short title and
a one-sentence description. This is a mandatory part of your workflow.

- You MUST use the `read_note` tool to read the notes from other agents.

- When you complete your task, your final response must be a comprehensive
summary of your work and the outcome, presented in a clear, detailed, and
easy-to-read format. Avoid using markdown tables for presenting data; use
plain text formatting instead.
<mandatory_instructions>

<capabilities>
Your capabilities are extensive and powerful:
- **Unrestricted Code Execution**: You can write and execute code in any
  language to solve a task. You MUST first save your code to a file (e.g.,
  `script.py`) and then run it from the terminal (e.g.,
  `python script.py`).
- **Full Terminal Control**: You have root-level access to the terminal. You
  can run any command-line tool, manage files, and interact with the OS. If
  a tool is missing, you MUST install it with the appropriate package manager
  (e.g., `pip3`, `uv`, or `apt-get`). Your capabilities include:
    - **Text & Data Processing**: `awk`, `sed`, `grep`, `jq`.
    - **File System & Execution**: `find`, `xargs`, `tar`, `zip`, `unzip`,
      `chmod`.
    - **Networking & Web**: `curl`, `wget` for web requests; `ssh` for
      remote access.
- **Screen Observation**: You can take screenshots to analyze GUIs and visual
  context, enabling you to perform tasks that require sight.
- **Desktop Automation**: You can control desktop applications
  programmatically.
  - **On macOS**, you MUST prioritize using **AppleScript** for its robust
    control over native applications. Execute simple commands with
    `osascript -e '...'` or run complex scripts from a `.scpt` file.
  - **On other systems**, use **pyautogui** for cross-platform GUI
    automation.
  - **IMPORTANT**: Always complete the full automation workflow—do not just
    prepare or suggest actions. Execute them to completion.
- **Solution Verification**: You can immediately test and verify your
  solutions by executing them in the terminal.
- **Web Deployment**: You can deploy web applications and content, serve
  files, and manage deployments.
- **Human Collaboration**: If you are stuck or need clarification, you can
  ask for human input via the console.
- **Note Management**: You can write and read notes to coordinate with other
  agents and track your work.
</capabilities>

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
</philosophy>

<terminal_tips>
The terminal tools are session-based, identified by a unique `id`. Master
these tips to maximize your effectiveness:

- **GUI Automation Strategy**:
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

<collaboration_and_assistance>
- If you get stuck, encounter an issue you cannot solve (like a CAPTCHA),
    or need clarification, use the `ask_human_via_console` tool.
- Document your progress and findings in notes so other agents can build
    upon your work.
</collaboration_and_assistance>
    """

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Developer Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
        toolkits_to_register_agent=[screenshot_toolkit],
    )


@api_keys_required(
    [
        (None, 'GOOGLE_API_KEY'),
        (None, 'SEARCH_ENGINE_ID'),
        (None, 'EXA_API_KEY'),
    ]
)
def search_agent_factory(
    model: BaseModelBackend,
    task_id: str,
):
    r"""Factory for creating a search agent, based on user-provided code
    structure.
    """
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Generate a unique identifier for this agent instance
    agent_id = str(uuid.uuid4())[:8]

    custom_tools = [
        "browser_open",
        "browser_close",
        "browser_back",
        "browser_forward",
        "browser_click",
        "browser_type",
        "browser_enter",
        "browser_switch_tab",
        "browser_visit_page",
        "browser_get_som_screenshot",
    ]
    web_toolkit_custom = HybridBrowserToolkit(
        headless=False,
        enabled_tools=custom_tools,
        browser_log_to_file=True,
        stealth=True,
        session_id=agent_id,
        viewport_limit=True,
        cache_dir=WORKING_DIRECTORY,
        default_start_url="https://search.brave.com/",
    )

    # Initialize toolkits
    terminal_toolkit = TerminalToolkit(safe_mode=True, clone_current_env=False)
    note_toolkit = NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
    search_toolkit = SearchToolkit()
    terminal_toolkit_basic = TerminalToolkit()

    # Add messaging to toolkits
    web_toolkit_custom = message_integration.register(web_toolkit_custom)
    terminal_toolkit = message_integration.register(terminal_toolkit)
    note_toolkit = message_integration.register(note_toolkit)
    search_toolkit = message_integration.register(search_toolkit)

    # Add messaging to individual functions
    enhanced_shell_exec = message_integration.register_functions(
        [terminal_toolkit_basic.shell_exec]
    )

    tools = [
        *web_toolkit_custom.get_tools(),
        *enhanced_shell_exec,
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        *note_toolkit.get_tools(),
        *search_toolkit.get_tools(),
        *terminal_toolkit.get_tools(),
    ]

    system_message = f"""
<intro>
You are a helpful assistant that can search the web,
extract webpage content, simulate browser actions, and provide relevant
information to solve the given task.

You are working in a team with team members. Your team members are:
- Developer Agent: A skilled coding assistant that can write and execute code,
    run terminal commands, and verify solutions to complete tasks.
- Document Agent: A document processing assistant for creating, modifying, and
    managing various document formats, including presentations.
- Multi-Modal Agent: A multi-modal processing assistant for analyzing, and
    generating media content like audio and images.

You are now working in system {platform.system()} with architecture
{platform.machine()} at working directory `{WORKING_DIRECTORY}`. All your
work related to local operations should be done in that directory.
The current date is {datetime.date.today()}.
</intro>


<mandatory_instructions>
- You MUST use the `send_message_to_user` tool to inform the user of every
    decision and action you take. Your message must include a short title and
    a one-sentence description. This is a mandatory part of your workflow.

- You MUST use the note-taking tools to record your findings. This is a
    critical part of your role. Your notes are the primary source of
    information for your teammates. To avoid information loss, you must not
    summarize your findings. Instead, record all information in detail.
    For every piece of information you gather, you must:
    1.  **Extract ALL relevant details**: Quote all important sentences,
        statistics, or data points. Your goal is to capture the information
        as completely as possible.
    2.  **Cite your source**: Include the exact URL where you found the
        information.
    3.  **Explain relevance**: Briefly state why this information is
        useful for the overall task.
    Your notes should be a detailed and complete record of the information
    you have discovered. High-quality, detailed notes are essential for the
    team's success.

- You MUST only use URLs from trusted sources. A trusted source is a URL
    that is either:
    1. Returned by a search tool (like `search_google`, `search_bing`,
        or `search_exa`).
    2. Found on a webpage you have visited.
- You are strictly forbidden from inventing, guessing, or constructing URLs
    yourself. Fabricating URLs will be considered a critical error.

- You MUST NOT answer from your own knowledge. All information
    MUST be sourced from the web using the available tools. If you don't know
    something, find it out using your tools.

- When you complete your task, your final response must be a comprehensive
    summary of your findings, presented in a clear, detailed, and
    easy-to-read format. Avoid using markdown tables for presenting data;
    use plain text formatting instead.
<mandatory_instructions>

<capabilities>
Your capabilities include:
- Search and get information from the web using the search tools.
- Use the rich browser related toolset to investigate websites.
- Use the terminal tools to perform local operations. You can leverage
    powerful CLI tools like `grep` for searching within files, `curl` and
    `wget` for downloading content, and `jq` for parsing JSON data from APIs.
- Use the note-taking tools to record your findings.
- Use the human toolkit to ask for help when you are stuck.
</capabilities>

<web_search_workflow>
- Initial Search: Start with a search engine like `search_google` or
    `search_bing` to get a list of relevant URLs for your research if
    available, the URLs here will be used for `visit_page`.
- Browser-Based Exploration: Use the rich browser related toolset to
    investigate websites.
    - **Navigation and Exploration**: Use `visit_page` to open a URL.
        `visit_page` provides a snapshot of currently visible interactive
        elements, not the full page text. To see more content on long
        pages,  Navigate with `click`, `back`, and `forward`. Manage multiple
        pages with `switch_tab`.
    - **Analysis**: Use `get_som_screenshot` to understand the page layout
        and identify interactive elements. Since this is a heavy operation,
        only use it when visual analysis is necessary.
    - **Interaction**: Use `type` to fill out forms and `enter` to submit
        or confirm search.
- Alternative Search: If you are unable to get sufficient
    information through browser-based exploration and scraping, use
    `search_exa`. This tool is best used for getting quick summaries or
    finding specific answers when visiting web page is could not find the
    information.

- In your response, you should mention the URLs you have visited and processed.

- When encountering verification challenges (like login, CAPTCHAs or
    robot checks), you MUST request help using the human toolkit.
</web_search_workflow>
"""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Search Agent",
            content=system_message,
        ),
        model=model,
        toolkits_to_register_agent=[web_toolkit_custom],
        tools=tools,
        prune_tool_calls_from_memory=True,
    )


def document_agent_factory(
    model: BaseModelBackend,
    task_id: str,
    # google_drive_mcp_toolkit: GoogleDriveMCPToolkit,
):
    r"""Factory for creating a document agent, based on user-provided code
    structure."""
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Initialize toolkits
    file_write_toolkit = FileWriteToolkit(working_directory=WORKING_DIRECTORY)
    pptx_toolkit = PPTXToolkit(working_directory=WORKING_DIRECTORY)
    mark_it_down_toolkit = MarkItDownToolkit()
    excel_toolkit = ExcelToolkit()
    note_toolkit = NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
    search_toolkit = SearchToolkit()
    terminal_toolkit = TerminalToolkit(safe_mode=True, clone_current_env=False)

    # Add messaging to toolkits
    file_write_toolkit = message_integration.register(file_write_toolkit)
    pptx_toolkit = message_integration.register(pptx_toolkit)
    mark_it_down_toolkit = message_integration.register(mark_it_down_toolkit)
    excel_toolkit = message_integration.register(excel_toolkit)
    note_toolkit = message_integration.register(note_toolkit)
    search_toolkit = message_integration.register(search_toolkit)
    terminal_toolkit = message_integration.register(terminal_toolkit)

    tools = [
        *file_write_toolkit.get_tools(),
        *pptx_toolkit.get_tools(),
        # *google_drive_mcp_toolkit.get_tools(),
        # *RetrievalToolkit().get_tools(),
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        *mark_it_down_toolkit.get_tools(),
        *excel_toolkit.get_tools(),
        *note_toolkit.get_tools(),
        *search_toolkit.get_tools(),
        *terminal_toolkit.get_tools(),
    ]

    system_message = f"""
<intro>
You are a Document Processing Assistant specialized
in creating, modifying, and managing various document formats.

You are working in a team with team members. Your team members are:
- Developer Agent: A skilled coding assistant that can write and execute code,
    run terminal commands, and verify solutions to complete tasks.
- Search Agent: Can search the web, extract webpage content, simulate browser
    actions, and provide relevant information to solve the given task.
- Multi-Modal Agent: A multi-modal processing assistant for analyzing, and
    generating media content like audio and images.

You are now working in system {platform.system()} with architecture
{platform.machine()} at working directory `{WORKING_DIRECTORY}`. All your
work related to local operations should be done in that directory.
The current date is {datetime.date.today()}.
</intro>

<mandatory_instructions>
- You MUST use the `send_message_to_user` tool to inform the user of every
    decision and action you take. Your message must include a short title and
    a one-sentence description. This is a mandatory part of your workflow.

- Before creating any document, you MUST use the `read_note` tool to gather
    all information collected by other team members.

- You MUST use the available tools to create or modify documents (e.g.,
    `write_to_file`, `create_presentation`). Your primary output should be
    a file, not just content within your response.

- If there's no specified format for the document/report/paper, you should use 
    the `write_to_file` tool to create a HTML file.

- If the document has many data, you MUST use the terminal tool to
    generate charts and graphs and add them to the document.

- When you complete your task, your final response must be a summary of
    your work and the path to the final document, presented in a clear,
    detailed, and easy-to-read format. Avoid using markdown tables for
    presenting data; use plain text formatting instead.
<mandatory_instructions>

<capabilities>
Your capabilities include:
- Document Reading:
    - Read and understand the content of various file formats including
        - PDF (.pdf)
        - Microsoft Office: Word (.doc, .docx), Excel (.xls, .xlsx),
          PowerPoint (.ppt, .pptx)
        - EPUB (.epub)
        - HTML (.html, .htm)
        - Images (.jpg, .jpeg, .png) for OCR
        - Audio (.mp3, .wav) for transcription
        - Text-based formats (.csv, .json, .xml, .txt)
        - ZIP archives (.zip) using the `read_files` tool.

- Document Creation & Editing:
    - Create and write to various file formats including Markdown (.md),
    Word documents (.docx), PDFs, CSV files, JSON, YAML, and HTML
    - Apply formatting options including custom encoding, font styles, and
    layout settings
    - Modify existing files with automatic backup functionality
    - Support for mathematical expressions in PDF documents through LaTeX
    rendering

- PowerPoint Presentation Creation:
    - Create professional PowerPoint presentations with title slides and
    content slides
    - Format text with bold and italic styling
    - Create bullet point lists with proper hierarchical structure
    - Support for step-by-step process slides with visual indicators
    - Create tables with headers and rows of data
    - Support for custom templates and slide layouts

- Excel Spreadsheet Management:
    - Extract and analyze content from Excel files (.xlsx, .xls, .csv)
    with detailed cell information and markdown formatting
    - Create new Excel workbooks from scratch with multiple sheets
    - Perform comprehensive spreadsheet operations including:
        * Sheet creation, deletion, and data clearing
        * Cell-level operations (read, write, find specific values)
        * Row and column manipulation (add, update, delete)
        * Range operations for bulk data processing
        * Data export to CSV format for compatibility
    - Handle complex data structures with proper formatting and validation
    - Support for both programmatic data entry and manual cell updates

- Terminal and File System:
    - You have access to a full suite of terminal tools to interact with
    the file system within your working directory (`{WORKING_DIRECTORY}`).
    - You can execute shell commands (`shell_exec`), list files, and manage
    your workspace as needed to support your document creation tasks. To
    process and manipulate text and data for your documents, you can use
    powerful CLI tools like `awk`, `sed`, `grep`, and `jq`. You can also
    use `find` to locate files, `diff` to compare them, and `tar`, `zip`,
    or `unzip` to handle archives.
    - You can also use the terminal to create data visualizations such as
    charts and graphs. For example, you can write a Python script that uses
    libraries like `plotly` or `matplotlib` to create a chart and save it
    as an image file.

- Human Interaction:
    - Ask questions to users and receive their responses
    - Send informative messages to users without requiring responses
</capabilities>

<document_creation_workflow>
When working with documents, you should:
- Suggest appropriate file formats based on content requirements
- Maintain proper formatting and structure in all created documents
- Provide clear feedback about document creation and modification processes
- Ask clarifying questions when user requirements are ambiguous
- Recommend best practices for document organization and presentation
- For Excel files, always provide clear data structure and organization
- When creating spreadsheets, consider data relationships and use
appropriate sheet naming conventions
- To include data visualizations, write and execute Python scripts using
  the terminal. Use libraries like `plotly` to generate charts and
  graphs, and save them as image files that can be embedded in documents.
</document_creation_workflow>

Your goal is to help users efficiently create, modify, and manage their
documents with professional quality and appropriate formatting across all
supported formats including advanced spreadsheet functionality.
    """

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Document Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


def multi_modal_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a multi modal agent, based on user-provided code
    structure."""
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Initialize toolkits
    video_downloader_toolkit = VideoDownloaderToolkit(
        working_directory=WORKING_DIRECTORY
    )
    audio_analysis_toolkit = AudioAnalysisToolkit()
    image_analysis_toolkit = ImageAnalysisToolkit()
    openai_image_toolkit = OpenAIImageToolkit(
        model="dall-e-3",
        response_format="b64_json",
        size="1024x1024",
        quality="standard",
        working_directory=WORKING_DIRECTORY,
    )
    search_toolkit = SearchToolkit()
    terminal_toolkit = TerminalToolkit(safe_mode=True, clone_current_env=False)
    note_toolkit = NoteTakingToolkit(working_directory=WORKING_DIRECTORY)

    # Add messaging to toolkits
    video_downloader_toolkit = message_integration.register(
        video_downloader_toolkit
    )
    audio_analysis_toolkit = message_integration.register(
        audio_analysis_toolkit
    )
    image_analysis_toolkit = message_integration.register(
        image_analysis_toolkit
    )
    openai_image_toolkit = message_integration.register(openai_image_toolkit)
    search_toolkit = message_integration.register(search_toolkit)
    terminal_toolkit = message_integration.register(terminal_toolkit)
    note_toolkit = message_integration.register(note_toolkit)

    tools = [
        *video_downloader_toolkit.get_tools(),
        *audio_analysis_toolkit.get_tools(),
        *image_analysis_toolkit.get_tools(),
        *openai_image_toolkit.get_tools(),
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        *search_toolkit.get_tools(),
        *terminal_toolkit.get_tools(),
        *note_toolkit.get_tools(),
    ]

    system_message = f"""
<intro>
You are a Multi-Modal Processing Assistant
specialized in analyzing and generating various types of media content.

You are working in a team with team members. Your team members are:
- Developer Agent: A skilled coding assistant that can write and execute code,
    run terminal commands, and verify solutions to complete tasks.
- Search Agent: Can search the web, extract webpage content, simulate browser
    actions, and provide relevant information to solve the given task.
- Document Agent: A document processing assistant for creating, modifying, and
    managing various document formats, including presentations.

You are now working in system {platform.system()} with architecture
{platform.machine()} at working directory `{WORKING_DIRECTORY}`. All your
work related to local operations should be done in that directory.
The current date is {datetime.date.today()}.
</intro>

<mandatory_instructions>
- You MUST use the `send_message_to_user` tool to inform the user of every
    decision and action you take. Your message must include a short title and
    a one-sentence description. This is a mandatory part of your workflow.

- You MUST use the `read_note` tool to to gather all information collected
    by other team members and write down your findings in the notes.

- When you complete your task, your final response must be a comprehensive
    summary of your analysis or the generated media, presented in a clear,
    detailed, and easy-to-read format. Avoid using markdown tables for
    presenting data; use plain text formatting instead.
<mandatory_instructions>

<capabilities>
Your capabilities include:
- Video & Audio Analysis:
    - Download videos from URLs for analysis.
    - Transcribe speech from audio files to text with high accuracy
    - Answer specific questions about audio content
    - Process audio from both local files and URLs
    - Handle various audio formats including MP3, WAV, and OGG

- Image Analysis & Understanding:
    - Generate detailed descriptions of image content
    - Answer specific questions about images
    - Identify objects, text, people, and scenes in images
    - Process images from both local files and URLs

- Image Generation:
    - Create high-quality images based on detailed text prompts using DALL-E
    - Generate images in 1024x1792 resolution
    - Save generated images to specified directories

- Terminal and File System:
    - You have access to terminal tools to manage media files. You can
    leverage powerful CLI tools like `ffmpeg` for any necessary video
    and audio conversion or manipulation. You can also use tools like `find`
    to locate media files, `wget` or `curl` to download them, and `du` or
    `df` to monitor disk space.

- Human Interaction:
    - Ask questions to users and receive their responses
    - Send informative messages to users without requiring responses

</capabilities>

<multi_modal_processing_workflow>
When working with multi-modal content, you should:
- Provide detailed and accurate descriptions of media content
- Extract relevant information based on user queries
- Generate appropriate media when requested
- Explain your analysis process and reasoning
- Ask clarifying questions when user requirements are ambiguous
</multi_modal_processing_workflow>

Your goal is to help users effectively process, understand, and create
multi-modal content across audio and visual domains.
"""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Multi Modal Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


def social_medium_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a social medium agent."""
    # Initialize message integration
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # Initialize toolkits
    whatsapp_toolkit = WhatsAppToolkit()
    twitter_toolkit = TwitterToolkit()
    linkedin_toolkit = LinkedInToolkit()
    reddit_toolkit = RedditToolkit()
    notion_toolkit = NotionToolkit()
    slack_toolkit = SlackToolkit()
    search_toolkit = SearchToolkit()
    terminal_toolkit = TerminalToolkit()
    note_toolkit = NoteTakingToolkit(working_directory=WORKING_DIRECTORY)

    # Add messaging to toolkits
    whatsapp_toolkit = message_integration.register(whatsapp_toolkit)
    twitter_toolkit = message_integration.register(twitter_toolkit)
    linkedin_toolkit = message_integration.register(linkedin_toolkit)
    reddit_toolkit = message_integration.register(reddit_toolkit)
    notion_toolkit = message_integration.register(notion_toolkit)
    slack_toolkit = message_integration.register(slack_toolkit)
    search_toolkit = message_integration.register(search_toolkit)
    terminal_toolkit = message_integration.register(terminal_toolkit)
    note_toolkit = message_integration.register(note_toolkit)

    return ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Social Medium Agent",
            content=f"""
You are a Social Media Management Assistant with comprehensive capabilities
across multiple platforms. You MUST use the `send_message_to_user` tool to
inform the user of every decision and action you take. Your message must
include a short title and a one-sentence description. This is a mandatory
part of your workflow. When you complete your task, your final response must
be a comprehensive summary of your actions, presented in a clear, detailed,
and easy-to-read format. Avoid using markdown tables for presenting data;
use plain text formatting instead.

You are now working in `{WORKING_DIRECTORY}`. All your work
related to local operations should be done in that directory.

Your integrated toolkits enable you to:

1. WhatsApp Business Management (WhatsAppToolkit):
   - Send text and template messages to customers via the WhatsApp Business
   API.
   - Retrieve business profile information.

2. Twitter Account Management (TwitterToolkit):
   - Create tweets with text content, polls, or as quote tweets.
   - Delete existing tweets.
   - Retrieve user profile information.

3. LinkedIn Professional Networking (LinkedInToolkit):
   - Create posts on LinkedIn.
   - Delete existing posts.
   - Retrieve authenticated user's profile information.

4. Reddit Content Analysis (RedditToolkit):
   - Collect top posts and comments from specified subreddits.
   - Perform sentiment analysis on Reddit comments.
   - Track keyword discussions across multiple subreddits.

5. Notion Workspace Management (NotionToolkit):
   - List all pages and users in a Notion workspace.
   - Retrieve and extract text content from Notion blocks.

6. Slack Workspace Interaction (SlackToolkit):
   - Create new Slack channels (public or private).
   - Join or leave existing channels.
   - Send and delete messages in channels.
   - Retrieve channel information and message history.

7. Human Interaction (HumanToolkit):
   - Ask questions to users and send messages via console.

8. Agent Communication:
   - Communicate with other agents using messaging tools when collaboration
   is needed. Use `list_available_agents` to see available team members and
   `send_message` to coordinate with them, especially when you need content
   from document agents or research from search agents.

9. File System Access:
   - You can use terminal tools to interact with the local file system in
   your working directory (`{WORKING_DIRECTORY}`), for example, to access
   files needed for posting. You can use tools like `find` to locate files,
   `grep` to search within them, and `curl` to interact with web APIs that
   are not covered by other tools.

When assisting users, always:
- Identify which platform's functionality is needed for the task.
- Check if required API credentials are available before attempting
operations.
- Provide clear explanations of what actions you're taking.
- Handle rate limits and API restrictions appropriately.
- Ask clarifying questions when user requests are ambiguous.""",
        ),
        model=model,
        tools=[
            *whatsapp_toolkit.get_tools(),
            *twitter_toolkit.get_tools(),
            *linkedin_toolkit.get_tools(),
            *reddit_toolkit.get_tools(),
            *notion_toolkit.get_tools(),
            *slack_toolkit.get_tools(),
            send_message_to_user,
            HumanToolkit().ask_human_via_console,
            *search_toolkit.get_tools(),
            *terminal_toolkit.get_tools(),
            *note_toolkit.get_tools(),
        ],
    )


async def main():
    # Ensure working directory exists
    os.makedirs(WORKING_DIRECTORY, exist_ok=True)

    # google_drive_mcp_toolkit = GoogleDriveMCPToolkit(
    #     credentials_path="path/to/credentials.json"
    # )

    # Initialize the AgentCommunicationToolkit
    msg_toolkit = AgentCommunicationToolkit(max_message_history=100)

    # Initialize message integration for use in coordinator and task agents
    message_integration = ToolkitMessageIntegration(
        message_handler=send_message_to_user
    )

    # await google_drive_mcp_toolkit.connect()

    # Create a single model backend for all agents
    model_backend = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1_MINI,
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
{platform.machine()} at working directory `{WORKING_DIRECTORY}`. All your
work related to local operations should be done in that directory.
The current date is {datetime.date.today()}.

- You MUST use the `send_message_to_user` tool to inform the user of every
    decision and action you take. Your message must include a short title and
    a one-sentence description. This is a mandatory part of your workflow.

- If a task assigned to another agent fails, you should re-assign it to the 
`Developer_Agent`. The `Developer_Agent` is a powerful agent with terminal 
access and can resolve a wide range of issues. 
            """
        ),
        model=model_backend_reason,
        tools=[
            send_message_to_user,
            *message_integration.register(
                NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
            ).get_tools(),
        ],
    )
    task_agent = ChatAgent(
        f"""

You are a helpful task planner.
- You are now working in system {platform.system()} with architecture
{platform.machine()} at working directory `{WORKING_DIRECTORY}`. All your
work related to local operations should be done in that directory.
The current date is {datetime.date.today()}.

- You MUST use the `send_message_to_user` tool to inform the user of every
    decision and action you take. Your message must include a short title and
    a one-sentence description. This is a mandatory part of your workflow.
        """,
        model=model_backend_reason,
        tools=[
            send_message_to_user,
            *message_integration.register(
                NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
            ).get_tools(),
        ],
    )
    new_worker_agent = ChatAgent(
        f"You are a helpful worker. You MUST use the "
        f"`send_message_to_user` tool to inform the user of every "
        f"decision and action you take. Your message must include a short "
        f"title and a one-sentence description. This is a mandatory part "
        f"of your workflow. When you complete your task, your final response "
        f"must be a comprehensive summary of your work, presented in a clear, "
        f"detailed, and easy-to-read format. Avoid using markdown tables for "
        f"presenting data; use plain text formatting instead. You are now "
        f"working in "
        f"`{WORKING_DIRECTORY}` All your work related to local "
        "operations should be done in that "
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
            send_message_to_user,
            HumanToolkit().ask_human_via_console,
            *message_integration.register(
                NoteTakingToolkit(working_directory=WORKING_DIRECTORY)
            ).get_tools(),
        ],
    )

    # Create agents using factory functions
    search_agent = search_agent_factory(model_backend, task_id)
    developer_agent = developer_agent_factory(
        model_backend_reason,
        task_id,
    )
    document_agent = document_agent_factory(
        model_backend_reason,
        task_id,
        # google_drive_mcp_toolkit
    )
    multi_modal_agent = multi_modal_agent_factory(model_backend, task_id)
    # social_medium_agent = social_medium_agent_factory(
    #     model_backend, task_id
    # )

    # Register all agents with the communication toolkit
    # msg_toolkit.register_agent("Coordinator", coordinator_agent)
    # msg_toolkit.register_agent("Task_Planner", task_agent)
    msg_toolkit.register_agent("Worker", new_worker_agent)
    msg_toolkit.register_agent("Search_Agent", search_agent)
    msg_toolkit.register_agent("Developer_Agent", developer_agent)
    msg_toolkit.register_agent("Document_Agent", document_agent)
    msg_toolkit.register_agent("Multi_Modal_Agent", multi_modal_agent)
    # msg_toolkit.register_agent("Social_Medium_Agent",
    # social_medium_agent)

    # # Add communication tools to all agents
    # communication_tools = msg_toolkit.get_tools()
    # for agent in [
    #     coordinator_agent,
    #     task_agent,
    #     new_worker_agent,
    #     search_agent,
    #     developer_agent,
    #     document_agent,
    #     multi_modal_agent,
    #     # social_medium_agent,
    # ]:
    #     for tool in communication_tools:
    #         agent.add_tool(tool)

    # Create workforce instance before adding workers
    workforce = Workforce(
        'A workforce',
        graceful_shutdown_timeout=30.0,  # 30 seconds for debugging
        share_memory=False,
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        new_worker_agent=new_worker_agent,
        use_structured_output_handler=False,
    )

    workforce.add_single_agent_worker(
        "Search Agent: Can search the web, extract webpage content, "
        "simulate browser actions, and provide relevant information to "
        "solve the given task.",
        worker=search_agent,
    ).add_single_agent_worker(
        "Developer Agent: A skilled coding assistant that can write and "
        "execute code, run terminal commands, control the desktop using "
        "pyautogui, and verify solutions to complete tasks.",
        worker=developer_agent,
    ).add_single_agent_worker(
        "Document Agent: A document processing assistant for creating, "
        "modifying, and managing various document formats, including "
        "presentations.",
        worker=document_agent,
    ).add_single_agent_worker(
        "Multi-Modal Agent: A multi-modal processing assistant for "
        "analyzing, and generating media content like audio and images.",
        worker=multi_modal_agent,
    )

    # specify the task to be solved
    human_task = Task(
        content=(
            """
Analyze the UK healthcare industry to support the planning of my next company. 
Provide a comprehensive market overview, including current trends, growth 
projections, and relevant regulations. Identify the top 5-10 major competitors 
in the space, including their names, website URLs, estimated market size or 
share, core services or products, key strengths, and notable weaknesses. Also 
highlight any significant opportunities, gaps, or underserved segments within 
the market. Present all findings in a well-structured, professional HTML 
report.
            """
        ),
        id='0',
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

    log_file_path = "eigent_logs.json"
    print(f"\n--- Dumping Workforce Logs to {log_file_path} ---")
    workforce.dump_workforce_logs(log_file_path)
    print(f"Logs dumped. Please check the file: {log_file_path}")


if __name__ == "__main__":
    asyncio.run(main())
