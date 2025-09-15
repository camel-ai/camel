---
title: "Toolkit as MCP Server"
icon: "server"
description: "Share any CAMEL toolkit as an MCP server so external clients and agents can use your tools."
---

<CardGroup cols={2}>

  <Card title="What is a Toolkit?" icon="screwdriver-wrench">
    A <b>Toolkit</b> is a bundle of related tools—functions that let agents fetch data, automate, search, or integrate with services.
    <br />
    <a href="/key_modules/tools"><b>Browse all CAMEL toolkits →</b></a>
  </Card>

  <Card title="Toolkit as an MCP Server" icon="head-side-gear">
    With one command, you can flip any toolkit into an <b>MCP server</b>.  
    Now, any MCP-compatible client or agent can call your tools—locally or over the network.
  </Card>

</CardGroup>

## Quick Example

<Card title="Run Any Toolkit as an MCP Server" icon="rocket">

You can turn any CAMEL toolkit into a full-featured MCP server—making its tools instantly available to other AI agents or external apps via the Model Context Protocol.

<b>Why do this?</b>  
- Instantly share your agent tools with external clients (e.g., Claude, Cursor, custom dashboards).
- Enable distributed, language-agnostic tool execution across different systems and teams.
- Easily test, debug, and reuse your tools—no need to change the toolkit or agent code.

### Launch a Toolkit Server

Below is a minimal script to expose <b>ArxivToolkit</b> as an MCP server.  
Swap in any other toolkit (e.g., <code>SearchToolkit</code>, <code>MathToolkit</code>), they all work the same way!

```python
from camel.toolkits import ArxivToolkit
import argparse

parser = argparse.ArgumentParser(
    description="Run Arxiv Toolkit as an MCP server."
)
parser.add_argument(
    "--mode",
    choices=["stdio", "sse", "streamable-http"],
    default="stdio",
    help="Select MCP server mode."
)
args = parser.parse_args()

toolkit = ArxivToolkit()
toolkit.mcp.run(args.mode)
```

- **stdio:** For local IPC (default, fast and secure for single-machine setups)
- **sse:** Server-Sent Events (good for remote servers and web clients)
- **streamable-http:** Modern, high-performance HTTP streaming

### Discoverable & Usable Instantly

Once running, your MCP server will:
- Advertise all available toolkit methods as standard MCP tools
- Support <b>dynamic tool discovery</b> (`tools/list` endpoint)
- Allow <b>any compatible agent or client</b> (not just CAMEL) to connect and call your tools

This means you can build an LLM workflow where, for example, Claude running in your browser or another service in your company network can call your toolkit directly—without ever importing your Python code.
</Card>
