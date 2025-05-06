# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import json

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import PulseMCPSearchToolkit
from camel.types import ModelPlatformType, ModelType

# Create an instance of the MCP search toolkit
search_toolkit = PulseMCPSearchToolkit()

# Example 1: Search for MCP servers with a specific query
print("Example 1: Search for MCP servers related to 'github'")
search_results = search_toolkit.search_mcp_servers(
    query="github",
    top_k=4,  # Limit to 4 results for brevity
)
print(json.dumps(search_results, indent=2))
"""
===============================================================================
Example 1: Search for MCP servers related to 'github'
{
  "servers": [
    {
      "name": "GitHub",
      "url": "https://www.pulsemcp.com/servers/modelcontextprotocol-github",
      "external_url": null,
      "short_description": "Manage repositories, issues, and search code via GitHub API.",
      "source_code_url": "https://github.com/modelcontextprotocol/servers/tree/HEAD/src/github",
      "github_stars": 41847,
      "package_registry": "npm",
      "package_name": "@modelcontextprotocol/server-github",
      "package_download_count": 710829,
      "EXPERIMENTAL_ai_generated_description": "This GitHub MCP server, developed by Anthropic, provides AI assistants with comprehensive access to GitHub's API functionality. It enables operations like file management, repository creation, issue tracking, and advanced code search across GitHub. Built in TypeScript, the implementation handles authentication, request formatting, and exposes GitHub's features through a standardized MCP interface. By bridging AI models and GitHub's development platform, this server allows AI systems to interact with code repositories, manage projects, and analyze development workflows. It is particularly useful for AI assistants supporting software development teams in tasks like code review, project management, and collaborative coding on GitHub."
    },
    {
      "name": "GitHub",
      "url": "https://www.pulsemcp.com/servers/github",
      "external_url": "https://github.blog/changelog/2025-04-04-github-mcp-server-public-preview/",
      "short_description": "Integration with GitHub Issues, Pull Requests, and more.",
      "source_code_url": "https://github.com/github/github-mcp-server",
      "github_stars": 12571,
      "package_registry": null,
      "package_name": null,
      "package_download_count": null,
      "EXPERIMENTAL_ai_generated_description": "A Model Context Protocol (MCP) server for GitHub that enables AI assistants to access GitHub repositories, issues, pull requests, and other GitHub data."
    },
    {
      "name": "Pipedream",
      "url": "https://www.pulsemcp.com/servers/pipedream",
      "external_url": "https://mcp.pipedream.com/",
      "short_description": "Access hosted MCP servers or deploy your own for 2,500+ APIs like Slack, GitHub, Notion, Google Drive, and more, all with built-in auth and 10k tools.",
      "source_code_url": "https://github.com/pipedreamhq/pipedream/tree/HEAD/modelcontextprotocol",
      "github_stars": 9646,
      "package_registry": "npm",
      "package_name": "@pipedream/mcp",
      "package_download_count": 2303,
      "EXPERIMENTAL_ai_generated_description": "Pipedream's MCP server lets you:\n- Run the servers locally with npx @pipedream/mcp\n- Host the servers yourself to use them within your app or company\n\nSome of the key features include the ability to:\n- Run your own MCP server for over 2,500 apps\n- Manage servers for your users, in your own app.\n- Connect accounts, configure params, and make API requests, all via tools\n- Fully-managed OAuth and credential storage "
    },
    {
      "name": "GitMCP (GitHub to MCP)",
      "url": "https://www.pulsemcp.com/servers/idosal-git-mcp",
      "external_url": "https://gitmcp.io/",
      "short_description": "GitMCP is a free, open-source, remote Model Context Protocol (MCP) server that transforms any GitHub project (repositories or GitHub pages) into a documentation hub. It allows AI tools like Cursor to access up-to-date documentation and code, ending hallucinations seamlessly.",
      "source_code_url": "https://github.com/idosal/git-mcp",
      "github_stars": 1864,
      "package_registry": null,
      "package_name": null,
      "package_download_count": null,
      "EXPERIMENTAL_ai_generated_description": "Transforms any GitHub project (repositories or GitHub pages) into a documentation hub. It allows AI tools like Cursor to access up-to-date documentation and code, ending hallucinations seamlessly."
    }
  ]
}
===============================================================================
"""  # noqa: E501

# Example 2: Search for MCP servers restricted to a specific package registry
print(
    "Example 2: Search for MCP servers restricted to a specific package registry"  # noqa: E501
)
search_results = search_toolkit.search_mcp_servers(
    query="Slack",
    package_registry="npm",  # Only search for servers registered in npm
    top_k=1,
)
print(json.dumps(search_results, indent=2))
"""
===============================================================================
Example 2: Search for MCP servers restricted to a specific package registry
{
  "servers": [
    {
      "name": "Slack",
      "url": "https://www.pulsemcp.com/servers/slack",
      "external_url": null,
      "short_description": "Send messages, manage channels, and access workspace history.",
      "source_code_url": "https://github.com/modelcontextprotocol/servers/tree/HEAD/src/slack",
      "github_stars": 41847,
      "package_registry": "npm",
      "package_name": "@modelcontextprotocol/server-slack",
      "package_download_count": 188989,
      "EXPERIMENTAL_ai_generated_description": "This Slack MCP Server, developed by the Anthropic team, provides a robust interface for language models to interact with Slack workspaces. It enables AI agents to perform a wide range of Slack-specific tasks including listing channels, posting messages, replying to threads, adding reactions, retrieving channel history, and accessing user information. The implementation distinguishes itself by offering comprehensive Slack API integration, making it ideal for AI-driven workplace communication and automation. By leveraging Slack's Bot User OAuth Tokens, it ensures secure and authorized access to workspace data. This tool is particularly powerful for AI assistants designed to enhance team collaboration, automate routine communication tasks, and provide intelligent insights from Slack conversations."
    }
  ]
}
===============================================================================
"""  # noqa: E501

# Example 3: Search for MCP servers using a chat agent
model = ModelFactory.create(
    model_platform=ModelPlatformType.ANTHROPIC,
    model_type=ModelType.CLAUDE_3_7_SONNET,
)

agent = ChatAgent(
    model=model,
    system_message="You are a helpful assistant that can search for MCP servers.",  # noqa: E501
    tools=search_toolkit.get_tools(),
)

response = agent.step("Search for MCP servers related to 'SQL'")
print(response.msg.content)
"""
===============================================================================
I've searched for MCP servers related to SQL and found 5 relevant results:

1. SQLite Server
- Allows querying and analyzing SQLite databases directly
- Available on PyPI as 'mcp-server-sqlite'
- Features tools for database operations and schema inspection

2. PostgreSQL Server
- Provides read-only access to Postgres databases
- Available on npm as '@modelcontextprotocol/server-postgres'
- Focuses on database schema inspection and SQL query execution

3. MySQL Server
- Enables exploring schemas and executing read-only SQL queries on MySQL databases
- Available on PyPI as 'mysql-mcp-server'
- Offers secure database interaction capabilities

4. Read MySQL Server
- Provides secure read-only MySQL database access
- Available on npm as '@benborla29/mcp-server-mysql'
- Built in TypeScript with focus on security through read-only transactions

5. SQL Alchemy Server
- Integrates with multiple SQL database engines using SQLAlchemy
- Supports PostgreSQL, MySQL, MariaDB, SQLite, and other SQLAlchemy-compatible databases
- Offers tools for database exploration and query assistance

Each server provides specific functionality for interacting with different types of SQL databases, with varying features and security measures. Would you like more specific information about any of these servers?
===============================================================================
"""  # noqa: E501
