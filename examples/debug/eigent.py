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
import uuid

import traceroot

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import (
    AgentCommunicationToolkit,
    AudioAnalysisToolkit,
    Crawl4AIToolkit,
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
    SearchToolkit,
    SlackToolkit,
    TerminalToolkit,
    TwitterToolkit,
    VideoDownloaderToolkit,
    WhatsAppToolkit,
)
from camel.types import ModelPlatformType, ModelType
from camel.utils.commons import api_keys_required

logger = traceroot.get_logger('camel')

WORKING_DIRECTORY = os.environ.get("CAMEL_WORKDIR") or "working_dir/"


@traceroot.trace()
def send_message_to_user(message: str) -> str:
    r"""Use this tool to send a tidy message to the user, including a
    short title and a one-sentence description.

    This one-way tool keeps the user informed about your progress,
    decisions, or actions. It does not require a response.
    You should use it to:
    - Announce what you are about to do (e.g.,
        'Starting Task\nSearching for papers on
        GUI Agents.').
    - Report the result of an action (e.g.,
        'Search Complete\nFound 15 relevant
        papers.').
    - State a decision (e.g.,
        'Next Step\nAnalyzing the top 10
        papers.').
    - Give a status update during a long-running task.

    Args:
        message (str): The tidy and informative message for the user,
            which should contain a title and a description.

    Returns:
        str: Confirmation that the message was successfully sent.
    """
    print(f"\nAgent Message:\n{message}")
    logger.info(f"\nAgent Message:\n{message}")
    return f"Message successfully sent to user: '{message}'"


@traceroot.trace()
def developer_agent_factory(
    model: BaseModelBackend,
    task_id: str,
):
    r"""Factory for creating a developer agent."""
    tools = [
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        *TerminalToolkit(clone_current_env=True).get_tools(),
    ]

    system_message = f"""You are a skilled coding assistant. You can write and 
    execute code by using the available terminal tools. You MUST use the 
    `send_message_to_user` tool to inform the user of every decision and 
    action you take. Your message must include a short title and a 
    one-sentence description. This is a mandatory part of your workflow.

    You are now working in `{WORKING_DIRECTORY}`. All your work
    related to local operations should be done in that directory.

    Your capabilities include:
    - Writing code to solve tasks. To execute the code, you MUST first save 
    it to a file in the workspace (e.g., `script.py`), and then run it using 
    the terminal tool (e.g., `python script.py`).
    - Running terminal commands to install packages (e.g., with `pip` or 
    `uv`), process files, or test functionality. All files you create should 
    be in the designated workspace.
    - You can use `uv` or `pip` to install packages, for example, `uv pip 
    install requests` or `pip install requests`.
    - Verifying your solutions through immediate execution and testing in the 
    terminal.
    - Utilizing any Python libraries (e.g., requests, BeautifulSoup, pandas, 
    etc.) needed for efficient solutions. You can install missing packages 
    using `pip` or `uv` in the terminal.
    - Implementing complete, production-ready code rather than theoretical 
    examples.
    - Demonstrating results with proper error handling and practical 
    implementation.
    - Asking for human input via the console if you are stuck or need 
    clarification.
    - Communicating with other agents using messaging tools. You can use 
    `list_available_agents` to see available team members and `send_message` 
    to coordinate with them for complex tasks requiring collaboration.

    ### Terminal Tool Workflow:
    The terminal tools are session-based. You must manage one or more terminal 
    sessions to perform your tasks. A session is identified by a unique `id`.

    1.  **Execute Commands**: Use `shell_exec(id="...", command="...")` to run 
        a command. If the `id` is new, a new session is created.
        Example: `shell_exec(id="session_1", command="ls -l")`

    2.  **Manage Long-Running Tasks**: For commands that take time, run them 
        in one step, and then use `shell_wait(id="...")` to wait for 
        completion. This prevents blocking and allows you to perform other 
        tasks in parallel.

    3.  **View Output**: Use `shell_view(id="...")` to see the full command 
        history and output of a session.

    4.  **Run Tasks in Parallel**: Use different session IDs to run multiple 
        commands concurrently.
        - `shell_exec(id="install", command="pip install numpy")`
        - `shell_exec(id="test", command="python my_script.py")`

    5.  **Interact with Processes**: For commands that require input:
        - Initialize TerminalToolkit with `interactive=True` for real-time 
          interactive sessions.
        - Use `shell_write_to_process(id="...", content="...")` to send input 
          to a non-interactive running process.

    6.  **Stop a Process**: If a process needs to be terminated, use 
        `shell_kill_process(id="...")`.

    ### Collaboration and Assistance:
    - If you get stuck, encounter an issue you cannot solve (like a CAPTCHA), 
      or need clarification, use the `ask_human_via_console` tool.
    - For complex tasks, you can collaborate with other agents. Use 
      `list_available_agents` to see your team members and `send_message` to 
      communicate with them.
    Remember to manage your terminal sessions. You can create new sessions 
    and run commands in them.
    """

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Developer Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


