---
title: "CAMEL Agents as an MCP Client"
icon: plug
---

This guide walks you through turning your CAMEL AI agent into an MCP client, letting your agent easily use tools from multiple MCP servers.

## Quick Setup Steps

1. **Create a Config File**: Tell CAMEL which MCP servers you want to connect to.
2. **Use MCPToolkit to Connect**: Load your config file to connect to the servers.
3. **Enable Tools in CAMEL Agent**: Pass the server tools to your CAMEL agent to use.

This guide walks you through turning your CAMEL AI agent into an MCP client, letting your agent easily use tools from multiple MCP servers.

## Step-by-Step Setup

<Steps>

  <Step title="Step 1: Configure MCP Servers">
    Start by creating a config file that tells your CAMEL agent what MCP servers to connect to. You can define local or remote servers, each with a transport method.

    <Tabs>
      <Tab title="Local Server (stdio)">
      ```json
      {
        "mcpServers": {
          "time_server": {
            "command": "python",
            "args": ["time_server.py"],
            "transport": "stdio"
          }
        }
      }
      ```
      </Tab>

      <Tab title="Remote Server (streamable-http, sse)">
      ```json
      {
        "mcpServers": {
          "composio-notion": {
            "command": "npx",
            "args": ["composio-core@rc", "mcp", "https://mcp.composio.dev/notion/your-server-id", "--client", "camel"],
            "env": {
              "COMPOSIO_API_KEY": "your-api-key-here"
            },
            "transport": "streamable-http"
          }
        }
      }
      ```
      </Tab>
  <Tab title="ACI.dev Server (configurable transport)">
    ```json
    {
      "mcpServers": {
        "aci_apps": {
          "command": "uvx",
          "args": [
            "aci-mcp",
            "apps-server",
            "--apps=BRAVE_SEARCH,GITHUB,ARXIV",
            "--linked-account-owner-id",
            "<your_linked_acc_owner_id>"
          ],
          "env": {
            "ACI_API_KEY": "your_aci_api_key"
          },
          "transport": "sse" // or "streamable-http"
        }
      }
    }
    ```
    <Note type="info">
You can use <code>sse</code> or <code>streamable-http</code> for ACI.dev, pick whichever is supported by your agent/server.
</Note>
  </Tab>


    </Tabs>
  </Step>

  <Step title="Step 2: Connect & Build the Agent">
    Use `MCPToolkit` to connect to the servers and pass the tools to your CAMEL agent.

    ```python
    import asyncio
    from camel.toolkits.mcp_toolkit import MCPToolkit
    from camel.agents import ChatAgent

    async def main():
        async with MCPToolkit(config_path="config/time.json") as toolkit:
          agent = ChatAgent(model=model, tools=toolkit.get_tools())
          response = await agent.astep("What time is it now?")
          print(response.msgs[0].content)

    asyncio.run(main())
    ```
  </Step>

  <Step title="Step 3: Add More Tools & Debug">
    Once connected, you can extend your setup with other servers from ACI.dev, Composio, or `npx`.  

    <Note type="info">
    - Use `stdio` for local testing, `sse` or `streamable-http` for cloud tools.
    - Secure your API keys using the `env` field in the config.
    - Use the MCP Inspector (`npx @modelcontextprotocol/inspector`) if you run into issues.

    Try plugging in servers like GitHub, Notion, or ArXiv and see your CAMEL agent in action.
    </Note>
  </Step>

</Steps>

## How It Works – System Diagram

<Card title="CAMEL Agent as an MCP Client" img="/images/camel_toolks_as_mcp_server.png">
This diagram illustrates how CAMEL agents use MCPToolkit to seamlessly connect with MCP servers. Servers provide external tools from platforms like GitHub, Gmail, Notion, and more.
</Card>

<Card title="Advanced: Register with MCP Hubs & Registries">

<Card title="Connect your agent to an MCP registry" icon="link">
Want your MCP agent discoverable by thousands of clients?  
Register it with a hub like <a href="https://aci.dev/" target="_blank">ACI.dev</a> or similar.
```python Register with ACI Registry lines icon="python"
from camel.agents import MCPAgent
from camel.types import ACIRegistryConfig, ModelFactory, ModelPlatformType, ModelType
import os

aci_config = ACIRegistryConfig(
    api_key=os.getenv("ACI_API_KEY"),
    linked_account_owner_id=os.getenv("ACI_LINKED_ACCOUNT_OWNER_ID"),
)
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
)

agent = MCPAgent(
    model=model,
    registry_configs=[aci_config],
)
```
Your agent is now connected to the <a href="https://aci.dev/" target="_blank">ACI.dev</a> registry and visible in the ecosystem.
</Card>

<Card title = "Discover MCP Servers Easily with PulseMCP">

Finding MCP servers is now a breeze with PulseMCP integration.  
You don’t have to guess which MCP servers are available, just search, browse, and connect.

<Card title="Discover MCP Servers Instantly" icon="wave-pulse">
PulseMCP acts as a living directory of the entire MCP ecosystem.  
CAMEL toolkits can plug directly into PulseMCP, letting you browse and connect to thousands of servers, all kept up to date in real time.

You can visit [PulseMCP.com](https://pulsemcp.com) to browse all available MCP servers—everything from file systems and search to specialized APIs.

If you prefer to search programmatically inside your CAMEL code, just use:

<CodeBlock language="python" title="pulse_mcp_search.py">
from camel.toolkits.mcp import PulseMCPSearchToolkit

search_toolkit = PulseMCPSearchToolkit()
results = search_toolkit.search_mcp_servers(query="Slack", top_k=1)
print(results)
</CodeBlock>

PulseMCP does the heavy lifting of finding, categorizing, and keeping MCP servers fresh—your agents just connect and go.
</Card>
</Card>

<Card title="Minimal agent without function-calling" icon="function">
Don’t need advanced tool-calling?  
See <a href="https://github.com/camel-ai/camel/blob/master/examples/agents/mcp_agent/mcp_agent_without_function_calling.py" target="_blank">this example</a> for a super-lightweight setup.
</Card>
</Card>

## Using Transport Methods

- **stdio**: Ideal for local servers. Fast and easy.
- **sse**: Great for cloud-hosted servers like ACI.dev.
- **streamable-http**: Recommended for modern cloud integrations.

## Tips to Keep in Mind

- For easiest troubleshooting, try with a simple local stdio server first; once you’re comfortable, you can connect to cloud servers using sse or streamable-http.
- Store your API keys securely in the config file, never in code.
- Use the MCP Inspector tool (`npx @modelcontextprotocol/inspector`) for debugging.

## Give It a Go

Try setting up a config file for an MCP server (like [GitHub](https://github.com/github/github-mcp-server) or [Notion](https://github.com/makenotion/notion-mcp-server)) and see your CAMEL agent use the new tools right away!
