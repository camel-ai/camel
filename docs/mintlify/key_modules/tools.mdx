---
title: "Tools"
icon: screwdriver-wrench
---

For more detailed usage information, please refer to our cookbook: [Tools Cookbook](../cookbooks/advanced_features/agents_with_tools.ipynb)

<Card title="What is a Tool?" icon="toolbox">
  A <b>Tool</b> in CAMEL is a callable function with a name, description, input parameters, and an output type.  
  Tools act as the interface between agents and the outside world—think of them like <b>OpenAI Functions</b> you can easily convert, extend, or use directly.
</Card>

<Card title="What is a Toolkit?" icon="screwdriver-wrench">
  A <b>Toolkit</b> is a curated collection of related tools designed to work together for a specific purpose.  
  CAMEL provides a range of built-in toolkits—covering everything from web search and data extraction to code execution, GitHub integration, and much more.
</Card>

## Get Started

<Card title="Install Toolkits" icon="terminal">
To unlock advanced capabilities for your agents, install CAMEL's extra tools package:
<CodeBlock language="sh" title="Install with pip">
pip install 'camel-ai[tools]'
</CodeBlock>
A tool in CAMEL is just a <b>FunctionTool</b>—an interface any agent can call to run custom logic or access APIs.
</Card>

<Card title="Define a Custom Tool" icon="toolbox">
You can easily create your own tools for any use case. Just write a Python function and wrap it using <b>FunctionTool</b>:

```python add_tool.py lines icon="python"
from camel.toolkits import FunctionTool

def add(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b

add_tool = FunctionTool(add)
```


Inspect your tool’s properties—such as its name, description, and OpenAI-compatible schema—using built-in methods:
<CodeGroup>
```python tool_properties.py
print(add_tool.get_function_name())          # add
print(add_tool.get_function_description())   # Adds two numbers.
print(add_tool.get_openai_function_schema()) # OpenAI Functions schema
print(add_tool.get_openai_tool_schema())     # OpenAI Tool format
```
```text output.txt
add
Adds two numbers.

{'name': 'add', 'description': 'Adds two numbers.', 'parameters': {'properties': {'a': {'type': 'integer', 'description': 'The first number to be added.'}, 'b': {'type': 'integer', 'description': 'The second number to be added.'}}, 'required': ['a', 'b'], 'type': 'object'}}

{'type': 'function', 'function': {'name': 'add', 'description': 'Adds two numbers.', 'parameters': {'properties': {'a': {'type': 'integer', 'description': 'The first number to be added.'}, 'b': {'type': 'integer', 'description': 'The second number to be added.'}}, 'required': ['a', 'b'], 'type': 'object'}}}
```
</CodeGroup>
</Card>

<Card title="Using Toolkits" icon="screwdriver-wrench">
Toolkits group related tools for specialized tasks—search, math, or automation. Use built‑in toolkits or build your own:

```python toolkit_usage.py lines icon="python"
from camel.toolkits import SearchToolkit
toolkit = SearchToolkit()
tools   = toolkit.get_tools()
```

You can also wrap toolkit methods as individual FunctionTools:

```python custom_tools.py lines icon="python"
from camel.toolkits import FunctionTool, SearchToolkit
google_tool = FunctionTool(SearchToolkit().search_google)
wiki_tool   = FunctionTool(SearchToolkit().search_wiki)
```
</Card>

<Card title="Passing Tools to ChatAgent" icon="user-cog">
You can enhance any <b>ChatAgent</b> with custom or toolkit-powered tools. Just pass the tools during initialization:

```python chatagent_tools.py lines icon="python"
from camel.agents import ChatAgent
tool_agent = ChatAgent(
    tools=tools,  # List of FunctionTools
)
response = tool_agent.step("A query related to the tool you added")
```
</Card>

## Built-in Toolkits

CAMEL provides a variety of built-in toolkits that you can use right away. Here's a comprehensive list of available toolkits:

