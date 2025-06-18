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

from camel.agents.chat_agent import ChatAgent
from camel.loaders import Firecrawl
from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks.task import Task
from camel.toolkits import (
    AudioAnalysisToolkit,
    CodeExecutionToolkit,
    DalleToolkit,
    FileWriteToolkit,
    FunctionTool,
    HumanToolkit,
    ImageAnalysisToolkit,
    LinkedInToolkit,
    NotionToolkit,
    PlaywrightMCPToolkit,
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
        *HumanToolkit().get_tools(),
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


async def search_agent_factory(
    model: BaseModelBackend,
    task_id: str,
    playwright_toolkit: PlaywrightMCPToolkit,
):
    r"""Factory for creating a search agent, based on user-provided code
    structure."""
    search_toolkits = SearchToolkit()
    # browser_toolkits = AsyncBrowserToolkit()
    terminal_toolkits = TerminalToolkit()
    human_toolkits = HumanToolkit()
    tools = [
        FunctionTool(search_toolkits.search_wiki),
        FunctionTool(search_toolkits.search_google),
        FunctionTool(search_toolkits.search_bing),
        FunctionTool(search_toolkits.search_baidu),
        *playwright_toolkit.get_tools(),
        # *browser_toolkits.get_tools(),
        *terminal_toolkits.get_tools(),
        *human_toolkits.get_tools(),
        Firecrawl().scrape,
    ]

    system_message = """You are a helpful assistant that can search the web, 
    extract webpage content, simulate browser actions, and provide relevant 
    information to solve the given task.
    Keep in mind that:
    - Do not be overly confident in your own knowledge. Searching can provide 
    a broader perspective and help validate existing knowledge.  
    - If one way fails to provide an answer, try other ways or methods. The 
    answer does exist.
    - When encountering verification challenges (like login, CAPTCHAs or robot 
    checks), you MUST request help using the human toolkit.
    - If the search snippet is unhelpful but the URL comes from an 
    authoritative source, try visit the website for more details.  
    - For the page you have visited, you should check the subpages of the page 
    to see if it can provide more information to solve the task. 
    - When looking for specific numerical values (e.g., dollar amounts), 
    prioritize reliable sources and avoid relying only on search snippets.  
    - When solving tasks that require web searches, check Wikipedia first 
    before exploring other websites.  
    - You can also simulate browser actions to get more information or verify 
    the information you have found.
    - Browser simulation is also helpful for finding target URLs. Browser 
    simulation operations do not necessarily need to find specific answers, 
    but can also help find web page URLs that contain answers (usually 
    difficult to find through simple web searches). You can find the answer to 
    the question by performing subsequent operations on the URL, such as 
    extracting the content of the webpage.
    - Do not solely rely on browser simulation to find the 
    answer, you should combine search tools, scraper tools and browser 
    simulation to comprehensively process web page information. Some content 
    may need to do browser simulation to get.
    - In your response, you should mention the urls you have visited and 
    processed.

Here are some tips that help you perform web search:
- Never add too many keywords in your search query! Some detailed results need 
    to perform browser interaction to get, not using search toolkit.
- If the question is complex, search results typically do not provide precise 
    answers. It is not likely to find the answer directly using search toolkit 
    only, the search query should be concise and focuses on finding official 
    sources rather than direct answers.
    For example, as for the question "What is the maximum length in meters of 
    #9 in the first National Geographic short on YouTube that was ever 
    released according to the Monterey Bay Aquarium website?", your first 
    search term must be coarse-grained like "National Geographic YouTube" to 
    find the youtube website first, and then try other fine-grained search 
    terms step-by-step to find more urls.
- The results you return do not have to directly answer the original question, 
    you only need to collect relevant information.
    
    """

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Document Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


def document_agent_factory(model: BaseModelBackend, task_id: str):
    r"""Factory for creating a document agent, based on user-provided code
    structure."""
    tools = [
        *FileWriteToolkit().get_tools(),
        *PPTXToolkit().get_tools(),
        # *RetrievalToolkit().get_tools(),
        *HumanToolkit().get_tools(),
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
        *VideoDownloaderToolkit().get_tools(),
        *AudioAnalysisToolkit().get_tools(),
        *ImageAnalysisToolkit().get_tools(),
        *DalleToolkit().get_tools(),
        *HumanToolkit().get_tools(),
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
            *WhatsAppToolkit().get_tools(),
            *TwitterToolkit().get_tools(),
            *LinkedInToolkit().get_tools(),
            *RedditToolkit().get_tools(),
            *NotionToolkit().get_tools(),
            *SlackToolkit().get_tools(),
            *HumanToolkit().get_tools(),
        ],
    )


async def main():
    playwright_toolkit = PlaywrightMCPToolkit(timeout=60)  # Create instance
    try:
        await playwright_toolkit.connect()  # Connect the instance

        # Create a single model backend for all agents
        model_backend = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1_MINI,
            # model_config_dict={
            #     "max_tokens": 64000,
            # }
        )

        model_backend_reason = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4_1_MINI,
            # model_config_dict={
            #     "max_tokens": 64000,
            # }
        )

        task_id = 'workforce_task'

        # Create agents using factory functions
        search_agent = await search_agent_factory(
            model_backend, task_id, playwright_toolkit
        )
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
            "Search & Information Retrieval Agent", worker=search_agent
        ).add_single_agent_worker(
            "Software Development & Code Generation Agent",
            worker=developer_agent,
        ).add_single_agent_worker(
            "Document Creation & Management Agent", worker=document_agent
        ).add_single_agent_worker(
            "Multi-Modal Content Analysis & Generation Agent",
            worker=multi_modal_agent,
        )

        # specify the task to be solved
        human_task = Task(
            content=(
                """
                I want to read papers about GUI Agent. Please help me find 
                ten papers, check the detailed content of the papers and help 
                me write a comparison report, then create a nice slides(pptx) 
                to introduce the latest research progress of GUI Agent. The 
                slides should be very comprehensive and 
                professional.
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
    finally:
        await playwright_toolkit.disconnect()  # Disconnect the same instance


if __name__ == "__main__":
    asyncio.run(main())
