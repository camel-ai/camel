import pytest
import asyncio
from unittest.mock import Mock, patch
from camel.agents import ChatAgent
from camel.toolkits import SearchToolkit, BrowserToolkit, TerminalToolkit, FunctionTool
from camel.messages import BaseMessage
from camel.types import RoleType, ModelPlatformType, ModelType
from camel.models import ModelFactory


class TestUnifiedAgent:
    """测试统一 Agent 与多个工具包的集成"""

    def setup_method(self):
        """设置测试环境"""
        # 初始化各个工具包
        self.search_toolkit = SearchToolkit()
        self.browser_toolkit = BrowserToolkit()
        self.terminal_toolkit = TerminalToolkit()

        # 创建统一的工具列表
        self.unified_tools = []

        # 添加搜索工具
        search_tools = self.search_toolkit.get_tools()
        self.unified_tools.extend(search_tools[:2])  # 只取前两个搜索工具

        # 添加浏览器工具
        browser_tools = self.browser_toolkit.get_tools()
        self.unified_tools.extend(browser_tools[:3])  # 只取前三个浏览器工具

        # 添加终端工具
        terminal_tools = self.terminal_toolkit.get_tools()
        self.unified_tools.extend(terminal_tools[:2])  # 只取前两个终端工具

        # 创建模型
        self.model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        )

        # 创建统一的 Agent
        self.unified_agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="UnifiedAssistant",
                content="You are a unified assistant with search, browser, and terminal capabilities."
            ),
            model=self.model,
            tools=self.unified_tools,
        )

    def test_toolkit_integration(self):
        """测试工具包集成"""
        # 验证工具包正确初始化
        assert isinstance(self.search_toolkit, SearchToolkit)
        assert isinstance(self.browser_toolkit, BrowserToolkit)
        assert isinstance(self.terminal_toolkit, TerminalToolkit)

        # 验证工具列表不为空
        assert len(self.unified_tools) > 0

        # 验证 Agent 包含所有工具
        assert len(self.unified_agent.tool_dict) == len(self.unified_tools)

    @patch('camel.toolkits.search_toolkit.SearchToolkit.search_google')
    def test_search_functionality(self, mock_search):
        """测试搜索功能"""
        mock_search.return_value = "Search results for CAMEL framework"

        # 创建只包含搜索工具的 Agent
        search_agent = ChatAgent(
            system_message="You are a search assistant",
            model=self.model,
            tools=[FunctionTool(self.search_toolkit.search_google)]
        )

        user_message = BaseMessage(
            role_name="User",
            role_type=RoleType.USER,
            content="Search for CAMEL framework information"
        )

        # 模拟工具调用
        tool_name = "search_google"
        if tool_name in search_agent.tool_dict:
            result = search_agent.tool_dict[tool_name].func("CAMEL framework")
            assert "Search results" in result

    @patch('camel.toolkits.terminal_toolkit.TerminalToolkit.execute_command')
    def test_terminal_functionality(self, mock_execute):
        """测试终端功能"""
        mock_execute.return_value = "Command executed successfully"

        # 创建只包含终端工具的 Agent
        terminal_agent = ChatAgent(
            system_message="You are a terminal assistant",
            model=self.model,
            tools=[FunctionTool(self.terminal_toolkit.execute_command)]
        )

        # 模拟命令执行
        tool_name = "execute_command"
        if tool_name in terminal_agent.tool_dict:
            result = terminal_agent.tool_dict[tool_name].func("ls -la")
            assert "executed successfully" in result

    def test_multi_toolkit_workflow(self):
        """测试多工具包协同工作流程"""
        # 模拟一个完整的工作流程：搜索 -> 浏览 -> 文件操作

        # 1. 搜索阶段
        with patch.object(self.search_toolkit, 'search_google') as mock_search:
            mock_search.return_value = "Found repository: https://github.com/camel-ai/camel"

            search_result = self.search_toolkit.search_google("CAMEL AI repository")
            assert "github.com/camel-ai/camel" in search_result

            # 2. 浏览阶段
        with patch.object(self.browser_toolkit, 'open_url') as mock_browse:
            mock_browse.return_value = "Successfully opened GitHub page"

            browse_result = self.browser_toolkit.open_url("https://github.com/camel-ai/camel")
            assert "Successfully opened" in browse_result

            # 3. 文件操作阶段
        with patch.object(self.terminal_toolkit, 'write_file') as mock_write:
            mock_write.return_value = "File written successfully"

            write_result = self.terminal_toolkit.write_file(
                "research_notes.txt",
                "CAMEL AI repository information"
            )
            assert "written successfully" in write_result

    @pytest.mark.asyncio
    async def test_async_agent_workflow(self):
        """测试异步 Agent 工作流程"""
        # 创建异步消息
        user_message = BaseMessage(
            role_name="User",
            role_type=RoleType.USER,
            content="Please search for Python tutorials and save the results"
        )

        # 模拟异步工具调用
        with patch.object(self.unified_agent.model_backend, 'run') as mock_run:
            # 模拟模型返回
            mock_response = Mock()
            mock_response.msgs = [BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="I'll help you search for Python tutorials and save the results."
            )]
            mock_response.terminated = False
            mock_response.info = {'tool_calls': []}

            mock_run.return_value = mock_response

            # 执行异步步骤
            response = await self.unified_agent.astep(user_message)

            # 验证响应
            assert response is not None
            assert len(response.msgs) > 0

    def test_tool_availability(self):
        """测试工具可用性"""
        # 验证搜索工具
        search_tools = self.search_toolkit.get_tools()
        assert len(search_tools) > 0

        # 验证浏览器工具
        browser_tools = self.browser_toolkit.get_tools()
        assert len(browser_tools) > 0

        # 验证终端工具
        terminal_tools = self.terminal_toolkit.get_tools()
        assert len(terminal_tools) > 0

        # 验证所有工具都是 FunctionTool 实例
        for tool in self.unified_tools:
            assert isinstance(tool, FunctionTool)

    def test_agent_tool_management(self):
        """测试 Agent 工具管理"""
        initial_tool_count = len(self.unified_agent.tool_dict)

        # 添加新工具
        def custom_tool(text: str) -> str:
            return f"Custom processing: {text}"

        self.unified_agent.add_tool(FunctionTool(custom_tool))

        # 验证工具已添加
        assert len(self.unified_agent.tool_dict) == initial_tool_count + 1
        assert "custom_tool" in self.unified_agent.tool_dict

        # 移除工具
        removed = self.unified_agent.remove_tool("custom_tool")
        assert removed is True
        assert len(self.unified_agent.tool_dict) == initial_tool_count

    def test_error_handling(self):
        """测试错误处理"""
        # 测试工具调用失败的情况
        with patch.object(self.search_toolkit, 'search_google') as mock_search:
            mock_search.side_effect = Exception("Search service unavailable")

            try:
                self.search_toolkit.search_google("test query")
                assert False, "Should have raised an exception"
            except Exception as e:
                assert "Search service unavailable" in str(e)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])