| Toolkit | Description |
|---------|-------------|
| ArxivToolkit | A toolkit for interacting with the arXiv API to search and download academic papers. |
| AskNewsToolkit | A toolkit for fetching news, stories, and other content based on user queries using the AskNews API. |
| AudioAnalysisToolkit | A toolkit for audio processing and analysis, including transcription and question answering about audio content. |
| BrowserToolkit | A toolkit for browsing the web and interacting with web pages, including browser simulation and content extraction. |
| CodeExecutionToolkit | A toolkit for code execution which can run code in various sandboxes including internal Python, Jupyter, Docker, subprocess, or e2b. |
| OpenAIImageToolkit | A toolkit for image generation using OpenAI's DALL-E model. |
| DappierToolkit | A toolkit for searching real-time data and fetching AI recommendations across key verticals like News, Finance, Stock Market, Sports, Weather and more using the Dappier API. |
| DataCommonsToolkit | A toolkit for querying and retrieving data from the Data Commons knowledge graph, including SPARQL queries, statistical time series data, and property analysis. |
| ExcelToolkit | A toolkit for extracting and processing content from Excel files, including conversion to markdown tables. |
| FunctionTool | A base toolkit for creating function-based tools that OpenAI chat models can call, with support for schema parsing and synthesis. |
| FileWriteTool | A toolkit for creating, writing, and modifying text in files. |
| GitHubToolkit | A toolkit for interacting with GitHub repositories, including retrieving issues and creating pull requests. |
| GoogleCalendarToolkit | A toolkit for creating events, retrieving events, updating events, and deleting events from a Google Calendar |
| GoogleMapsToolkit | A toolkit for accessing Google Maps services, including address validation, elevation data, and timezone information. |
| GoogleScholarToolkit | A toolkit for retrieving information about authors and their publications from Google Scholar. |
| HumanToolkit | A toolkit for facilitating human-in-the-loop interactions and feedback in AI systems. |
| ImageAnalysisToolkit | A toolkit for comprehensive image analysis and understanding using vision-capable language models. |
| JinaRerankerToolkit | A toolkit for reranking documents (text or images) based on their relevance to a given query using the Jina Reranker model. |
| LinkedInToolkit | A toolkit for LinkedIn operations including creating posts, deleting posts, and retrieving user profile information. |
| MathToolkit | A toolkit for performing basic mathematical operations such as addition, subtraction, and multiplication. |
| MCPToolkit | A toolkit for interacting with external tools using the Model Context Protocol (MCP).  |
| MemoryToolkit | A toolkit for saving, loading, and clearing a ChatAgent's memory.  |
| MeshyToolkit | A toolkit for working with 3D mesh data and operations. |
| MinerUToolkit | A toolkit for extracting and processing document content using the MinerU API, with support for OCR, formula recognition, and table detection. |
| NetworkXToolkit | A toolkit for graph operations and analysis using the NetworkX library. |
| NotionToolkit | A toolkit for retrieving information from Notion pages and workspaces using the Notion API. |
| OpenAPIToolkit | A toolkit for working with OpenAPI specifications and REST APIs. |
| OpenBBToolkit | A toolkit for accessing and analyzing financial market data through the OpenBB Platform, including stocks, ETFs, cryptocurrencies, and economic indicators. |
| PPTXToolkit | A toolkit for creating and manipulating PowerPoint (PPTX) files, including adding slides, text, and images. |
| PubMedToolkit | A toolkit for interacting with PubMed's E-utilities API to access MEDLINE data. |
| RedditToolkit | A toolkit for Reddit operations including collecting top posts, performing sentiment analysis on comments, and tracking keyword discussions. |
| RetrievalToolkit | A toolkit for retrieving information from local vector storage systems based on specified queries. |
| SearchToolkit | A toolkit for performing web searches using various search engines like Google, DuckDuckGo, Wikipedia, Bing, BaiDu and Wolfram Alpha. |
| SemanticScholarToolkit | A toolkit for interacting with the Semantic Scholar API to fetch paper and author data from academic publications. |
| SlackToolkit | A toolkit for Slack operations including creating channels, joining channels, and managing channel membership. |
| StripeToolkit | A toolkit for processing payments and managing financial transactions via Stripe. |
| SymPyToolkit | A toolkit for performing symbolic computations using SymPy, including algebraic manipulation, calculus, and linear algebra. |
| TerminalToolkit | A toolkit for terminal operations such as searching for files by name or content, executing shell commands, and managing terminal sessions across multiple operating systems. |
| TwitterToolkit | A toolkit for Twitter operations including creating tweets, deleting tweets, and retrieving user profile information. |
| VideoAnalysisToolkit | A toolkit for analyzing video content with vision-language models, including frame extraction and question answering about video content. |
| VideoDownloaderToolkit | A toolkit for downloading videos and optionally splitting them into chunks, with support for various video services. |
| WeatherToolkit | A toolkit for fetching weather data for cities using the OpenWeatherMap API. |
| WhatsAppToolkit | A toolkit for interacting with the WhatsApp Business API, including sending messages, managing message templates, and accessing business profile information. |
| ZapierToolkit | A toolkit for interacting with Zapier's NLA API to execute actions through natural language commands and automate workflows. |
| KlavisToolkit | A toolkit for interacting with Kavis AI's API to create remote hosted production-ready MCP servers. |