@api_keys_required(
    [
        (None, 'GOOGLE_API_KEY'),
        (None, 'SEARCH_ENGINE_ID'),
        (None, 'EXA_API_KEY'),
    ]
)
@traceroot.trace()
def search_agent_factory(
    model: BaseModelBackend,
    task_id: str,
):
    r"""Factory for creating a search agent, based on user-provided code
    structure.
    """
    # Generate a unique identifier for this agent instance
    agent_id = str(uuid.uuid4())[:8]

    custom_tools = [
        "browser_open",
        "browser_close",
        "browser_click",
        "browser_type",
        "browser_back",
        "browser_forward",
        "browser_switch_tab",
        "browser_enter",
        "browser_get_som_screenshot",
        "browser_visit_page",
        "browser_scroll",
    ]
    web_toolkit_custom = HybridBrowserToolkit(
        headless=False,
        enabled_tools=custom_tools,
        browser_log_to_file=True,
        stealth=True,
        session_id=agent_id,
        cache_dir=WORKING_DIRECTORY,
        default_start_url="https://search.brave.com/",
    )

    tools = [
        *web_toolkit_custom.get_tools(),
        TerminalToolkit().shell_exec,
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        NoteTakingToolkit().append_note,
        *Crawl4AIToolkit().get_tools(),
        SearchToolkit().search_exa,
        SearchToolkit().search_google,
        SearchToolkit().search_bing,
    ]

    system_message = f"""You are a helpful assistant that can search the web, 
    extract webpage content, simulate browser actions, and provide relevant 
    information to solve the given task.

    **CRITICAL**: You MUST NOT answer from your own knowledge. All information
    MUST be sourced from the web using the available tools. If you don't know
    something, find it out using your tools.

    You are now working in `{WORKING_DIRECTORY}`. All your work
    related to local operations should be done in that directory.

    ### Mandatory Instructions
    1.  **Inform the User**: You MUST use the `send_message_to_user` tool to
        inform the user of every decision and action you take. Your message
        must include a short title and a one-sentence description.
    2.  **Take Detailed Notes**: You MUST use the `append_note` tool to
        record your findings. Ensure notes are detailed, well-organized,
        and include source URLs. Do not overwrite notes unless summarizing;
        append new information. Your notes are crucial for the Document
        Agent.

    ### Web Search Workflow
    1.  **Initial Search**: Start with a search engine like `search_google` or
        `search_bing` to get a list of relevant URLs for your research if
        available, the URLs here will be used for `visit_page`.
    2.  **Browser-Based Exploration**: Use the rich browser related toolset to
        investigate websites.
        - **Navigation and Exploration**: Use `visit_page` to open a URL.
          `visit_page` provides a snapshot of currently visible interactive
          elements, not the full page text. To see more content on long
          pages, you MUST use the `scroll(direction='down')` tool. Repeat
          scrolling to ensure you have covered the entire page. Navigate
          with `click`, `back`, and `forward`. Manage multiple pages with
          `switch_tab`.
        - **Analysis**: Use `get_som_screenshot` to understand the page layout
          and identify interactive elements. Since this is a heavy operation,
          only use it when visual analysis is necessary.
        - **Interaction**: Use `type` to fill out forms and `enter` to submit
          or confirm search.
    3.  **Detailed Content Extraction**: Prioritize using the scraping tools
        from `Crawl4AIToolkit` for in-depth information gathering from a
        webpage.
    4.  **Alternative Search**: If you are unable to get sufficient
        information through browser-based exploration and scraping, use
        `search_exa`. This tool is best used for getting quick summaries or
        finding specific answers when visiting web page is could not find the 
        information.

    ### Guidelines and Best Practices
    - **URL Integrity**: You MUST only use URLs from trusted sources (e.g.,
      search engine results or links on visited pages). NEVER invent or
      guess URLs.
    - **Thoroughness**: If a search query is complex, break it down. If a
      snippet is unhelpful but the URL seems authoritative, visit the page.
      Check subpages for more information.
    - **Local File Operations**: You can use `shell_exec` to perform 
      terminal commands within your working directory, such as listing files 
      (`ls`) or checking file content (`cat`).
    - **Persistence**: If one method fails, try another. Combine search,
      scraper, and browser tools for comprehensive information gathering.
    - **Collaboration**: Communicate with other agents using `send_message`
      when you need help. Use `list_available_agents` to see who is
      available.
    - **Clarity**: In your response, you should mention the URLs you have
      visited and processed.

    ### Handling Obstacles
    - When encountering verification challenges (like login, CAPTCHAs or 
    robot checks), you MUST request help using the human toolkit.
"""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Search Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


