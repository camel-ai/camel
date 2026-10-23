# MCP Code Execution

CAMEL 现在支持通过代码执行与 MCP (Model Context Protocol) 服务器交互，这是一种更高效的工具调用方式。

## 概述

传统的 MCP 工具调用方式存在一些局限性：

1. **上下文消耗大**：所有工具定义都需要加载到上下文中，导致 token 消耗增加
2. **中间结果传递**：每次工具调用的结果都需要通过模型上下文传递
3. **组合能力弱**：难以高效地组合多个工具调用

通过代码执行方式，Agent 可以编写代码来调用 MCP 工具，带来以下优势：

- **减少 token 消耗**：只加载需要的工具，中间结果保存在执行环境中
- **更好的工具组合**：使用 Python 的控制流（循环、条件语句）来编排工具
- **状态持久化**：可以保存中间结果到文件系统
- **技能构建**：可以保存和重用开发的代码片段

## 架构

```
┌─────────────────┐
│  MCPCodeAgent   │  - 生成代码调用工具
└────────┬────────┘
         │
         ├─── MCPCodeExecutor  - 管理代码执行
         │         │
         │         ├─── Code Generator  - 生成工具 API
         │         └─── Workspace      - 管理工作空间
         │
         ├─── SkillManager     - 管理可重用技能
         │
         └─── MCPToolkit       - MCP 服务器连接
```

## 核心组件

### 1. MCPCodeAgent

使用代码执行与 MCP 服务器交互的 Agent。

```python
from camel.agents import MCPCodeAgent

# 配置 MCP 服务器
config = {
    "mcpServers": {
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
        }
    }
}

# 创建 Agent
agent = await MCPCodeAgent.create(
    config_dict=config,
    workspace_dir="./workspace"
)

# 使用 Agent
response = await agent.astep("列出 /tmp 目录中的所有文件")
```

### 2. MCPCodeExecutor

管理代码执行和 MCP 工具调用的执行器。

```python
from camel.utils.mcp_code_executor import MCPCodeExecutor
from camel.toolkits.mcp_toolkit import MCPToolkit

toolkit = MCPToolkit(config_dict=config)
await toolkit.connect()

executor = MCPCodeExecutor(toolkit, "./workspace")
await executor.generate_apis()

# 获取工作空间信息
info = executor.get_workspace_info()
print(info["directory_tree"])
```

### 3. MCPCodeGenerator

为 MCP 服务器生成代码 API。

```python
from camel.utils.mcp_code_generator import MCPCodeGenerator

generator = MCPCodeGenerator("./workspace")

# 为服务器生成 API
generator.generate_server_api("google_drive", tools_list)

# 生成技能目录结构
generator.generate_skills_structure()

# 查看目录树
print(generator.get_directory_tree())
```

### 4. SkillManager

管理可重用的代码技能。

```python
from camel.utils.mcp_skills import Skill, SkillManager

manager = SkillManager("./workspace/skills")

# 创建技能
skill = Skill(
    name="count_files",
    description="统计目录中的文件数量",
    code="""
async def count_files(directory):
    from servers.filesystem import list_directory
    result = await list_directory(path=directory)
    return len(result.get('files', []))
""",
    tags=["filesystem", "utility"]
)

# 保存技能
manager.save_skill(skill)

# 搜索技能
skills = manager.search_skills(query="file", tags=["filesystem"])
```

## 使用示例

### 示例 1: 基础用法

```python
import asyncio
from camel.agents import MCPCodeAgent

async def main():
    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            }
        }
    }
    
    async with await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./workspace"
    ) as agent:
        response = await agent.astep(
            "读取 /tmp/example.txt 并统计单词数"
        )
        print(response.msgs[0].content)

asyncio.run(main())
```

### 示例 2: 多工具组合

```python
async def multi_tool_example():
    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
            },
            "github": {
                "url": "https://api.github.com/mcp",
                "headers": {"Authorization": "Bearer YOUR_TOKEN"}
            }
        }
    }
    
    agent = await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./workspace"
    )
    
    # Agent 会生成代码来组合多个工具调用
    response = await agent.astep("""
        1. 从 GitHub 仓库下载文件
        2. 处理文件内容
        3. 保存结果到本地文件系统
        4. 生成统计报告
    """)
    
    print(response.msgs[0].content)
    await agent.disconnect()
```

### 示例 3: 技能管理

```python
async def skills_example():
    agent = await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./workspace",
        enable_skills=True
    )
    
    # 保存技能
    agent.save_skill(
        name="csv_processor",
        description="处理 CSV 文件",
        code="""
async def process_csv(filepath):
    from servers.filesystem import read_file
    result = await read_file(path=filepath)
    lines = result['result'].split('\\n')
    return [line.split(',') for line in lines]
""",
        tags=["csv", "data"],
        examples=["data = await process_csv('/tmp/data.csv')"]
    )
    
    # 列出技能
    skills = agent.list_skills()
    print(f"Available skills: {skills}")
    
    # 使用技能
    response = await agent.astep(
        "使用 csv_processor 技能处理 /tmp/data.csv"
    )
```

