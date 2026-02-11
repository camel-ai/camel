# MCP Code Execution - Quick Start

[English](#english) | [中文](#中文)

## English

### Overview

MCP Code Execution is a new way to interact with MCP (Model Context Protocol) servers by having agents write code instead of making direct tool calls. This approach provides several benefits:

- **Reduced Token Consumption**: Only loads necessary tools, saves intermediate results in execution environment
- **Better Tool Composition**: Uses Python control flow (loops, conditionals) to orchestrate tools
- **State Persistence**: Can save intermediate results to filesystem
- **Skill Building**: Can save and reuse developed code snippets

### Quick Start

```python
import asyncio
from camel.agents import MCPCodeAgent

async def main():
    # Configure MCP servers
    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            }
        }
    }
    
    # Create and use agent
    async with await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./workspace"
    ) as agent:
        response = await agent.astep(
            "List all files in /tmp and count them"
        )
        print(response.msgs[0].content)

asyncio.run(main())
```

### Key Components

1. **MCPCodeAgent**: Agent that generates code to call MCP tools
2. **MCPCodeExecutor**: Manages code execution and MCP tool calls
3. **MCPCodeGenerator**: Generates code APIs for MCP servers
4. **SkillManager**: Manages reusable code skills

### Example: Multi-Tool Composition

```python
# The agent writes code to compose multiple tool calls efficiently
response = await agent.astep("""
    1. Read document from Google Drive
    2. Process the content
    3. Update Salesforce record
    4. Generate summary report
    
    Do this efficiently by keeping intermediate data in variables,
    not passing through context.
""")
```

### Example: Skills Management

```python
# Save a reusable skill
agent.save_skill(
    name="csv_processor",
    description="Process CSV files",
    code="""
async def process_csv(filepath):
    from servers.filesystem import read_file
    result = await read_file(path=filepath)
    return parse_csv(result['result'])
""",
    tags=["csv", "data"]
)

# Use the skill later
response = await agent.astep("Use csv_processor to analyze /tmp/data.csv")
```

### Documentation

For detailed documentation, see [MCP Code Execution Guide](./mcp_code_execution.md).

### References

- [Anthropic: Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [MCP-Zero Paper](https://arxiv.org/pdf/2506.01056)
- [GitHub Issue #2627](https://github.com/camel-ai/camel/issues/2627)

---

## 中文

### 概述

MCP 代码执行是一种通过让 Agent 编写代码而不是直接调用工具来与 MCP (Model Context Protocol) 服务器交互的新方式。这种方法提供了几个好处：

- **减少 Token 消耗**：只加载必要的工具，在执行环境中保存中间结果
- **更好的工具组合**：使用 Python 控制流（循环、条件语句）来编排工具
- **状态持久化**：可以将中间结果保存到文件系统
- **技能构建**：可以保存和重用开发的代码片段

### 快速开始

```python
import asyncio
from camel.agents import MCPCodeAgent

async def main():
    # 配置 MCP 服务器
    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            }
        }
    }
    
    # 创建并使用 Agent
    async with await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./workspace"
    ) as agent:
        response = await agent.astep(
            "列出 /tmp 中的所有文件并统计数量"
        )
        print(response.msgs[0].content)

asyncio.run(main())
```

### 核心组件

1. **MCPCodeAgent**：生成代码来调用 MCP 工具的 Agent
2. **MCPCodeExecutor**：管理代码执行和 MCP 工具调用
3. **MCPCodeGenerator**：为 MCP 服务器生成代码 API
4. **SkillManager**：管理可重用的代码技能

### 示例：多工具组合

```python
# Agent 编写代码来高效组合多个工具调用
response = await agent.astep("""
    1. 从 Google Drive 读取文档
    2. 处理内容
    3. 更新 Salesforce 记录
    4. 生成摘要报告
    
    请高效地完成这些操作，将中间数据保存在变量中，
    而不是通过上下文传递。
""")
```

### 示例：技能管理

```python
# 保存可重用的技能
agent.save_skill(
    name="csv_processor",
    description="处理 CSV 文件",
    code="""
async def process_csv(filepath):
    from servers.filesystem import read_file
    result = await read_file(path=filepath)
    return parse_csv(result['result'])
""",
    tags=["csv", "data"]
)

# 之后使用技能
response = await agent.astep("使用 csv_processor 分析 /tmp/data.csv")
```

### 文档

详细文档请参见 [MCP 代码执行指南](./mcp_code_execution.md)。

### 参考资料

- [Anthropic: 使用 MCP 的代码执行](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [MCP-Zero 论文](https://arxiv.org/pdf/2506.01056)
- [GitHub Issue #2627](https://github.com/camel-ai/camel/issues/2627)

---

## Architecture

```
┌─────────────────┐
│  MCPCodeAgent   │  Generates code to call tools
└────────┬────────┘
         │
         ├─── MCPCodeExecutor   Manages code execution
         │         │
         │         ├─── Code Generator   Generates tool APIs
         │         └─── Workspace        Manages workspace
         │
         ├─── SkillManager      Manages reusable skills
         │
         └─── MCPToolkit        MCP server connections
```

## Installation

```bash
pip install camel-ai[all]
```

## License

Apache License 2.0 - See [LICENSE](../LICENSE) for details.