## Using Toolkits as MCP Servers

<Card title="MCP Servers in CAMEL" icon="server">
CAMEL supports the <b>Model Context Protocol (MCP)</b>, letting you expose any toolkit as a standalone server. This enables distributed tool execution and seamless integration across multiple systems—clients can remotely discover and invoke tools via a consistent protocol.
</Card>

<Card title="What is MCP?" icon="anchor">
MCP (Model Context Protocol) is a unified protocol for connecting LLMs with external tools and services. In CAMEL, you can turn any toolkit into an MCP server, making its tools available for remote calls—ideal for building distributed, modular, and language-agnostic AI workflows.
</Card>

<Card title="Expose a Toolkit as an MCP Server" icon="rocket">
Any CAMEL toolkit can run as an MCP server. Example for ArxivToolkit:

```python arxiv_mcp_server.py lines icon="python"
import argparse
import sys
from camel.toolkits import ArxivToolkit

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Arxiv Toolkit in MCP server mode.",
        usage="python arxiv_mcp_server.py [--mode MODE] [--timeout TIMEOUT]"
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP server mode (default: 'stdio')"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Timeout in seconds (default: None)"
    )
    args = parser.parse_args()

    toolkit = ArxivToolkit(timeout=args.timeout)
    toolkit.run_mcp_server(mode=args.mode)
```
</Card>

<Card title="MCP Server Configuration" icon="settings">
Define how to launch your MCP servers with a config file:
<CodeGroup>
```json mcp_servers_config.json
{
  "mcpServers": {
    "arxiv_toolkit": {
      "command": "python",
      "args": [
        "-m",
        "examples.mcp_arxiv_toolkit.arxiv_toolkit_server",
        "--timeout",
        "30"
      ]
    }
  }
}
```
</CodeGroup>
</Card>

<Card title="Connect to MCP Servers as a Client" icon="plug">
From your client application, you can connect to MCP servers and use their tools remotely:
<CodeGroup>
```python mcp_client_example.py
import asyncio
from mcp.types import CallToolResult
from camel.toolkits.mcp_toolkit import MCPToolkit, MCPClient

async def run_example():
    mcp_toolkit = MCPToolkit(config_path="path/to/mcp_servers_config.json")
    await mcp_toolkit.connect()

    mcp_client: MCPClient = mcp_toolkit.servers[0]

    res = await mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)
    tools = [tool.name for tool in res.tools]
    print(f"Available tools: {tools}")

    result: CallToolResult = await mcp_client.session.call_tool(
        "tool_name", {"param1": "value1", "param2": "value2"}
    )
    print(result.content[0].text)

    await mcp_toolkit.disconnect()

if __name__ == "__main__":
    asyncio.run(run_example())
```
</CodeGroup>
</Card>

<Card title="Benefits of MCP Servers" icon="zap">
<ul>
  <li><b>Distributed Execution:</b> Run tools anywhere—across machines or containers.</li>
  <li><b>Process Isolation:</b> Each toolkit runs in its own process for reliability and security.</li>
  <li><b>Resource Management:</b> Allocate memory/CPU for heavy toolkits without impacting others.</li>
  <li><b>Scalability:</b> Scale specific toolkits up or down as your workload changes.</li>
  <li><b>Language Interoperability:</b> Implement MCP servers in any language that supports the protocol.</li>
</ul>
</Card>

<Card title="Best Practices for MCP Integration" icon="star">
<ul>
  <li><b>Timeouts:</b> Always set timeouts to prevent blocked operations.</li>
  <li><b>Error Handling:</b> Implement robust error and exception handling in both server and client code.</li>
  <li><b>Resource Cleanup:</b> Properly disconnect and free resources when finished.</li>
  <li><b>Configuration:</b> Use config files or environment variables for flexible deployment.</li>
  <li><b>Monitoring:</b> Add logging and health checks for production MCP deployments.</li>
</ul>
</Card>

<Card title="Conclusion" icon="trophy">
Tools—especially when deployed as MCP servers—are the bridge between CAMEL agents and the real world. With this architecture, you can empower agents to automate, fetch, compute, and integrate with almost any external system.
</Card>
