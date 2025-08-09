---
title: 'Connect to Existing MCP Tools in CAMEL ChatAgent'
description: 'How to plug any MCP protocol tool (like file systems, web APIs) into your CAMEL ChatAgent for seamless tool-using agents.'
icon: 'network'
---

## Overview

You can connect any Model Context Protocol (MCP) tool—like the official filesystem server—directly to your CAMEL ChatAgent.  
This gives your agents natural language access to external filesystems, databases, or any MCP-compatible service.

<Info>
<strong>Use Case:</strong>  
Let your agent list files or read documents by wiring up the official MCP Filesystem server as a tool—no code changes to the agent required!
</Info>

<Steps>
  <Step title="Install the MCP Tool Server">
    You can use any MCP-compatible tool.  
    For this example, we'll use the <strong>official filesystem server</strong> from the Model Context Protocol community.
    <br /><br />
    Install globally using npm:
    <br /><br />
    ```bash Terminal
    npm install -g @modelcontextprotocol/server-filesystem
    ```
  </Step>

  <Step title="Start the MCP Tool Server">
    Start the server in the directory you want to expose (e.g., your project root):
    <br /><br />
    ```bash Terminal
    npx -y @modelcontextprotocol/server-filesystem .
    ```
    This limits all file operations to the current directory.
  </Step>

  <Step title="Connect MCP Tool Server to CAMEL">
    Now, connect the MCP tool server to CAMEL using <code>MCPClient</code> or <code>MCPToolkit</code>.
    <br /><br />
    <strong>Direct Client Example (Async):</strong>
    ```python mcp_filesystem_client.py lines icon="python"
    import asyncio
    from camel.utils.mcp_client import MCPClient

    async def mcp_client_example():
        config = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        }
        async with MCPClient(config) as client:
            mcp_tools = await client.list_mcp_tools()
            print("Available MCP tools:", [tool.name for tool in mcp_tools.tools])
            call_tool_result = await client.call_tool(
                "list_directory", {"path": "."}
            )
            print("Directory Contents:")
            for i, item in enumerate(call_tool_result.content[0].text.split('\n')):
                if item.strip():
                    print(f"  {item}")
                    if i >= 4:
                        break

    asyncio.run(mcp_client_example())
    ```
  </Step>

  <Step title="Integrate with CAMEL ChatAgent">
    Add the tools exposed by the MCP server to your ChatAgent.
    <br /><br />
    <strong>Async Agent Integration:</strong>
    ```python mcp_agent_integration.py lines icon="python"
    import asyncio
    from pathlib import Path
    from camel.agents import ChatAgent
    from camel.models import ModelFactory
    from camel.toolkits import MCPToolkit
    from camel.types import ModelPlatformType, ModelType

    async def mcp_toolkit_example():
        config_path = Path(__file__).parent / "mcp_servers_config.json"
        async with MCPToolkit(config_path=str(config_path)) as mcp_toolkit:
            sys_msg = "You are a helpful assistant"
            model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )
            camel_agent = ChatAgent(
                system_message=sys_msg,
                model=model,
                tools=[*mcp_toolkit.get_tools()],
            )
            user_msg = "List 5 files in the project, using relative paths"
            response = await camel_agent.astep(user_msg)
            print(response.msgs[0].content)
            print(response.info['tool_calls'])

    asyncio.run(mcp_toolkit_example())
    ```
    <br />
    <strong>Config Example (<code>mcp_servers_config.json</code>):</strong>
    ```json mcp_servers_config.json lines icon="settings"
    {
      "mcpServers": {
        "filesystem": {
          "command": "npx",
          "args": [
            "-y",
            "@modelcontextprotocol/server-filesystem@2025.1.14",
            "."
          ]
        }
      },
      "mcpWebServers": {}
    }
    ```
  </Step>

  <Step title="Sync Version (Optional)">
    Use <code>step()</code> for synchronous execution:
    <br /><br />
    ```python mcp_agent_sync.py lines icon="python"
    from pathlib import Path
    from camel.agents import ChatAgent
    from camel.models import ModelFactory
    from camel.toolkits import MCPToolkit
    from camel.types import ModelPlatformType, ModelType

    def mcp_toolkit_example_sync():
        config_path = Path(__file__).parent / "mcp_servers_config.json"
        with MCPToolkit(config_path=str(config_path)) as mcp_toolkit:
            sys_msg = "You are a helpful assistant"
            model = ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )
            camel_agent = ChatAgent(
                system_message=sys_msg,
                model=model,
                tools=[*mcp_toolkit.get_tools()],
            )
            user_msg = "List 5 files in the project, using relative paths"
            response = camel_agent.step(user_msg)
            print(response.msgs[0].content)
            print(response.info['tool_calls'])

    mcp_toolkit_example_sync()
    ```
  </Step>
</Steps>

<Info>
That's it!  
Your CAMEL agent can now leverage any external tool (filesystem, APIs, custom scripts) that supports MCP. Plug and play!
</Info>
