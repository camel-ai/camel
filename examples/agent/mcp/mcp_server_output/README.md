# SearchAgentMCP

This is an MCP server for the search agent.

## Setup

1. Make sure you have the required dependencies:
   ```
   pip install camel-ai mcp-server-fastmcp
   ```

2. Set the required environment variables:
   ```
   # No API key required
   ```

3. Run the server:
   ```
   python searchagentmcp.py
   ```

## Usage

The server exposes the following tools:

- `step(name, message, response_format=None)`: Execute a chat step
- `reset()`: Reset all agents
- `set_output_language(language)`: Set the output language

And the following resources:

- `agent://`: Get information about all agents
- `agent://{name}`: Get information about a specific agent
- `history://{name}`: Get the chat history for a specific agent
- `tool://{name}`: Get available tools for a specific agent

## Example

```python
from mcp.client import Client

client = Client("ws://localhost:8000")
await client.connect()

# Chat with the agent
response = await client.call("step", {
    "name": "search",
    "message": "Hello, how are you?"
})
print(response)

# Reset the agent
await client.call("reset")

# Disconnect
await client.disconnect()
```