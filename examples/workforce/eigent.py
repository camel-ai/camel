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

# ---------------------------------------------------------
# Enable detailed logging for debugging/demo purposes
# ---------------------------------------------------------
from camel.logger import set_log_level, set_log_file

# Console level: DEBUG; File log for later inspection
set_log_level("DEBUG")  # Change to "INFO" if too verbose
set_log_file("eigent_runtime.log")

from camel.agents.chat_agent import ChatAgent
from camel.loaders import Crawl4AI
from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import (
    AudioAnalysisToolkit,
    BrowserNonVisualToolkit,
    CodeExecutionToolkit,
    DalleToolkit,
    FileWriteToolkit,
    FunctionTool,
    HumanToolkit,
    ImageAnalysisToolkit,
    LinkedInToolkit,
    NotionToolkit,
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


def developer_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a developer agent."""
    tools = [
        *TerminalToolkit().get_tools(),
        HumanToolkit().ask_human_via_console,
        *TerminalToolkit(clone_current_env=True).get_tools(),
        *CodeExecutionToolkit().get_tools(),
    ]

    system_message = """You are a skilled coding assistant with DIRECT CODE 
    EXECUTION CAPABILITIES. You can:
    - WRITE AND EXECUTE code in real-time to solve tasks
    - RUN terminal commands to install packages, process files, or test 
    functionality
    - VERIFY your solutions through immediate execution and testing
    - UTILIZE any Python libraries (requests, BeautifulSoup, pandas, etc.) 
    needed for efficient solutions
    - IMPLEMENT complete, production-ready code rather than theoretical 
    examples
    - DEMONSTRATE results with proper error handling and practical 
    implementation
    - If there's dependency issues when you try to execute code, you should 
    use the terminal toolkit to install the dependencies."""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Developer Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


class SearchAgent(ChatAgent):
    """SearchAgent with browser & terminal toolkits that recreates toolkits
    on each clone so that every cloned agent owns an independent Playwright
    browser session.
    """

    def __init__(self, model: BaseModelBackend):
        # Construct fresh toolkits for *this* agent
        browser_toolkit = BrowserNonVisualToolkit(headless=False)
        terminal_toolkit = TerminalToolkit()
        human_ask = HumanToolkit().ask_human_via_console

        tools = [
            *browser_toolkit.get_tools(),
            *terminal_toolkit.get_tools(),
            human_ask,
        ]

        system_message = BaseMessage.make_assistant_message(
            role_name="Document Agent",
            content="You are a helpful assistant that can search the web, "
            "extract webpage content, simulate browser actions, and provide "
            "relevant information to solve the given task."
        )

        super().__init__(
            system_message=system_message,
            model=model,
            tools=tools,
        )


    # Override clone to ensure a brand-new BrowserNonVisualToolkit per clone
    def clone(self, with_memory: bool = False):  # type: ignore[override]
        cloned = super().clone(with_memory=with_memory)

        # Remove existing internal tools copied from parent
        cloned._internal_tools = {}

        # Re-create toolkits so that clone gets its own browser session
        browser_toolkit = BrowserNonVisualToolkit(headless=False)
        terminal_toolkit = TerminalToolkit()
        human_ask = HumanToolkit().ask_human_via_console

        for tool in [
            *browser_toolkit.get_tools(),
            *terminal_toolkit.get_tools(),
            human_ask,
        ]:
            cloned.add_tool(tool)

        return cloned


def search_agent_factory(
    model: BaseModelBackend,
    task_id: str,
):
    # Simply return a new instance of our custom SearchAgent class.
    return SearchAgent(model=model)


def document_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a document agent, based on user-provided code
    structure."""
    tools = [
        *FileWriteToolkit().get_tools(),
        # *PPTXToolkit().get_tools(),
        # *RetrievalToolkit().get_tools(),
        HumanToolkit().ask_human_via_console,
    ]

    system_message = """You are a Document Processing Assistant specialized in 
    creating, modifying, and managing various document formats. Your 
    capabilities include:

    1. Document Creation & Editing:
       - Create and write to various file formats including Markdown (.md), 
       Word documents (.docx), PDFs, CSV files, JSON, YAML, and HTML
       - Apply formatting options including custom encoding, font styles, and 
       layout settings
       - Modify existing files with automatic backup functionality
       - Support for mathematical expressions in PDF documents through LaTeX 
       rendering

    2. PowerPoint Presentation Creation:
       - Create professional PowerPoint presentations with title slides and 
       content slides
       - Format text with bold and italic styling
       - Create bullet point lists with proper hierarchical structure
       - Support for step-by-step process slides with visual indicators
       - Create tables with headers and rows of data
       - Support for custom templates and slide layouts

    3. Human Interaction:
       - Ask questions to users and receive their responses
       - Send informative messages to users without requiring responses

    When working with documents, you should:
    - Suggest appropriate file formats based on content requirements
    - Maintain proper formatting and structure in all created documents
    - Provide clear feedback about document creation and modification processes
    - Ask clarifying questions when user requirements are ambiguous
    - Recommend best practices for document organization and presentation

    Your goal is to help users efficiently create, modify, and manage their 
    documents with professional quality and appropriate formatting."""

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
    tools = [
        # *VideoDownloaderToolkit().get_tools(),
        # *AudioAnalysisToolkit().get_tools(),
        # *ImageAnalysisToolkit().get_tools(),
        # *DalleToolkit().get_tools(),
        HumanToolkit().ask_human_via_console,
    ]

    system_message = """You are a Multi-Modal Processing Assistant specialized 
    in analyzing and generating various types of media content. Your 
    capabilities include:

    1. Audio Analysis & Processing:
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


def social_medium_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a social medium agent."""
    return ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Social Medium Agent",
            content="""You are a Social Media Management Assistant with 
            comprehensive capabilities across multiple platforms. Your 
            integrated toolkits enable you to:

1. WhatsApp Business Management (WhatsAppToolkit):
   - Send text messages to customers via the WhatsApp Business API
   - Send template messages for standardized communications
   - Retrieve business profile information

2. Twitter Account Management (TwitterToolkit):
   - Create tweets with text content (respecting character limits)
   - Create tweets with polls or as quote tweets
   - Delete existing tweets
   - Retrieve user profile information

3. LinkedIn Professional Networking (LinkedInToolkit):
   - Create posts on LinkedIn (respecting character limits)
   - Delete existing posts (with user confirmation)
   - Retrieve authenticated user's profile information

4. Reddit Content Analysis (RedditToolkit):
   - Collect top posts and comments from specified subreddits
   - Perform sentiment analysis on Reddit comments
   - Track keyword discussions across multiple subreddits

5. Notion Workspace Management (NotionToolkit):
   - List all pages in a Notion workspace
   - List all users with access to the workspace
   - Retrieve and extract text content from Notion blocks

6. Slack Workspace Interaction (SlackToolkit):
   - Create new Slack channels (public or private)
   - Join or leave existing channels
   - Send and delete messages in channels
   - Retrieve channel information and message history

7. Human Interaction (HumanToolkit):
   - Ask questions to users via console
   - Send messages to users via console

When assisting users, always:
1. Identify which platform's functionality is needed for the task
2. Check if required API credentials are available before attempting operations
3. Provide clear explanations of what actions you're taking
4. Handle rate limits and API restrictions appropriately
5. Ask clarifying questions when user requests are ambiguous""",
        ),
        model=model,
        tools=[
            # *WhatsAppToolkit().get_tools(),
            # *TwitterToolkit().get_tools(),
            # *LinkedInToolkit().get_tools(),
            # *RedditToolkit().get_tools(),
            # *NotionToolkit().get_tools(),
            # *SlackToolkit().get_tools(),
            HumanToolkit().ask_human_via_console,
        ],
    )


