# Feature Implementation: MCP Code Execution

## Overview

This document describes the implementation of MCP Code Execution feature for CAMEL, based on:
- [GitHub Issue #2627](https://github.com/camel-ai/camel/issues/2627)
- [Anthropic's Code execution with MCP article](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [MCP-Zero Paper](https://arxiv.org/pdf/2506.01056)

## Motivation

Traditional MCP tool calling has limitations:
1. **High token consumption**: All tool definitions loaded into context
2. **Intermediate result passing**: Every tool call result passes through model context
3. **Limited composition**: Difficult to efficiently compose multiple tool calls

## Solution

Instead of direct tool calls, agents write Python code to interact with MCP tools. This approach:
- **Reduces token consumption**: Only loads needed tools, intermediate results stay in execution environment
- **Enables better composition**: Uses Python control flow to orchestrate tools
- **Supports state persistence**: Can save intermediate results to filesystem
- **Allows skill building**: Can save and reuse developed code snippets

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MCPCodeAgent                            │
│  - Generates code to call MCP tools                         │
│  - Manages skills and execution context                     │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌───────────────┐ ┌──────────────┐ ┌────────────┐
│ MCPCodeExec   │ │ SkillManager │ │ MCPToolkit │
│  - Executes   │ │  - Saves &   │ │  - Manages │
│    code       │ │    loads     │ │    server  │
│  - Manages    │ │    skills    │ │    conns   │
│    workspace  │ │  - Searches  │ │  - Provides│
│               │ │    skills    │ │    tools   │
└───────┬───────┘ └──────────────┘ └────────────┘
        │
        ▼
┌───────────────┐
│ CodeGenerator │
│  - Generates  │
│    tool APIs  │
│  - Creates    │
│    file tree  │
└───────────────┘
```

## Implemented Components

### 1. Core Modules

#### `camel/utils/mcp_code_generator.py`

Generates code API representations for MCP servers.

**Key Features:**
- Generates Python modules for each MCP tool
- Creates file tree structure (servers/tool_name/function.py)
- Generates type hints from JSON schemas
- Creates index files for easy imports
- Supports skills directory structure

**Main Classes:**
- `MCPCodeGenerator`: Main generator class

**Example Generated Code:**
```python
# servers/google_drive/get_document.py
async def get_document(
    document_id: str,
    fields: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieves a document from Google Drive"""
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

#### `camel/utils/mcp_code_executor.py`

Manages code execution and MCP tool calls.

**Key Features:**
- Singleton pattern for global access from generated code
- Manages workspace and execution context
- Handles async code execution
- Integrates with MCP toolkit for tool calls
- Provides workspace information

**Main Classes:**
- `MCPCodeExecutor`: Executor for running agent code

**Key Methods:**
- `generate_apis()`: Generate code APIs for all connected servers
- `call_tool()`: Call MCP tool through toolkit
- `execute_code()`: Execute agent-generated code
- `get_workspace_info()`: Get workspace structure information

#### `camel/utils/mcp_skills.py`

Manages reusable code skills.

**Key Features:**
- Save and load skills as Python files
- Skill metadata management (tags, usage count, examples)
- Search and filter skills
- Export/import skills
- Automatic usage tracking

**Main Classes:**
- `Skill`: Pydantic model for skill data
- `SkillManager`: Manager for skill operations

**Skill Structure:**
```python
skill = Skill(
    name="count_files",
    description="Count files in directory",
    code="async def count_files(path): ...",
    tags=["filesystem", "utility"],
    examples=["count = await count_files('/tmp')"],
    usage_count=5
)
```

#### `camel/agents/mcp_code_agent.py`

Agent that uses code execution to interact with MCP servers.

**Key Features:**
- Generates code instead of direct tool calls
- Automatic API generation on connection
- Integrated skills management
- Context-aware prompting with available tools
- Code extraction and execution
- Async/await support

**Main Classes:**
- `MCPCodeAgent`: Main agent class

**Key Methods:**
- `create()`: Factory method to create and connect agent
- `connect()`: Connect to MCP servers and generate APIs
- `astep()`: Async step with code generation and execution
- `save_skill()`: Save code snippet as reusable skill
- `list_skills()`: List available skills

### 2. Examples

#### `examples/agents/mcp_code_agent_quickstart.py`

Simple quick start example.

**Features:**
- Basic agent creation
- Simple task execution
- Context manager usage

#### `examples/agents/mcp_code_agent_example.py`

Comprehensive examples demonstrating:
1. Basic usage
2. Skills management
3. Multi-tool composition
4. Context efficiency
5. Workspace information

### 3. Tests

#### `test/agents/test_mcp_code_agent.py`

Unit and integration tests for:
- `MCPCodeGenerator`
- `SkillManager`
- `MCPCodeExecutor`
- `MCPCodeAgent` (integration tests)

**Test Coverage:**
- Initialization
- Skill management (save, load, search, delete)
- Code generation
- Agent creation and lifecycle

### 4. Documentation

#### `docs/mcp_code_execution.md`

Comprehensive Chinese documentation covering:
- Overview and motivation
- Architecture
- Core components
- Usage examples
- API reference
- Best practices
- Comparison with traditional approach

#### `docs/mcp_code_execution_README.md`

Quick start guide in English and Chinese with:
- Installation
- Quick start examples
- Key components overview
- References

## Usage Example

### Basic Usage

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
            "List all .txt files in /tmp and count them"
        )
        print(response.msgs[0].content)

asyncio.run(main())
```

### Multi-Tool Composition

```python
# Agent generates code that composes multiple tool calls
response = await agent.astep("""
    1. Read document from Google Drive (doc_id: abc123)
    2. Extract key information
    3. Update Salesforce record (record_id: xyz789)
    4. Generate summary report
    
    Do this efficiently by keeping intermediate data in variables.
""")
```

### Skills Management

```python
# Save a skill
agent.save_skill(
    name="csv_to_dict",
    description="Convert CSV to dictionary",
    code="""
async def csv_to_dict(filepath):
    from servers.filesystem import read_file
    result = await read_file(path=filepath)
    lines = result['result'].split('\\n')
    return [dict(zip(lines[0].split(','), line.split(','))) 
            for line in lines[1:]]
""",
    tags=["csv", "data"],
    examples=["data = await csv_to_dict('/tmp/data.csv')"]
)

# Use the skill
response = await agent.astep(
    "Use csv_to_dict skill to process /tmp/users.csv and "
    "count unique domains in email addresses"
)
```

## Benefits Demonstration

### Traditional Approach

```
User: Read Google Drive doc abc123 and update Salesforce

Agent:
[Loads ALL tool definitions - 10K tokens]

TOOL_CALL: get_document(document_id="abc123")
→ Returns "Meeting notes... [5000 words]"
[Content loaded to context - 6K tokens]

TOOL_CALL: update_record(
    object_type="Lead",
    record_id="00Q123",
    data={"Notes": "Meeting notes... [5000 words repeated]"}
)
[Content passed through context again - 6K tokens]

Total: ~22K tokens
```

### Code Execution Approach

```
User: Read Google Drive doc abc123 and update Salesforce

Agent:
[Only loads needed tools - 2K tokens]

Generates code:
```python
from servers.google_drive import get_document
from servers.salesforce import update_record

# Read document
doc = await get_document(document_id="abc123")

# Update directly, content stays in execution environment
await update_record(
    object_type="Lead",
    record_id="00Q123",
    data={"Notes": doc['result']}
)
```

[Code execution - 1K tokens]
Total: ~3K tokens (86% reduction)
```

## Workspace Structure

```
workspace/
├── servers/              # Generated MCP tool APIs
│   ├── filesystem/
│   │   ├── __init__.py
│   │   ├── read_file.py
│   │   ├── write_file.py
│   │   └── list_directory.py
│   ├── google_drive/
│   │   ├── __init__.py
│   │   ├── get_document.py
│   │   └── update_document.py
│   └── client.py        # Tool calling client
├── skills/              # Reusable skills
│   ├── README.md
│   ├── __init__.py
│   ├── csv_processor.py
│   ├── csv_processor.md
│   └── file_analyzer.py
└── temp/                # Temporary files
```

## Integration Points

1. **MCPToolkit Integration**: Uses existing MCPToolkit for server connections
2. **Interpreter Integration**: Uses InternalPythonInterpreter for safe code execution
3. **ChatAgent Extension**: Extends ChatAgent for consistent API
4. **Model Integration**: Works with any CAMEL model backend

## Testing

Run tests:
```bash
pytest test/agents/test_mcp_code_agent.py -v
```

Run examples:
```bash
python examples/agents/mcp_code_agent_quickstart.py
python examples/agents/mcp_code_agent_example.py
```

## Future Enhancements

1. **Enhanced Security**: More fine-grained control over code execution
2. **Skill Sharing**: Community skill repository
3. **Performance Optimization**: Caching and lazy loading
4. **Better Error Handling**: More informative error messages
5. **Debugging Support**: Step-through debugging for agent code
6. **Metrics Collection**: Track token savings and performance

## References

1. [Anthropic: Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
2. [MCP-Zero: Proactive Toolchain Construction](https://arxiv.org/pdf/2506.01056)
3. [Model Context Protocol](https://modelcontextprotocol.io/)
4. [CAMEL GitHub Issue #2627](https://github.com/camel-ai/camel/issues/2627)

## Contributors

Implementation by Claude (Anthropic) based on requirements from CAMEL-AI community.

## License

Apache License 2.0 - See LICENSE file for details.