### 示例 4: 上下文效率

```python
async def efficient_example():
    agent = await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./workspace"
    )
    
    # 这个任务如果使用直接工具调用会消耗大量 token
    # 但通过代码执行，中间结果保存在执行环境中
    response = await agent.astep("""
        处理 /tmp 目录中的所有文件：
        1. 读取每个文件
        2. 计算统计信息（大小、行数、单词数）
        3. 只保留统计摘要，不保留完整内容
        4. 返回 JSON 格式的报告
        
        请高效地在循环中处理文件，避免将完整内容传递到上下文中。
    """)
    
    print(response.msgs[0].content)
```

## 工作空间结构

```
workspace/
├── servers/              # 生成的 MCP 工具 API
│   ├── filesystem/
│   │   ├── __init__.py
│   │   ├── read_file.py
│   │   ├── write_file.py
│   │   └── list_directory.py
│   ├── google_drive/
│   │   ├── __init__.py
│   │   ├── get_document.py
│   │   └── update_document.py
│   └── client.py        # 工具调用客户端
├── skills/              # 可重用技能
│   ├── README.md
│   ├── __init__.py
│   ├── csv_processor.py
│   ├── csv_processor.md
│   └── file_analyzer.py
└── temp/                # 临时文件
```

## 代码 API 格式

生成的工具包装代码示例：

```python
# servers/google_drive/get_document.py
from typing import Any, Dict, Optional
from camel.utils.mcp_code_executor import call_mcp_tool

async def get_document(
    document_id: str,
    fields: Optional[str] = None
) -> Dict[str, Any]:
    """
    从 Google Drive 检索文档
    
    这是 MCP 工具 'get_document' 的自动生成包装器
    来自服务器 'google_drive'。
    """
    arguments = {}
    if document_id is not None:
        arguments['document_id'] = document_id
    if fields is not None:
        arguments['fields'] = fields

    return await call_mcp_tool(
        server_name="google_drive",
        tool_name="get_document",
        arguments=arguments
    )
```

Agent 可以直接导入和使用：

```python
from servers.google_drive import get_document
from servers.salesforce import update_record

# 读取文档
doc = await get_document(document_id="abc123")

# 更新 Salesforce 记录
await update_record(
    object_type="Lead",
    record_id="00Q123",
    data={"Notes": doc['result']}
)
```

## 技能格式

技能文件示例：

```python
# skills/count_files.py
# Skill: count_files
# Created: 2026-02-11T10:30:00
# Updated: 2026-02-11T10:30:00
# Tags: filesystem, utility

"""
统计目录中的文件数量

Examples:
    count = await count_files_in_directory('/tmp')
    print(f'Found {count} files')

"""

async def count_files_in_directory(directory_path):
    '''统计目录中的文件数量'''
    from servers.filesystem import list_directory
    
    result = await list_directory(path=directory_path)
    files = result.get('files', [])
    return len(files)
```

对应的元数据文件 `count_files.md`：

```markdown
# count_files

统计目录中的文件数量

## Metadata

- **Created**: 2026-02-11T10:30:00
- **Updated**: 2026-02-11T10:30:00
- **Usage Count**: 5
- **Tags**: filesystem, utility

## Dependencies

- `from servers.filesystem import list_directory`

## Examples

```python
count = await count_files_in_directory('/tmp')
print(f'Found {count} files')
```

## Additional Information

```json
{
  "version": "1.0",
  "author": "agent"
}
```
```

## 优势对比

### 传统方式 vs 代码执行方式

**传统直接工具调用：**

```
用户: 从 Google Drive 读取文档 abc123 并更新到 Salesforce

Agent:
[加载所有工具定义 - 消耗 10K tokens]

TOOL_CALL: get_document(document_id="abc123")
→ 返回 "会议记录... [5000 字完整内容]"
[内容加载到上下文 - 消耗 6K tokens]

TOOL_CALL: update_record(
    object_type="Lead",
    record_id="00Q123",
    data={"Notes": "会议记录... [5000 字重复]"}
)
[内容再次通过上下文 - 消耗 6K tokens]

总计: ~22K tokens
```

**代码执行方式：**

```
用户: 从 Google Drive 读取文档 abc123 并更新到 Salesforce

Agent:
[只加载需要的工具 - 消耗 2K tokens]

生成代码:
```python
from servers.google_drive import get_document
from servers.salesforce import update_record

# 读取文档
doc = await get_document(document_id="abc123")

