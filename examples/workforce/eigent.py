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
    """Factory for creating a developer agent."""
    tools = [
        *TerminalToolkit().get_tools(),
        *HumanToolkit().get_tools(),
        *CodeExecutionToolkit().get_tools(),
    ]

    system_message = """You are a helpful assistant that specializes in 
    reasoning and coding, and can think step by step to solve the task. When 
    necessary, you can write python code to solve the task. If you have 
    written code, do not forget to execute the code. Never generate codes like 
    'example code', your code should be able to fully solve the task. You can 
    also leverage multiple libraries, such as requests, BeautifulSoup, re, 
    pandas, etc, to solve the task. For processing excel files, you should 
    write codes to process them."""

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
    """Factory for creating a search agent, based on user-provided code
    structure."""
    search_toolkits = SearchToolkit()
    # browser_toolkits = AsyncBrowserToolkit()
    terminal_toolkits = TerminalToolkit()
    human_toolkits = HumanToolkit()
    tools = [
        FunctionTool(search_toolkits.search_wiki),
        # FunctionTool(search_toolkits.search_duckduckgo),
        # FunctionTool(search_toolkits.search_bing),
        # FunctionTool(search_toolkits.search_baidu),
        *playwright_toolkit.get_tools(),  # Use passed toolkit
        # *browser_toolkits.get_tools(),
        *terminal_toolkits.get_tools(),
        *human_toolkits.get_tools(),
    ]

    system_message = """You are a helpful assistant that can search the web, 
    extract webpage content, simulate browser actions, and provide relevant 
    information to solve the given task.
    Keep in mind that:
    - Do not be overly confident in your own knowledge. Searching can provide 
    a broader perspective and help validate existing knowledge.  
    - If one way fails to provide an answer, try other ways or methods. The 
    answer does exists.
    - If the search snippet is unhelpful but the URL comes from an 
    authoritative source, try visit the website for more details.  
    - When looking for specific numerical values (e.g., dollar amounts), 
    prioritize reliable sources and avoid relying only on search snippets.  
    - When solving tasks that require web searches, check Wikipedia first 
    before 'exploring other websites.  
    - You can also simulate browser actions to get more information or verify 
    the 'information you have found'.
    - Browser simulation is also helpful for finding target URLs. Browser 
    simulation operations do not necessarily need to find specific answers, 
    but can also help find web page URLs that contain answers (usually 
    difficult to find through simple web searches). You can find the answer to 
    the question by performing subsequent operations on the URL, such as 
    extracting the content of the webpage.
    - Do not solely rely on document tools or browser simulation to find the 
    answer, you should combine document tools and browser simulation to 
    comprehensively process web page information. Some content may need to do 
    browser simulation to get, or some content is rendered by javascript.
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
    you only need to collect relevant information."""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Document Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


def document_agent_factory(model: BaseModelBackend, task_id: str):
    """Factory for creating a document agent, based on user-provided code
    structure."""
    tools = [
        *FileWriteToolkit().get_tools(),
        *PPTXToolkit().get_tools(),
        # *RetrievalToolkit().get_tools(),
        *HumanToolkit().get_tools(),
    ]

    system_message = """You are a helpful assistant that can process documents 
    and multi modal data, such as images, audio, and video, you could also 
    generate documents including pptx, pdf, md, etc."""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Document Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


def multi_modal_agent_factory(model: BaseModelBackend, task_id: str):
    """Factory for creating a multi modal agent, based on user-provided code
    structure."""
    tools = [
        *VideoDownloaderToolkit().get_tools(),
        *AudioAnalysisToolkit().get_tools(),
        *ImageAnalysisToolkit().get_tools(),
        *DalleToolkit().get_tools(),
        *HumanToolkit().get_tools(),
    ]

    system_message = """You are a helpful assistant that can process multi 
    modal data, such as images, audio, and video."""

    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Multi Modal Agent",
            content=system_message,
        ),
        model=model,
        tools=tools,
    )


def social_medium_agent_factory(model: BaseModelBackend, task_id: str):
    """Factory for creating a social medium agent."""
    return ChatAgent(
        BaseMessage.make_assistant_message(
            role_name="Social Medium Agent",
            content="""You are a helpful assistant specializing in social 
            media management, content creation, and interaction across various 
            platforms. You can assist with tasks on WhatsApp, Twitter, 
            LinkedIn, Reddit, Notion, Slack, Discord, and leverage Google 
            Suite tools for productivity.""",
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
    playwright_toolkit = PlaywrightMCPToolkit()  # Create instance
    try:
        await playwright_toolkit.connect()  # Connect the instance

        # Create a single model backend for all agents
        model_backend = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
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

        workforce = Workforce(
            'A workforce',
            graceful_shutdown_timeout=30.0,  # 30 seconds for debugging
            share_memory=True,
        )

        workforce.add_single_agent_worker(
            "A search agent", worker=search_agent
        ).add_single_agent_worker(
            "A developer agent", worker=developer_agent
        ).add_single_agent_worker(
            "A document agent", worker=document_agent
        ).add_single_agent_worker(
            "A multi modal agent", worker=multi_modal_agent
        )

        # specify the task to be solved
        human_task = Task(
            content=(
                """I want to read papers about GUI Agent. Please help me find 
                ten papers, check the detailed content of the papers and help 
                me write a comparison report, then create a nice slides to 
                introduce the latest research progress of GUI Agent."""
            ),
            id='0',
        )

        task = await workforce.process_task(human_task)
        print('Final Result of Original task:\n', task.result)
    finally:
        await playwright_toolkit.disconnect()  # Disconnect the same instance


if __name__ == "__main__":
    asyncio.run(main())
