# CAMEL Agent MCP Server

This MCP server exposes CAMEL's Agent module as a tool that can be used by LLMs through the Model Context Protocol (MCP).

## Overview

The Agent module in CAMEL provides powerful AI agent capabilities with memory, tool use, and conversational abilities. This MCP server provides access to the Agent functionality, allowing LLMs to:

1. Create and manage agent instances
2. Execute conversations with agents
3. Use various agent types (ChatAgent, TaskSpecifyAgent, etc.)
4. Access agent memory and configuration
5. Work with agent tools and capabilities

## Setup

1. Ensure you have CAMEL installed with all dependencies:
   ```bash
   pip install camel-ai[all]
   ```

2. Set the required environment variables for API keys:
   ```bash
   export OPENAI_API_KEY=your_openai_api_key
   export OPENROUTER_API_KEY=your_openrouter_api_key  # Optional for advanced models
   ```

## Running the Server

To start the Agent MCP server:

```bash
python -m services.agent_mcp.server
```

Alternatively, use the MCP CLI (if you have MCP installed):

```bash
mcp run services/agent_mcp/server.py
```

## Features

### Available Tools

The server exposes the following tools:

- `get_available_agents()`: Returns a list of predefined agent configurations
- `create_agent()`: Creates a new agent instance with specified parameters
- `chat_with_agent()`: Executes a conversation step with an agent
- `get_agent_info()`: Gets information about a specific agent instance
- `delete_agent()`: Deletes an agent instance
- `reset_agent()`: Resets an agent's memory
- `execute_tool()`: Allows an agent to execute tools if it has tool capabilities

### Predefined Agent Types

The server supports various agent types:

1. **ChatAgent**: A general-purpose conversational agent
2. **TaskSpecifyAgent**: Specializes in task specification
3. **CriticAgent**: Evaluates and critiques responses
4. **TaskPlannerAgent**: Helps create plans for complex tasks

## Example Usage

Here's a basic example of how to interact with the server:

```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
    # Create an agent
    response = await client.post(
        "/api/v1/tools/create_agent",
        json={
            "role_name": "Python Expert",
            "system_message": "You are an expert Python programmer who helps write clean, efficient code.",
            "with_tools": True,
        },
    )
    agent_data = response.json()["result"]
    agent_id = agent_data["agent_id"]

    # Chat with the agent
    response = await client.post(
        "/api/v1/tools/chat_with_agent",
        json={
            "agent_id": agent_id,
            "message": "How do I implement a decorator in Python?",
        },
    )
    chat_result = response.json()["result"]
    print(chat_result["response"])
```

## Customization

You can customize the Agent MCP server by editing the `config.py` file:

1. Change the default models
2. Add new tool configurations
3. Modify the agent presets
4. Configure system prompts and default settings 