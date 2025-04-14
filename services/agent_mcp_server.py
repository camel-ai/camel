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
from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from camel.utils import model_from_json_schema
from services.agent_config import agents_dict, description_dict

mcp = FastMCP("ChatAgentMCP", dependencies=["camel-ai"])


@mcp.tool()
async def step(
    name: str,
    message: str,
    response_format: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a single step in the chat session with the agent.

    Args:
        name: The name of the agent to use
        message: The input message for the agent
        response_format: Optional schema for structured response

    Returns:
        A dictionary containing the response from the agent
    """
    try:
        agent = agents_dict[name]
    except KeyError:
        return {
            "status": "error",
            "message": f"Agent with name {name} not found",
        }

    format_cls = None
    if response_format:
        format_cls = model_from_json_schema(
            "DynamicResponseFormat", response_format
        )

    response = await agent.astep(message, format_cls)

    return {
        "status": "success",
        "messages": [msg.to_dict() for msg in response.msgs],
        "terminated": response.terminated,
        "info": response.info,
    }


@mcp.tool()
def reset() -> Dict[str, str]:
    """Reset the chat agent to its initial state.
    Returns:
        A dictionary containing the status of the reset operation
    """
    for agent in agents_dict.values():
        agent.reset()
    return {"status": "success", "message": "All agents reset successfully"}


@mcp.tool()
def set_output_language(language: str) -> Dict[str, str]:
    """Set the output language for the chat agent.
    Args:
        language: The language to set the output language to

    Returns:
        A dictionary containing the status of the language setting operation
    """
    for agent in agents_dict.values():
        agent.output_language = language
    return {
        "status": "success",
        "message": f"Output language set to '{language}'",
    }


@mcp.resource("agent://")
def get_agents_info() -> Dict[str, Any]:
    """Get information about all agents provided by the server.
    Returns:
        A dictionary containing information about all agents
    """
    return description_dict


@mcp.resource("history://{name}")
def get_chat_history(name: str) -> Dict[str, Any]:
    """Get the chat history for the given agent.
    Args:
        name: The name of the agent to get the chat history for

    Returns:
        A dictionary containing the chat history for the given agent
    """
    try:
        agent = agents_dict[name]
    except KeyError:
        return {
            "status": "error",
            "message": f"Agent with name {name} not found",
        }
    return agent.chat_history


@mcp.resource("agent://{name}")
def get_agent_info(name: str) -> Dict[str, Any]:
    """Get information about the given agent.
    Args:
        name: The name of the agent to get information for

    Returns:
        A dictionary containing information about the given agent
    """
    try:
        agent = agents_dict[name]
    except KeyError:
        return {
            "status": "error",
            "message": f"Agent with name {name} not found",
        }
    info = {
        "agent_id": agent.agent_id,
        "model_type": str(agent.model_type),
        "token_limit": agent.token_limit,
        "output_language": agent.output_language,
        "description": description_dict[name],
    }
    return info


@mcp.resource("tool://{name}")
def get_available_tools(name: str) -> Dict[str, Any]:
    """Get a list of available internal tools.
    Args:
        name: The name of the agent to get the available tools for

    Returns:
        A dictionary containing the available internal tools
    """
    try:
        agent = agents_dict[name]
    except KeyError:
        return {
            "status": "error",
            "message": f"Agent with name {name} not found",
        }
    return agent.tool_dict


if __name__ == "__main__":
    mcp.run(transport='stdio')
