---
title: "CAMEL Agent as an MCP Server"
icon: server
description: "Turn your CAMEL ChatAgent into an MCP server—let any client (Claude, Cursor, custom apps) connect and use your agent as a universal AI backend."
---

<Card title="Why export a ChatAgent as an MCP server?" icon="server">
Publishing your <b>ChatAgent</b> as an MCP server turns your agent into a universal AI backend.
Any MCP-compatible client (Claude, Cursor, editors, or your own app) can connect, chat, and run tools through your agent as if it were a native API—no custom integration required.
</Card>

## Quick Start

<Card>

<Card title="Method 1: Use Service Scripts" icon="terminal">
<b>Scripted Server:</b>  
Launch your agent as an MCP server with the ready-made scripts in <code>services/</code>.  
Configure your MCP client (Claude, Cursor, etc.) to connect:
```json mcp_servers_config.json Example highlight={5}
{
  "camel-chat-agent": {
    "command": "/path/to/python",
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
<Info>
<b>Tip:</b> Just point your MCP client at this config, and it will auto-discover and call your agent!
</Info>
</Card>

<Card title="Method 2: Use `to_mcp()`" icon="bolt">
Turn any <code>ChatAgent</code> into an MCP server instantly with <code>to_mcp()</code>:
```python agent_mcp_server.py lines icon="python"
from camel.agents import ChatAgent

# Create a chat agent with your model
agent = ChatAgent(model="gpt-4o-mini")

# Convert to an MCP server
mcp_server = agent.to_mcp(
    name="demo", description="A demonstration of ChatAgent to MCP conversion"
)

if __name__ == "__main__":
    print("Starting MCP server on http://localhost:8000")
    mcp_server.run(transport="streamable-http")
```
<Info>
<b>Supported transports:</b> <code>stdio</code>, <code>sse</code>, <code>streamable-http</code>
</Info>
</Card>

</Card>


<Card title="What does this unlock?" icon="unlock">
- **Plug-and-play with any MCP client**: Claude, Cursor, editors, automations—just connect and go.
- **Universal API**: Your agent becomes an “AI API” for any tool that speaks MCP.
- **Security & Flexibility**: Keep control over keys, environments, and agent configs.
</Card>

## Real-world Example

<Card title="Claude calling a CAMEL MCP server" icon="comments">
You can use Claude, Cursor, or any other app to call your custom agent!  
Just connect to your <b>CAMEL MCP server</b>
<img src="/images/claude_example1.png" alt="Claude MCP Screenshot" />
<img src="/images/claude_example2.png" alt="Claude MCP Screenshot" />
<Info>
You can expose any number of custom tools, multi-agent workflows, or domain knowledge, right from your own laptop or server!
</Info>
</Card>

---

## Why make your ChatAgent an MCP server?

<Card title="Benefits" icon="star">
- **Universal Access:** Any client, any platform, anytime.
- **Multi-Agent Workflows:** Power agent societies by letting agents call each other.
- **Local Control:** Expose only the tools and data you want, with full security.
- **No Glue Code:** MCP handles discovery and invocation, no custom REST or RPC needed.
</Card>

---

<Info>
Want to create your own tools and toolkits?  
See <a href="/key_modules/tools">Toolkits Reference</a> for everything you can expose to the MCP ecosystem!
</Info>
