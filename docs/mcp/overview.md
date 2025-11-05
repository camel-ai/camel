---
title: 'Overview'
description: 'Introduction to MCP: what it is, why it matters, and how it transforms agent integration.'
icon: 'play'
---

## What is MCP all about?

MCP (Model Context Protocol) originated from an [Anthropic article](https://www.anthropic.com/news/model-context-protocol) published on November 25, 2024: *Introducing the Model Context Protocol*.

MCP defines **how applications and AI models exchange contextual information**.  
It enables developers to connect data sources, tools, and functions to LLMs using a universal, standardized protocol—much like USB-C enables diverse devices to connect via a single interface.

<CardGroup cols={2}>
  <Card title="Universal Standard" icon="universal-access">
    MCP aims to be the "USB-C for AI": one protocol, endless integrations. Plug in any tool or data source—LLM models just work with it.
  </Card>
  <Card title="Layer of Abstraction" icon="layer-group">
    Sits between LLMs and external tools/data, so you can add capabilities and context without changing agent code.
  </Card>
  <Card title="Flexible & Language-Agnostic" icon="language">
    MCP servers can be built in any language, run anywhere, and connect to anything—from cloud APIs to local files.
  </Card>
  <Card title="Consistent Developer Experience" icon="puzzle">
    Write your agent logic once, then extend it with new plugins or data via MCP, just by registering a new server.
  </Card>
</CardGroup>

## Visualizing MCP

Here’s how MCP acts as an **intermediate protocol layer** between LLMs and tools:

<Frame caption="Visualization of MCP as an intermediate layer between LLMs and tools">
  <img src="/images/mcp-architecture.jpeg" />
</Frame>

## What Changes with MCP?

<Frame caption="With MCP, tools and models connect through a single protocol instead of point-to-point integrations">
  <img src="/images/mcp-without-vs-with.jpg" />
</Frame>

## Why introduce MCP?

- **Ecosystem**: Leverage a growing library of MCP plugins—just plug them in.
- **Uniformity**: Not limited to any one model or vendor; if your agent supports MCP, you can swap models/tools anytime.
- **Data Security**: Keep sensitive data on your device. MCP servers decide what to expose—your private data never needs to leave your machine.

## MCP Architecture and Principles

**Basic Architecture**

MCP follows a **client-server model** with three main roles:

<CardGroup cols={3}>
  <Card title="MCP Host" icon="message-quote">
    Applications like Claude Desktop, IDEs, or AI tools that need external data/tools. The "Host" is the user-facing app.
  </Card>
  <Card title="MCP Client" icon="signal-stream">
    Built into the Host, the MCP Client manages protocol communication and connects to MCP Servers.
  </Card>
  <Card title="MCP Server" icon="server">
    Lightweight services (local or remote) that expose specific functions (e.g., read files, search web) via the MCP protocol.
  </Card>
</CardGroup>

- **Local Data Sources**: Files, folders, databases, and services MCP servers can securely access.
- **Remote Services**: Online APIs and cloud platforms accessible to MCP servers.

![MCP Server/Client diagram](/images/mcp-client-server-example.png)
### How it works, step by step:

1. **User asks:**  
   “What documents do I have on my desktop?” via the Host (e.g., Claude Desktop).

2. **Host (MCP Host):**  
   Receives your question and forwards it to the Claude model.

3. **Client (MCP Client):**  
   Claude model decides it needs more data, Client is activated to connect to a file system MCP Server.

4. **Server (MCP Server):**  
   The server reads your desktop directory and returns a list of documents.

5. **Results:**  
   Claude uses this info to answer your question, displayed in your desktop app.

This architecture **lets agents dynamically call tools and access data**—local or remote—while developers only focus on building the relevant MCPServer.  
**You don’t have to handle the nitty-gritty of connecting Hosts and Clients.**

<Note type="info">
For deeper architecture details and diagrams, see the  
<a href="https://modelcontextprotocol.io/docs/concepts/architecture" target="_blank">official MCP docs: Architecture Concepts</a>.
</Note>

## At a Glance

- **MCP** standardizes and simplifies agent-to-tool connections.
- **Developers** build or reuse MCP servers, not custom integrations for every agent.
- **Users** get safer, more flexible, and privacy-friendly AI workflows.

---