# 直接更新，内容不通过模型上下文
await update_record(
    object_type="Lead",
    record_id="00Q123",
    data={"Notes": doc['result']}
)
```

[代码执行 - 消耗 1K tokens]
总计: ~3K tokens (节省 86%)
```

## 隐私和安全

代码执行方式提供更好的隐私保护：

1. **中间数据隔离**：敏感数据在执行环境中流动，不通过模型上下文
2. **选择性日志**：只记录明确输出的信息
3. **数据标记化**：可以自动标记化 PII 数据
4. **确定性安全规则**：可以定义数据流向规则

示例：

```python
# 敏感数据不会暴露给模型
from servers.spreadsheet import get_sheet
from servers.salesforce import update_record

sheet = await get_sheet(sheet_id='abc123')
# sheet 包含敏感的邮箱、电话等，但不经过模型

for row in sheet['rows']:
    await update_record(
        object_type='Lead',
        record_id=row['salesforce_id'],
        data={
            'Email': row['email'],      # 直接流动
            'Phone': row['phone'],      # 直接流动
            'Name': row['name']         # 直接流动
        }
    )

# 只有统计信息返回给模型
print(f"Updated {len(sheet['rows'])} leads")
```

## API 参考

### MCPCodeAgent

```python
class MCPCodeAgent(ChatAgent):
    def __init__(
        self,
        mcp_toolkit: MCPToolkit,
        workspace_dir: str,
        interpreter: Optional[BaseInterpreter] = None,
        system_message: Optional[Union[str, BaseMessage]] = None,
        model: Optional[BaseModelBackend] = None,
        enable_skills: bool = True,
        auto_generate_apis: bool = True,
        **kwargs
    )
    
    async def connect(self) -> None
    async def disconnect(self) -> None
    async def astep(
        self, 
        input_message: Union[BaseMessage, str],
        *args, **kwargs
    ) -> ChatAgentResponse
    
    def save_skill(
        self,
        name: str,
        description: str,
        code: str,
        tags: Optional[List[str]] = None,
        examples: Optional[List[str]] = None
    ) -> bool
    
    def list_skills(self) -> List[str]
    def get_skill(self, name: str) -> Optional[str]
    
    @classmethod
    async def create(
        cls,
        config_path: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        workspace_dir: str = "./mcp_workspace",
        **kwargs
    ) -> "MCPCodeAgent"
```

### MCPCodeExecutor

```python
class MCPCodeExecutor:
    def __init__(
        self,
        mcp_toolkit: MCPToolkit,
        workspace_dir: str
    )
    
    async def generate_apis(self) -> None
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]
    
    def get_workspace_info(self) -> Dict[str, Any]
    def get_execution_context(self) -> Dict[str, Any]
    async def execute_code(self, code: str) -> Any
    def cleanup(self) -> None
    
    @classmethod
    def get_instance(cls) -> Optional["MCPCodeExecutor"]
```

### MCPCodeGenerator

```python
class MCPCodeGenerator:
    def __init__(
        self,
        workspace_dir: str,
        servers_dir: str = "servers"
    )
    
    def generate_server_api(
        self,
        server_name: str,
        tools: List[types.Tool]
    ) -> None
    
    def generate_main_client(self) -> None
    def generate_skills_structure(self) -> None
    def list_available_tools(self) -> Dict[str, List[str]]
    def get_directory_tree(self) -> str
    def cleanup(self) -> None
```

### SkillManager

```python
class SkillManager:
    def __init__(self, skills_dir: str)
    
    def save_skill(self, skill: Skill, overwrite: bool = True) -> bool
    def load_skill(self, name: str) -> Optional[Skill]
    def search_skills(
        self,
        query: str = "",
        tags: Optional[List[str]] = None
    ) -> List[Skill]
    
    def list_skills(self) -> List[str]
    def delete_skill(self, name: str) -> bool
    def get_skills_summary(self) -> str
    def export_skills(self, export_path: str) -> bool
    def import_skills(
        self,
        import_path: str,
        overwrite: bool = False
    ) -> int
```

## 最佳实践

1. **工具发现**：让 Agent 先探索可用工具，再编写代码
2. **错误处理**：在代码中添加适当的错误处理
3. **状态管理**：使用文件系统保存中间状态
4. **技能积累**：将有用的函数保存为技能
5. **文档说明**：为技能添加清晰的文档和示例
6. **组合优先**：优先使用代码组合工具，而不是单独调用
7. **上下文优化**：将大量数据保留在执行环境中

## 参考资料

- [Anthropic: Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [MCP-Zero 论文](https://arxiv.org/pdf/2506.01056)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [CAMEL-AI GitHub Issue #2627](https://github.com/camel-ai/camel/issues/2627)

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](../CONTRIBUTING.md) 了解如何参与贡献。

## 许可证

Apache License 2.0 - 查看 [LICENSE](../LICENSE) 文件了解详情。