async def main():
    # Create a single model backend for all agents
    model_backend = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1_MINI,
        # model_config_dict={
        #     "max_tokens": 32768,
        # },
    )

    model_backend_reason = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1_MINI,
        # model_config_dict={
        #     "max_tokens": 32768,
        # },
    )

    task_id = 'workforce_task'

    # Create agents using factory functions
    search_agent = search_agent_factory(model_backend, task_id)
    developer_agent = developer_agent_factory(model_backend, task_id)
    document_agent = document_agent_factory(model_backend, task_id)
    multi_modal_agent = multi_modal_agent_factory(model_backend, task_id)
    # social_medium_agent = social_medium_agent_factory(model_backend,
    # task_id)

    # Configure kwargs for all agents to use the same model_backend
    coordinator_agent_kwargs = {"model": model_backend_reason}
    task_agent_kwargs = {"model": model_backend_reason}
    new_worker_agent_kwargs = {"model": model_backend}

    workforce = Workforce(
        'A workforce',
        graceful_shutdown_timeout=30.0,  # 30 seconds for debugging
        share_memory=False,
        coordinator_agent_kwargs=coordinator_agent_kwargs,
        task_agent_kwargs=task_agent_kwargs,
        new_worker_agent_kwargs=new_worker_agent_kwargs,
    )

    workforce.add_single_agent_worker(
        "Search Agent: Can search the web, extract webpage content, "
        "simulate browser actions, and provide relevant information to "
        "solve the given task.",
        worker=search_agent,
    )

    workforce.add_single_agent_worker(
        "Document Agent: A document processing assistant for creating, "
        "modifying, and managing various document formats, including "
        "presentations.",
        worker=document_agent,
    )

    # specify the task to be solved
    human_task = Task(
        content=(
            """
Gather today's headline news from BBC, Washington Post, Google News and CNN.
Each headline can be processed in parallel by the SearchAgent pool.
            """  # noqa: E501
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
