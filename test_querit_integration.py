#!/usr/bin/env python3
"""
Querit Search 集成测试脚本

使用方法:
    # 第一步：设置环境变量
    export QUERIT_API_KEY="你的API Key"

    # 第二步：运行测试
    python test_querit_integration.py

测试说明:
    - 层级 1：单元测试（mock，不需要 API Key）
    - 层级 2：真实 API 调用（需要 API Key）
    - 层级 3：与 ChatAgent 集成测试（需要 API Key + OpenAI Key）
"""

import json
import os
import sys

# 确保可以导入 camel
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(label, passed, detail=""):
    icon = "✅" if passed else "❌"
    print(f"  {icon} {label}")
    if detail:
        print(f"     {detail}")


# ============================================================
#  层级 1：单元测试（不需要 API Key，用 mock 模拟）
# ============================================================
def run_unit_tests():
    print_header("层级 1：单元测试（Mock）")

    from unittest.mock import MagicMock, patch

    from camel.toolkits import SearchToolkit

    toolkit = SearchToolkit()

    # 测试 1：方法存在性
    has_method = hasattr(toolkit, 'search_querit')
    print_result("search_querit 方法存在", has_method)

    # 测试 2：已注册到 get_tools
    tool_names = [t.get_function_name() for t in toolkit.get_tools()]
    registered = 'search_querit' in tool_names
    print_result(
        "已注册到 get_tools()",
        registered,
        f"共 {len(tool_names)} 个工具",
    )

    # 测试 3：Mock 基本搜索
    mock_api_response = {
        "took": "100ms",
        "error_code": 200,
        "error_msg": "",
        "search_id": 99999,
        "query_context": {"query": "test"},
        "results": {
            "result": [
                {
                    "url": "https://example.com",
                    "page_age": "2025-01-01T00:00:00Z",
                    "title": "Test Title",
                    "snippet": "Test snippet content",
                    "site_name": "example.com",
                    "site_icon": "https://example.com/favicon.ico",
                },
            ]
        },
    }

    with patch('requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_api_response
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {'QUERIT_API_KEY': 'fake_key'}):
            result = toolkit.search_querit(query="test")

    basic_ok = (
        "results" in result
        and len(result["results"]) == 1
        and result["results"][0]["title"] == "Test Title"
        and result["results"][0]["url"] == "https://example.com"
        and result["took"] == "100ms"
        and result["search_id"] == 99999
    )
    print_result("Mock 基本搜索", basic_ok)

    # 测试 4：Mock 带过滤器搜索
    with patch('requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_api_response
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {'QUERIT_API_KEY': 'fake_key'}):
            toolkit.search_querit(
                query="test",
                site_include=["github.com"],
                time_range="d7",
                country_include=["japan"],
                language_include=["japanese"],
            )

        # 验证发送的 payload
        call_data = json.loads(mock_post.call_args[1]['data'])
        filters_ok = (
            "filters" in call_data
            and call_data["filters"]["sites"]["include"] == ["github.com"]
            and call_data["filters"]["timeRange"]["date"] == "d7"
            and call_data["filters"]["geo"]["countries"]["include"]
            == ["japan"]
            and call_data["filters"]["languages"]["include"] == ["japanese"]
        )
    print_result("Mock 过滤器参数正确传递", filters_ok)

    # 测试 5：Mock 无过滤器时不发送 filters 字段
    with patch('requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_api_response
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {'QUERIT_API_KEY': 'fake_key'}):
            toolkit.search_querit(query="test")

        call_data = json.loads(mock_post.call_args[1]['data'])
        no_filters = "filters" not in call_data
    print_result("无过滤器时 payload 不含 filters 字段", no_filters)

    # 测试 6：Mock HTTP 错误处理
    with patch('requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = 'Unauthorized'
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {'QUERIT_API_KEY': 'bad_key'}):
            result = toolkit.search_querit(query="test")

    http_err_ok = "error" in result and "401" in result["error"]
    print_result("HTTP 错误处理", http_err_ok)

    # 测试 7：Mock API 业务错误（如限流 429）
    with patch('requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "took": "5ms",
            "error_code": 429,
            "error_msg": "Rate limit exceeded",
            "search_id": 0,
            "query_context": {"query": "test"},
            "results": {"result": []},
        }
        mock_post.return_value = mock_resp

        with patch.dict(os.environ, {'QUERIT_API_KEY': 'fake_key'}):
            result = toolkit.search_querit(query="test")

    api_err_ok = (
        "error" in result and "Rate limit exceeded" in result["error"]
    )
    print_result("API 业务错误处理 (429 限流)", api_err_ok)

    # 测试 8：Mock 网络异常
    import requests as req

    with patch('requests.post') as mock_post:
        mock_post.side_effect = req.exceptions.ConnectionError(
            "Network unreachable"
        )

        with patch.dict(os.environ, {'QUERIT_API_KEY': 'fake_key'}):
            result = toolkit.search_querit(query="test")

    net_err_ok = "error" in result and "request failed" in result["error"]
    print_result("网络异常处理", net_err_ok)

    all_passed = all(
        [
            has_method,
            registered,
            basic_ok,
            filters_ok,
            no_filters,
            http_err_ok,
            api_err_ok,
            net_err_ok,
        ]
    )
    return all_passed