@traceroot.trace()
def document_agent_factory(
    model: BaseModelBackend,
    task_id: str,
    # google_drive_mcp_toolkit: GoogleDriveMCPToolkit,
):
    r"""Factory for creating a document agent, based on user-provided code
    structure."""
    tools = [
        *FileWriteToolkit().get_tools(),
        *PPTXToolkit().get_tools(),
        # *google_drive_mcp_toolkit.get_tools(),
        # *RetrievalToolkit().get_tools(),
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        *MarkItDownToolkit().get_tools(),
        *ExcelToolkit().get_tools(),
        NoteTakingToolkit().read_note,
        SearchToolkit().search_exa,
        *TerminalToolkit().get_tools(),
    ]

    system_message = f"""You are a Document Processing Assistant specialized 
    in creating, modifying, and managing various document formats. You MUST 
    use the `send_message_to_user` tool to inform the user of every decision 
    and action you take. Your message must include a short title and a 
    one-sentence description. This is a mandatory part of your workflow.

    You are now working in `{WORKING_DIRECTORY}`. All your work
    related to local operations should be done in that directory.

    Your capabilities include:

    1. Information Gathering:
       - Before creating any document, you MUST use the `read_note` tool to 
       get all the information gathered by the Search Agent.
       - The notes contain all the raw data, findings, and sources you need 
       to complete your work.
       - You can communicate with other agents using messaging tools when you 
       need additional information. Use `list_available_agents` to see 
       available team members and `send_message` to request specific data or 
       clarifications.

    2. Document Creation & Editing:
       - Create and write to various file formats including Markdown (.md), 
       Word documents (.docx), PDFs, CSV files, JSON, YAML, and HTML
       - Apply formatting options including custom encoding, font styles, and 
       layout settings
       - Modify existing files with automatic backup functionality
       - Support for mathematical expressions in PDF documents through LaTeX 
       rendering

    3. PowerPoint Presentation Creation:
       - Create professional PowerPoint presentations with title slides and 
       content slides
       - Format text with bold and italic styling
       - Create bullet point lists with proper hierarchical structure
       - Support for step-by-step process slides with visual indicators
       - Create tables with headers and rows of data
       - Support for custom templates and slide layouts

    4. Excel Spreadsheet Management:
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

    5. Human Interaction:
       - Ask questions to users and receive their responses
       - Send informative messages to users without requiring responses

    6. Terminal and File System:
       - You have access to a full suite of terminal tools to interact with 
       the file system within your working directory (`{WORKING_DIRECTORY}`).
       - You can execute shell commands (`shell_exec`), list files, and manage 
       your workspace as needed to support your document creation tasks.

    When working with documents, you should:
    - Suggest appropriate file formats based on content requirements
    - Maintain proper formatting and structure in all created documents
    - Provide clear feedback about document creation and modification processes
    - Ask clarifying questions when user requirements are ambiguous
    - Recommend best practices for document organization and presentation
    - For Excel files, always provide clear data structure and organization
    - When creating spreadsheets, consider data relationships and use 
    appropriate sheet naming conventions

    Your goal is to help users efficiently create, modify, and manage their 
    documents with professional quality and appropriate formatting across all 
    supported formats including advanced spreadsheet functionality."""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Document Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


