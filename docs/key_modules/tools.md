# Tools

For more detailed usage information, please refer to our cookbook: [Tools Cookbook](../cookbooks/advanced_features/agents_with_tools.ipynb)

## 1. Concept
Tools serve as interfaces that allow LLMs and Agents to interact with the world. A tool is essentially a function that has a name, a description, input parameters, and an output type. In this section, we will introduce the tools currently supported by CAMEL and explain how to define your own tools and Toolkits.

**Tools:** Tools are akin to OpenAI Functions and can be easily converted to that format. In CAMEL, we offer a variety of commonly used tools that you can utilize directly. While built-in tools can be quite useful, it's highly likely that you'll need to define your own tools. This guide for detailed instructions on how to create custom tools.

**Toolkits:** Toolkits are collections of tools that are designed to work well together. 

## 2. Get Started

To enhance your agents' capabilities with CAMEL tools, start by installing our additional tools package:
```sh
pip install 'camel-ai[tools]'
```

In CAMEL, a tool is an `FunctionTool` that LLMs can call.


### 2.1 How to Define Your Own Tool?

Developers can create custom tools tailored to their agent's specific needs with ease. Here's how you can define and use a custom tool:

**Example: Adding Two Numbers**

First, define your function and wrap it using the `FunctionTool`

```python
from camel.toolkits import FunctionTool

def add(a: int, b: int) -> int:
    r"""Adds two numbers.

    Args:
        a (int): The first number to be added.
        b (int): The second number to be added.

    Returns:
        integer: The sum of the two numbers.
    """
    return a + b

# Wrap the function with FunctionTool
add_tool = FunctionTool(add)
```

**Accessing Tool Properties**

Once your tool is defined, you can inspect its properties using built-in methods:

Retrieve the function's name:

```python
print(add_tool.get_function_name())
```

```markdown
>>> add
```

Get the description of what the function does:

```python
print(add_tool.get_function_description())
```

```markdown
>>> Adds two numbers.
```

Fetch the schema representation for OpenAI functions:

```python
print(add_tool.get_openai_function_schema())
```

```markdown
>>> 
{'name': 'add',
 'description': 'Adds two numbers.',
 'parameters': {'properties': {'a': {'type': 'integer',
    'description': 'The first number to be added.'},
   'b': {'type': 'integer', 'description': 'The second number to be added.'}},
  'required': ['a', 'b'],
  'type': 'object'}}
```

Retrieve the tool schema, compatible with OpenAI's structure:

```python
print(add_tool.get_openai_tool_schema())
```

```markdown
>>> 
{'type': 'function',
 'function': {'name': 'add',
  'description': 'Adds two numbers.',
  'parameters': {'properties': {'a': {'type': 'integer',
     'description': 'The first number to be added.'},
    'b': {'type': 'integer', 'description': 'The second number to be added.'}},
   'required': ['a', 'b'],
   'type': 'object'}}}
```

### 2.2 Toolkits

Toolkits are collections of tools that are designed to be used together for specific tasks. All Toolkits expose a `get_tools` method which returns a list of tools. You can therefore do:

```python
from camel.toolkits import SearchToolkit

# Initialize a toolkit
toolkit = SearchToolkit()

# Get list of tools
tools = toolkit.get_tools()
```

To utilize specific tools from the toolkits, you can implement code like the following:

```python
from camel.toolkits import FunctionTool, SearchToolkit

google_tool = FunctionTool(SearchToolkit().search_google)
wiki_tool = FunctionTool(SearchToolkit().search_wiki)
```

### 2.3 Passing Tools to `ChatAgent`
Enhance the functionality of a ChatAgent by passing custom tools during initialization. Here's how you can do it:

```python
from camel.agents import ChatAgent

# Initialize a ChatAgent with your custom tools
tool_agent = ChatAgent(
    tools=tools,
)

# Interact with the agent
response = tool_agent.step("A query related to the tool you added")
```

## 3. Built-in Toolkits

CAMEL provides a variety of built-in toolkits that you can use right away. Here's a comprehensive list of available toolkits:

