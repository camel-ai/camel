# CAMEL Model Context Protocol (MCP) Server

This directory contains the implementation for exposing CAMEL agents through the Model Context Protocol (MCP).

## What is MCP?

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io) lets you build servers that expose data and functionality to LLM applications in a standardized way. It acts like a web API specifically designed for LLM interactions, allowing you to:

- Expose data through **Resources** (like GET endpoints to load information into LLM context)
- Provide functionality through **Tools** (like POST endpoints to execute code or produce side effects)
- Define interaction patterns through **Prompts** (reusable templates for LLM interactions)

## CAMEL Agent MCP Server

The CAMEL Agent MCP Server allows you to expose your CAMEL agents as MCP services, making them accessible to any MCP-compatible client like Claude Desktop. This enables seamless integration of CAMEL's powerful agent capabilities with various applications.

> **IMPORTANT**: Before using the server, customize your agents in `agent_config.py` to set up your preferred models, system messages, and tools. The default configuration uses 3 different model platforms, but you can configure it to use any model supported by CAMEL.

### Available Agents

The default config file provides the following agents:

- **General Agent**: A helpful assistant for answering questions and helping with tasks
- **Search Agent**: An assistant with web search capabilities
- **Reasoning Agent**: An assistant specialized in reasoning tasks

### Tools and Resources

The server exposes the following MCP tools:

- `step`: Execute a single conversation step with a specified agent
- `reset`: Reset all agents to their initial state
- `set_output_language`: Set the output language for all agents
- `get_agents_info`: Get information about all available agents
- `get_chat_history`: Get the chat history for a specific agent
- `get_agent_info`: Get detailed information about a specific agent
- `get_available_tools`: Get a list of tools available to a specific agent

## Client Configuration

To connect MCP clients (such as Claude Desktop or Cursor) to your CAMEL agent server, you need to provide a JSON configuration. Here's an example configuration:

```json
{
  "camel-agents": {
    "command": "/path/to/your/python",
    "args": [
      "/path/to/camel/services/agent_mcp_server.py"
    ],
    "env": {
      "OPENAI_API_KEY": "...",
      "OPENROUTER_API_KEY": "...",
      "BRAVE_API_KEY": "..."
    }
  }
}
```

Replace the paths and API keys with your own values. This configuration tells the MCP client where to find your Python interpreter and the server script, as well as providing necessary environment variables for API access.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- CAMEL library (`pip install camel-ai[all]`)
- MCP library (`pip install mcp`)

### Configuration

1. Configure your agents in `agent_config.py`:
   - Define the models to use
   - Create custom agents with specific capabilities
   - Set system messages and tools

2. Set necessary environment variables:
   - `OPENROUTER_API_KEY`: For OpenRouter API access
   - Other API keys as needed for specific models

### Running the Server

You can run the MCP server in different ways:

#### Development Mode

Test and debug your server with the MCP Inspector:

```bash
mcp dev services/agent_mcp_server.py
```

#### Claude Desktop Integration

Install your server in Claude Desktop:

```bash
mcp install services/agent_mcp_server.py --name "CAMEL Agents"
```

#### Direct Execution

Run the server directly:

```bash
python services/agent_mcp_server.py
```

or

```bash
mcp run services/agent_mcp_server.py
```

## Usage Examples

### Using the Step Tool

```python
# Example of using the step tool
response = await step(
    name="search",
    message="What is the latest news about artificial intelligence?",
    ctx=context
)
```

### Using Resources

```python
# Get information about available agents
agent_info = await get_agents_info()

# Get chat history for a specific agent
history = await get_chat_history(name="general")
```

## Customization

You can customize the agents by modifying `agent_config.py`:

- Change models and parameters
- Add new agents with specific capabilities
- Configure tools and system messages

## License

Licensed under the Apache License, Version 2.0. See LICENSE for details.
