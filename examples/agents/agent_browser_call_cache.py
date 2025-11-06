"""Example of creating a search agent with browser capabilities and tool call caching."""
import os
import uuid


from camel.logger import get_logger

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.toolkits import (
    ToolkitMessageIntegration, HybridBrowserToolkit)
from camel.types import ModelPlatformType, ModelType
from camel.memories import BrowserChatHistoryMemory


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
        "browser_select",
        "browser_close",
        "browser_back",
        "browser_forward",
        "browser_click",
        "browser_type",
        "browser_enter",
        "browser_switch_tab",
        "browser_visit_page",
        "browser_get_page_snapshot",
    ]
    USER_DATA_DIR = os.getenv("CAMEL_BROWSER_USER_DATA_DIR", "user_data")
    web_toolkit_custom = HybridBrowserToolkit(
        headless=False,
        enabled_tools=custom_tools,
        browser_log_to_file=True,
        stealth=True,
        session_id=agent_id,
        viewport_limit=False,
        cache_dir=WORKING_DIRECTORY,
        default_start_url="about:blank",
        user_data_dir=USER_DATA_DIR,
        log_dir=os.getenv("CAMEL_BROWSER_USER_LOG_DIR", "browser_logs"),
    )

    # Add messaging to toolkits
    web_toolkit_custom = message_integration.register_toolkits(
        web_toolkit_custom
    )

    tools = [
        *web_toolkit_custom.get_tools(),
    ]

    system_message = """
<role>
You are a Senior Research Analyst, a key member of a multi-agent team. Your 
primary responsibility is to conduct expert-level web research to gather, 
analyze, and document information required to solve the user's task. You 
operate with precision, efficiency, and a commitment to data quality.
</role>

<mandatory_instructions>
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
    Your notes should be a detailed and complete record of the information
    you have discovered. High-quality, detailed notes are essential for the
    team's success.

- When you complete your task, your final response must be a comprehensive
    summary of your findings, presented in a clear, detailed, and
    easy-to-read format. Avoid using markdown tables for presenting data;
    use plain text formatting instead.
<mandatory_instructions>

<capabilities>
Your capabilities include:
- Search and get information from the web using the search tools.
- Use the rich browser related toolset to investigate websites.
</capabilities>

<web_search_workflow>
- Browser-Based Exploration: Use the rich browser related toolset to
    investigate websites.
    
    - **Navigation and Exploration**: Use `browser_visit_page` to open a URL.
        `browser_visit_page` provides a snapshot of currently visible 
        interactive elements, not the full page text. To see more content on 
        long pages,  Navigate with `browser_click`, `browser_back`, and 
        `browser_forward`. Manage multiple pages with `browser_switch_tab`.
    - **Analysis**: Use `browser_get_som_screenshot` to understand the page 
        layout and identify interactive elements. Since this is a heavy 
        operation, only use it when visual analysis is necessary.
    - **Interaction**: Use `browser_type` to fill out forms and 
        `browser_enter` to submit or confirm search.

- In your response, you should mention the URLs you have visited and processed.

- When encountering verification challenges (like login, CAPTCHAs or
    robot checks), you MUST request help using the human toolkit.
- When encountering cookies page, you need to click accept all.
</web_search_workflow>
"""
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Search Agent",
            content=system_message,
        ),
        model=model,
        enable_tool_output_cache=False,
        toolkits_to_register_agent=[web_toolkit_custom],
        tools=tools,
        memory=BrowserChatHistoryMemory
    )

    # Return both agent and toolkit for cleanup purposes
    return agent, web_toolkit_custom


async def main():
    """Main function to run the search agent with browser capabilities and
    tool call caching.
    """
    model_backend = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1,
        model_config_dict={
            "stream": False,
        },
    )
    search_agent, browser_toolkit = search_agent_factory(
        model_backend, task_id=1
    )
    try:
        task_message = (
            "web: https://en.wikipedia.org/wiki/Agent"
            "got this web and get the summary of it"
        )
        await search_agent.astep(input_message=task_message)
        context = search_agent.memory.get_context()
        # there will be 7 messages context: ([7*messages], token_count)
        
        print("\n--- Agent Pruned Memory Context ---")
        # 0, system 
        print(context[0][0]["content"])
        # 1, user
        print(context[0][1]["content"])
        # 2, browse tool call
        print(context[0][2]["content"])
        # 3, browser content response
        print(context[0][3]["content"])
        # 4, snapeshot tool call
        print(context[0][4]["content"])
        # 5, snapshot response
        print(context[0][5]["content"])
        # 6, agent final response
        print(context[0][6]["content"])
    finally:
        # IMPORTANT: Close browser after each task to prevent resource leaks
        if browser_toolkit is not None:
            try:
                print(f"\n--- Closing Browser for Task ---")
                await browser_toolkit.browser_close()
                print("Browser closed successfully.")
            except Exception as e:
                print(f"Error closing browser: {e}")


if __name__ == "__main__":
    import asyncio
    logger.info("Starting Search Agent with Browser Call Cache...")
    asyncio.run(main())
    logger.info("Search Agent run completed.")