| Toolkit | Description |
|---------|-------------|
| ArxivToolkit | A toolkit for interacting with the arXiv API to search and download academic papers. |
| AskNewsToolkit | A toolkit for fetching news, stories, and other content based on user queries using the AskNews API. |
| AudioAnalysisToolkit | A toolkit for audio processing and analysis, including transcription and question answering about audio content. |
| BrowserToolkit | A toolkit for browsing the web and interacting with web pages, including browser simulation and content extraction. |
| CodeExecutionToolkit | A toolkit for code execution which can run code in various sandboxes including internal Python, Jupyter, Docker, subprocess, or e2b. |
| DalleToolkit | A toolkit for image generation using OpenAI's DALL-E model. |
| DappierToolkit | A toolkit for searching real-time data and fetching AI recommendations across key verticals like News, Finance, Stock Market, Sports, Weather and more using the Dappier API. |
| DataCommonsToolkit | A toolkit for querying and retrieving data from the Data Commons knowledge graph, including SPARQL queries, statistical time series data, and property analysis. |
| ExcelToolkit | A toolkit for extracting and processing content from Excel files, including conversion to markdown tables. |
| FunctionTool | A base toolkit for creating function-based tools that OpenAI chat models can call, with support for schema parsing and synthesis. |
| FileWriteTool | A toolkit for creating, writing, and modifying text in files. |
| GitHubToolkit | A toolkit for interacting with GitHub repositories, including retrieving issues and creating pull requests. |
| GoogleMapsToolkit | A toolkit for accessing Google Maps services, including address validation, elevation data, and timezone information. |
| GoogleScholarToolkit | A toolkit for retrieving information about authors and their publications from Google Scholar. |
| HumanToolkit | A toolkit for facilitating human-in-the-loop interactions and feedback in AI systems. |
| ImageAnalysisToolkit | A toolkit for comprehensive image analysis and understanding using vision-capable language models. |
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

## 4. Using Toolkits as MCP Servers

CAMEL supports the Model Context Protocol (MCP), which allows you to expose toolkits as standalone servers that can be accessed by clients. This enables distributed tool execution and integration with various systems.

### 4.1 What is MCP?

Model Context Protocol (MCP) is a protocol that enables language models to interact with external tools and services. In CAMEL, toolkits can be exposed as MCP servers, allowing clients to discover and call tools remotely.

### 4.2 Creating an MCP Server from a Toolkit

Any CAMEL toolkit can be exposed as an MCP server. Here's how to create an MCP server using the ArXiv toolkit as an example:

```python
# arxiv_toolkit_server.py
import argparse
import sys

from camel.toolkits import ArxivToolkit

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Arxiv Toolkit with MCP server mode.",
        usage=f"python {sys.argv[0]} [--mode MODE]",
    )
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP server mode (default: 'stdio')",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Timeout for the MCP server (default: None)",
    )

    args = parser.parse_args()

    toolkit = ArxivToolkit(timeout=args.timeout)

    # Run the toolkit as an MCP server
    toolkit.mcp.run(args.mode)
```

The server can be run in two modes:
- `stdio`: Standard input/output mode (default)
- `sse`: Server-Sent Events mode

### 4.3 Configuring MCP Servers

Create a configuration file (e.g., `mcp_servers_config.json`) to specify how to launch your MCP servers:

```json
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

### 4.4 Connecting to MCP Servers from a Client

You can connect to MCP servers and use their tools from a client application:

```python
import asyncio
from mcp.types import CallToolResult
from camel.toolkits.mcp_toolkit import MCPToolkit, _MCPServer

async def run_example():
    # Initialize the MCPToolkit with your configuration file
    mcp_toolkit = MCPToolkit(config_path="path/to/mcp_servers_config.json")

    # Connect to all configured MCP servers
    await mcp_toolkit.connect()

    # Get the first MCP server
    mcp_client: _MCPServer = mcp_toolkit.servers[0]
    
    # List available tools from the server
    res = await mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)

    tools = [tool.name for tool in res.tools]
    print(f"Available tools: {tools}")

    # Call a tool from the server
    result: CallToolResult = await mcp_client.session.call_tool(
        "tool_name", {"param1": "value1", "param2": "value2"}
    )
    print(result.content[0].text)

    # Disconnect from all servers
    await mcp_toolkit.disconnect()

if __name__ == "__main__":
    asyncio.run(run_example())
```

### 4.5 Benefits of Using MCP Servers

1. **Distributed Execution**: Run tools on separate machines or processes.
2. **Isolation**: Each toolkit runs in its own process, providing better isolation and stability.
3. **Resource Management**: Allocate resources to specific toolkits based on their requirements.
4. **Scalability**: Scale individual toolkits independently based on demand.
5. **Language Interoperability**: MCP servers can be implemented in different programming languages.

### 4.6 Best Practices

- **Timeouts**: Always set appropriate timeouts to prevent hanging operations.
- **Error Handling**: Implement proper error handling for both server and client sides.
- **Resource Cleanup**: Ensure proper disconnection from servers when done.
- **Configuration Management**: Use environment variables or configuration files for server settings.
- **Monitoring**: Implement logging and monitoring for MCP servers in production environments.

## 5. Conclusion

Tools are essential for extending the capabilities of CAMEL agents, empowering them to perform a wide range of tasks and collaborate efficiently.