# ============================================================
#  层级 2：真实 API 调用（需要 QUERIT_API_KEY）
# ============================================================
def run_api_tests():
    print_header("层级 2：真实 API 调用")

    api_key = os.getenv("QUERIT_API_KEY")
    if not api_key:
        print("  ⏭️  跳过：未设置 QUERIT_API_KEY 环境变量")
        print("  提示：export QUERIT_API_KEY='你的Key' 后再运行")
        return None

    from camel.toolkits import SearchToolkit

    toolkit = SearchToolkit()

    # 测试 1：基本搜索
    print("\n  正在调用 Querit API...")
    result = toolkit.search_querit(
        query="CAMEL-AI multi-agent framework",
        number_of_result_pages=5,
    )

    if "error" in result:
        print_result("基本搜索", False, f"错误: {result['error']}")
        return False

    has_results = (
        "results" in result and len(result["results"]) > 0
    )
    print_result(
        "基本搜索",
        has_results,
        f"返回 {len(result.get('results', []))} 条结果, "
        f"耗时 {result.get('took', 'N/A')}",
    )

    if has_results:
        first = result["results"][0]
        fields_ok = all(
            k in first
            for k in [
                "result_id",
                "title",
                "snippet",
                "url",
                "site_name",
            ]
        )
        print_result("返回字段完整性", fields_ok)
        print(f"     第1条: [{first.get('title', '')}]")
        print(f"            {first.get('url', '')}")

    # 测试 2：带过滤器搜索
    result2 = toolkit.search_querit(
        query="Python programming",
        number_of_result_pages=3,
        language_include=["english"],
        time_range="m1",
    )

    if "error" in result2:
        print_result("过滤器搜索", False, f"错误: {result2['error']}")
    else:
        filter_ok = "results" in result2
        print_result(
            "过滤器搜索",
            filter_ok,
            f"返回 {len(result2.get('results', []))} 条结果",
        )

    # 测试 3：空结果处理
    result3 = toolkit.search_querit(
        query="xyzzy_completely_nonexistent_term_12345",
        number_of_result_pages=3,
    )

    empty_ok = "error" not in result3  # 不应报错，应返回空结果
    print_result(
        "空结果处理（不应报错）",
        empty_ok,
        f"返回 {len(result3.get('results', []))} 条结果",
    )

    return has_results


# ============================================================
#  层级 3：与 ChatAgent 集成（需要 QUERIT_API_KEY + OPENAI_API_KEY）
# ============================================================
def run_agent_tests():
    print_header("层级 3：ChatAgent 集成测试")

    querit_key = os.getenv("QUERIT_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not querit_key:
        print("  ⏭️  跳过：未设置 QUERIT_API_KEY")
        return None
    if not openai_key:
        print("  ⏭️  跳过：未设置 OPENAI_API_KEY")
        print("  提示：此测试需要 OpenAI API Key 来驱动 ChatAgent")
        return None

    from camel.agents import ChatAgent
    from camel.toolkits import FunctionTool, SearchToolkit

    agent = ChatAgent(
        system_message=(
            "You are a helpful assistant. Use the search_querit tool "
            "to find information and answer questions. "
            "Always respond in English."
        ),
        tools=[FunctionTool(SearchToolkit().search_querit)],
    )

    print("\n  正在通过 ChatAgent 调用 Querit 搜索...")
    response = agent.step(
        input_message="What is CAMEL-AI? Search for it and give a brief answer."
    )

    content = response.msgs[0].content if response.msgs else ""
    tool_calls = response.info.get("tool_calls", [])

    has_content = len(content) > 20
    used_tool = any(
        tc.tool_name == "search_querit" for tc in tool_calls
    )

    print_result("Agent 生成了回答", has_content)
    print_result("Agent 调用了 search_querit 工具", used_tool)

    if has_content:
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"\n  Agent 回答预览:\n  {preview}")

    if tool_calls:
        for tc in tool_calls:
            print(
                f"\n  工具调用记录: {tc.tool_name}("
                f"query={tc.args.get('query', 'N/A')})"
            )

    return has_content and used_tool


# ============================================================
#  主函数
# ============================================================
if __name__ == "__main__":
    print("\n🐫 Querit Search Integration - 完整测试")
    print("=" * 60)

    results = {}

    # 层级 1：单元测试
    results["unit"] = run_unit_tests()

    # 层级 2：真实 API
    results["api"] = run_api_tests()

    # 层级 3：Agent 集成
    results["agent"] = run_agent_tests()

    # 汇总
    print_header("测试汇总")

    for name, passed in results.items():
        labels = {
            "unit": "层级 1 - 单元测试（Mock）",
            "api": "层级 2 - 真实 API 调用",
            "agent": "层级 3 - ChatAgent 集成",
        }
        if passed is None:
            print(f"  ⏭️  {labels[name]}: 跳过")
        elif passed:
            print(f"  ✅ {labels[name]}: 全部通过")
        else:
            print(f"  ❌ {labels[name]}: 有失败项")

    print()

    # 如果任何测试失败则退出码非零
    if any(v is False for v in results.values()):
        sys.exit(1)
