from camel.agents import ChatAgent
from camel.toolkits import SearchToolkit, BrowserToolkit, TerminalToolkit
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def create_unified_agent():
    """创建统一的多功能 Agent"""

    # 初始化工具包
    search_toolkit = SearchToolkit()
    browser_toolkit = BrowserToolkit()
    terminal_toolkit = TerminalToolkit()

    # 组合工具
    all_tools = []
    all_tools.extend(search_toolkit.get_tools())
    all_tools.extend(browser_toolkit.get_tools())
    all_tools.extend(terminal_toolkit.get_tools())

    # 创建模型
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
    )

    # 创建统一 Agent
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="UnifiedAssistant",
            content="""You are a unified assistant with comprehensive capabilities:  
            - Web search using multiple search engines  
            - Web browsing and content extraction    
            - Terminal operations and file management  

            You can help users with research, development, and automation tasks."""
        ),
        model=model,
        tools=all_tools,
    )

    return agent


def main():
    """主函数演示统一 Agent 的使用"""
    agent = create_unified_agent()

    # 示例任务：研究项目并创建报告
    tasks = [
        "Search for information about CAMEL AI framework",
        "Browse the official GitHub repository",
        "Create a summary report and save it to a file"
    ]

    for task in tasks:
        print(f"\n执行任务: {task}")
        response = agent.step(task)
        print(f"响应: {response.msgs[0].content}")


if __name__ == "__main__":
    main()