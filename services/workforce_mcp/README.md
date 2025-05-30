# CAMEL Workforce MCP Server

This MCP server exposes CAMEL's Workforce module as a tool that can be used by LLMs through the Model Context Protocol (MCP).

## Overview

The Workforce module in CAMEL is a multi-agent cooperative system where different agents work together to solve complex tasks. This MCP server provides access to the Workforce functionality, allowing LLMs to:

1. Process tasks using the Workforce system
2. Get information about the current Workforce configuration
3. Add new workers to the Workforce
4. Reset or clone the Workforce

## Setup

1. Ensure you have CAMEL installed with all dependencies:
   ```bash
   pip install camel-ai[all]
   ```

2. Set the required environment variables for API keys:
   ```bash
   export OPENAI_API_KEY=your_openai_api_key
   export OPENROUTER_API_KEY=your_openrouter_api_key
   ```

## Running the Server

You can run the server with:

```bash
cd /path/to/camel
python -m services.workforce_mcp.server
```

For Claude Desktop integration:

```bash
mcp install services/workforce_mcp/server.py --name "CAMEL Workforce"
```

For testing and debugging:

```bash
mcp dev services/workforce_mcp/server.py
```

## Available Tools

### Process a Task

```python
process_task(
    content: str,
    additional_info: Optional[str] = None,
)
```

Processes a task using the CAMEL Workforce system. The Workforce will decompose the task, assign subtasks to appropriate workers, and return the results.

### Get Workforce Info

```python
get_workforce_info()
```

Returns information about the current Workforce configuration, including all workers and their capabilities.

### Add a Single Agent Worker

```python
add_single_agent_worker(
    description: str,
    system_message: str,
    model_name: Optional[str] = None,
    tools: Optional[List[str]] = None,
)
```

Adds a new single agent worker to the Workforce with the specified description, system message, and optional tools.

### Add a Role-Playing Worker

```python
add_role_playing_worker(
    description: str,
    assistant_role_name: str,
    user_role_name: str,
    chat_turn_limit: int = 3,
)
```

Adds a new role-playing worker to the Workforce, which consists of two agents that collaborate in a role-playing manner.

### Reset Workforce

```python
reset_workforce()
```

Resets the Workforce to its initial state, clearing all task history.

### Clone Workforce

```python
clone_workforce(with_memory: bool = False)
```

Creates a clone of the current Workforce, optionally including memory (conversation history). 