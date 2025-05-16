# CAMEL RolePlaying MCP Server

This MCP server exposes CAMEL's RolePlaying module as a tool that can be used by LLMs through the Model Context Protocol (MCP).

## Overview

The RolePlaying module in CAMEL is a multi-agent conversational system where different roles interact to accomplish tasks. This MCP server provides access to the RolePlaying functionality, allowing LLMs to:

1. Create and manage role-playing sessions
2. Get available pre-defined scenarios
3. Execute conversations between agents
4. Clone sessions with new tasks
5. Delete sessions when no longer needed

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

To start the RolePlaying MCP server:

```bash
python -m services.role_playing_mcp.server
```

Alternatively, use the MCP CLI (if you have MCP installed):

```bash
mcp run services/role_playing_mcp/server.py
```

## Features

### Available Tools

The server exposes the following tools:

- `get_available_scenarios()`: Returns a list of pre-defined role-playing scenarios
- `create_session()`: Creates a new role-playing session
- `chat_step()`: Advances the conversation in a session
- `chat_step_async()`: Asynchronously advances the conversation
- `get_session_info()`: Gets information about a specific session
- `delete_session()`: Deletes a session
- `clone_session()`: Creates a clone of an existing session with a new task

### Predefined Scenarios

The server comes with several predefined scenarios:

1. **Code Collaboration**: Senior Software Engineer and Software Product Manager
2. **Creative Writing**: Creative Writer and Book Editor
3. **Business Planning**: Business Consultant and Entrepreneur
4. **Scientific Discussion**: Research Scientist and Science Journalist

## Example Usage

Check the `example_usage.py` file for a comprehensive example of how to interact with the server. Here's a basic snippet:

```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
    # Create a session
    response = await client.post(
        "/api/v1/tools/create_session",
        json={"scenario_name": "code_collaboration"},
    )
    session_data = response.json()["result"]
    session_id = session_data["session_id"]

    # Send a message
    response = await client.post(
        "/api/v1/tools/chat_step",
        json={
            "session_id": session_id,
            "message": "Let's start planning our todo app. What features should we include?",
        },
    )
    chat_result = response.json()["result"]
    print(chat_result["assistant_response"])
    print(chat_result["user_response"])
```

## Customization

You can customize the RolePlaying MCP server by editing the `config.py` file:

1. Change the default models
2. Add new scenarios
3. Modify the default role names and prompts
4. Configure task types for different domains 