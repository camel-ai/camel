# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""
Example: Using MCP Code Agent

This example demonstrates how to use the MCPCodeAgent, which interacts with
MCP servers through code execution instead of direct tool calls.

Based on:
- https://www.anthropic.com/engineering/code-execution-with-mcp
- https://arxiv.org/pdf/2506.01056 (MCP-Zero paper)
"""

import asyncio

from camel.agents import MCPCodeAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


async def basic_example():
    r"""Basic example of using MCPCodeAgent."""
    print("=" * 60)
    print("Example 1: Basic MCP Code Agent Usage")
    print("=" * 60)

    # Configuration for MCP servers
    # This example uses the filesystem server
    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "/tmp",
                ],
            }
        }
    }

    # Create agent with configuration
    agent = await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./mcp_workspace",
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        ),
    )

    # Ask agent to perform a task
    # The agent will generate code to interact with MCP tools
    response = await agent.astep(
        "List the files in the /tmp directory and count how many there are."
    )

    print("\nAgent Response:")
    print(response.msgs[0].content if response.msgs else "No response")

    # Disconnect when done
    await agent.disconnect()


async def skills_example():
    r"""Example demonstrating skills management."""
    print("\n" + "=" * 60)
    print("Example 2: Skills Management")
    print("=" * 60)

    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "/tmp",
                ],
            }
        }
    }

    agent = await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./mcp_workspace",
        enable_skills=True,
    )

    # Save a skill
    skill_code = """
async def count_files_in_directory(directory_path):
    '''Count the number of files in a directory.'''
    from servers.filesystem import list_directory
    
    result = await list_directory(path=directory_path)
    files = result.get('files', [])
    return len(files)
"""

    agent.save_skill(
        name="count_files",
        description="Count files in a directory",
        code=skill_code,
        tags=["filesystem", "utility"],
        examples=[
            "count = await count_files_in_directory('/tmp')",
            "print(f'Found {count} files')",
        ],
    )

    print("\nSaved skill: count_files")

    # List available skills
    skills = agent.list_skills()
    print(f"\nAvailable skills: {skills}")

    # Use the skill in a task
    response = await agent.astep(
        "Use the count_files skill to count files in /tmp, "
        "then create a summary report."
    )

    print("\nAgent Response:")
    print(response.msgs[0].content if response.msgs else "No response")

    await agent.disconnect()


async def multi_tool_composition_example():
    r"""Example showing composition of multiple MCP tools."""
    print("\n" + "=" * 60)
    print("Example 3: Multi-Tool Composition")
    print("=" * 60)

    # Configuration with multiple servers
    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "/tmp",
                ],
            },
            # Add more servers as needed
        }
    }

    agent = await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./mcp_workspace",
    )

    # Complex task requiring multiple tool calls
    response = await agent.astep(
        """
        Perform the following tasks:
        1. List all .txt files in /tmp
        2. For each .txt file, read its content
        3. Count the total number of lines across all files
        4. Save a summary to /tmp/file_summary.txt
        """
    )

    print("\nAgent Response:")
    print(response.msgs[0].content if response.msgs else "No response")

    await agent.disconnect()


async def context_efficiency_example():
    r"""Example showing reduced context consumption."""
    print("\n" + "=" * 60)
    print("Example 4: Context Efficiency")
    print("=" * 60)

    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "/tmp",
                ],
            }
        }
    }

    agent = await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./mcp_workspace",
    )

    # Task that would consume lots of tokens with direct tool calls
    # but is efficient with code execution
    response = await agent.astep(
        """
        Process all files in /tmp:
        1. Read each file
        2. Calculate statistics (size, line count, word count)
        3. Keep only the summary statistics, not the full content
        4. Return a JSON report with the statistics
        
        Do this efficiently by processing files in a loop without passing
        full content through context.
        """
    )

    print("\nAgent Response:")
    print(response.msgs[0].content if response.msgs else "No response")

    await agent.disconnect()


async def workspace_info_example():
    r"""Example showing workspace and tool discovery."""
    print("\n" + "=" * 60)
    print("Example 5: Workspace Information")
    print("=" * 60)

    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "/tmp",
                ],
            }
        }
    }

    agent = await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./mcp_workspace",
    )

    # Get workspace information
    workspace_info = agent.executor.get_workspace_info()

    print("\nWorkspace Directory:")
    print(workspace_info["workspace_dir"])

    print("\nDirectory Tree:")
    print(workspace_info["directory_tree"])

    print("\nAvailable Tools:")
    for server, tools in workspace_info["available_tools"].items():
        print(f"\n{server}:")
        for tool in tools:
            print(f"  - {tool}")

    await agent.disconnect()


async def main():
    r"""Run all examples."""
    try:
        await basic_example()
        await skills_example()
        await multi_tool_composition_example()
        await context_efficiency_example()
        await workspace_info_example()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