@traceroot.trace()
def multi_modal_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a multi modal agent, based on user-provided code
    structure."""
    tools = [
        *VideoDownloaderToolkit().get_tools(),
        *AudioAnalysisToolkit().get_tools(),
        *ImageAnalysisToolkit().get_tools(),
        *OpenAIImageToolkit(
            model="dall-e-3",
            response_format="b64_json",
            size="1024x1024",
            quality="standard",
        ).get_tools(),
        send_message_to_user,
        HumanToolkit().ask_human_via_console,
        SearchToolkit().search_exa,
        *TerminalToolkit().get_tools(),
    ]

    system_message = f"""You are a Multi-Modal Processing Assistant 
    specialized in analyzing and generating various types of media content. 
    You MUST use the `send_message_to_user` tool to inform the user of every 
    decision and action you take. Your message must include a short title and 
    a one-sentence description. This is a mandatory part of your workflow.

    You are now working in `{WORKING_DIRECTORY}`. All your work
    related to local operations should be done in that directory.

    Your capabilities include:

    1. Video & Audio Analysis:
       - Download videos from URLs for analysis.
       - Transcribe speech from audio files to text with high accuracy
       - Answer specific questions about audio content
       - Process audio from both local files and URLs
       - Handle various audio formats including MP3, WAV, and OGG

    2. Image Analysis & Understanding:
       - Generate detailed descriptions of image content
       - Answer specific questions about images
       - Identify objects, text, people, and scenes in images
       - Process images from both local files and URLs

    3. Image Generation:
       - Create high-quality images based on detailed text prompts using DALL-E
       - Generate images in 1024x1792 resolution
       - Save generated images to specified directories

    4. Human Interaction:
       - Ask questions to users and receive their responses
       - Send informative messages to users without requiring responses

    5. Agent Communication:
       - Communicate with other agents using messaging tools when 
       collaboration is needed. Use `list_available_agents` to see available 
       team members and `send_message` to coordinate with them, especially 
       when you need to share analysis results or request additional 
       processing capabilities.

    6. File Management:
       - You can use terminal tools to manage files within your working
       directory (`{WORKING_DIRECTORY}`). This is useful for listing
       downloaded media or organizing generated images.

    When working with multi-modal content, you should:
    - Provide detailed and accurate descriptions of media content
    - Extract relevant information based on user queries
    - Generate appropriate media when requested
    - Explain your analysis process and reasoning
    - Ask clarifying questions when user requirements are ambiguous

    Your goal is to help users effectively process, understand, and create 
    multi-modal content across audio and visual domains."""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Multi Modal Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


@traceroot.trace()
def social_medium_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a social medium agent."""
    return ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Social Medium Agent",
            content=f"""
You are a Social Media Management Assistant with comprehensive capabilities 
across multiple platforms. You MUST use the `send_message_to_user` tool to 
inform the user of every decision and action you take. Your message must 
include a short title and a one-sentence description. This is a mandatory 
part of your workflow.


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
   files needed for posting.

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
            *WhatsAppToolkit().get_tools(),
            *TwitterToolkit().get_tools(),
            *LinkedInToolkit().get_tools(),
            *RedditToolkit().get_tools(),
            *NotionToolkit().get_tools(),
            *SlackToolkit().get_tools(),
            send_message_to_user,
            HumanToolkit().ask_human_via_console,
            SearchToolkit().search_exa,
            *TerminalToolkit().get_tools(),
        ],
    )


@traceroot.trace()
async def main():
    # google_drive_mcp_toolkit = GoogleDriveMCPToolkit(
    #     credentials_path="path/to/credentials.json"
    # )

    # Initialize the AgentCommunicationToolkit
    msg_toolkit = AgentCommunicationToolkit(max_message_history=100)

    # await google_drive_mcp_toolkit.connect()

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
        f"You are a helpful coordinator. You MUST use the "
        f"`send_message_to_user` tool to inform the user of every "
        f"decision and action you take. Your message must include a short "
        f"title and a one-sentence description. This is a mandatory part "
        f"of your workflow. You are now working in "
        f"`{WORKING_DIRECTORY}`. "
        "All your work related to local operations should be done in that "
        "directory.",
        model=model_backend_reason,
        tools=[
            send_message_to_user,
        ],
    )
    task_agent = ChatAgent(
        f"You are a helpful task planner. You MUST use the "
        f"`send_message_to_user` tool to inform the user of every decision "
        f"and action you take. Your message must include a short title and "
        f"a one-sentence description. This is a mandatory part of your "
        f"workflow. You are now working in `{WORKING_DIRECTORY}`. "
        "All your work related to local operations should be done in that "
        "directory.",
        model=model_backend_reason,
        tools=[
            send_message_to_user,
        ],
    )
    new_worker_agent = ChatAgent(
        f"You are a helpful worker. You MUST use the "
        f"`send_message_to_user` tool to inform the user of every "
        f"decision and action you take. Your message must include a short "
        f"title and a one-sentence description. This is a mandatory part "
        f"of your workflow. You are now working in "
        f"`{WORKING_DIRECTORY}` All your work related to local "
        "operations should be done in that "
        "directory. You can also communicate with other agents "
        "using messaging tools - use `list_available_agents` to see "
        "available team members and `send_message` to coordinate work "
        "and ask for help when needed.",
        model=model_backend,
        tools=[
            send_message_to_user,
            HumanToolkit().ask_human_via_console,
        ],
    )

    # Create agents using factory functions
    search_agent = search_agent_factory(model_backend, task_id)
    developer_agent = developer_agent_factory(
        model_backend,
        task_id,
    )
    document_agent = document_agent_factory(
        model_backend,
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
        "execute code, run terminal commands, and verify solutions to "
        "complete tasks.",
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
            go to amazon and find a popular product, 
            check the comments and reviews, 
            and then write a report about the product.
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
