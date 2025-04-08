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

import json
import logging
import os
import sys
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType

# ========================================================================
# CUSTOMIZATION SECTION - YOU CAN MODIFY THIS PART TO DEFINE YOUR OWN AGENT
# ========================================================================
# Configure logging - adjust level and format as needed
logging.basicConfig(
    stream=sys.stderr,  # Cannot use stdout if the transport is stdio
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Define the model - replace with your preferred model configuration
# Examples:
# 1. OpenAI: model_platform=ModelPlatformType.OPENAI, model_type="gpt-4o"
# 2. Anthropic: model_platform=ModelPlatformType.ANTHROPIC,
#    model_type="claude-3-opus-20240229"
model = ModelFactory.create(
    url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),  # Set this environment variable
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="nvidia/llama-3.1-nemotron-70b-instruct:free",
)

# Create a default chat agent - customize as needed
chat_agent = ChatAgent(
    model=model,
    system_message="You are a helpful assistant.",  # Customize this message
    # Uncomment to set a specific output language
    # output_language="en",  # or "zh", "es", "fr", etc.
)
# ========================================================================

# Create MCP server
mcp = FastMCP("ChatAgentMCP", dependencies=["camel-ai"])


@mcp.tool()
async def step(
    message: str,
    response_format: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute a single step in the chat session with the agent.

    Args:
        message: The input message for the agent
        response_format: Optional schema for structured response

    Returns:
        The response from the agent
    """
    format_cls = None
    if response_format:
        format_cls = type(
            'DynamicResponseFormat', (BaseModel,), response_format
        )

    response = await chat_agent.astep(message, format_cls)

    return {
        "status": "success",
        "messages": [msg.to_dict() for msg in response.msgs],
        "terminated": response.terminated,
        "info": response.info,
    }


@mcp.tool()
def add_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],  # JSON Schema
    function_code: str,
) -> Dict[str, str]:
    """Add a new tool to the chat agent."""
    try:
        exec_globals: Dict[str, Any] = {}
        exec_locals: Dict[str, Any] = {}
        exec(function_code, exec_globals, exec_locals)
        func = exec_locals.get(name)

        if not func or not callable(func):
            raise ValueError(f"Function '{name}' not found or not callable")

        from camel.toolkits import FunctionTool  # 你项目可能有类似的类

        tool = FunctionTool(
            func=func,
            openai_tool_schema=parameters,
        )

        chat_agent.add_tool(tool)

        return {
            "status": "success",
            "message": f"Tool '{name}' added successfully",
        }

    except Exception as e:
        logger.exception("Error adding tool")
        return {"status": "error", "message": str(e)}


@mcp.tool()
def remove_tool(name: str) -> Dict[str, str]:
    """Remove a tool from the chat agent."""
    success = chat_agent.remove_tool(name)
    if success:
        return {
            "status": "success",
            "message": f"Tool '{name}' removed successfully",
        }
    return {"status": "error", "message": f"Tool '{name}' not found"}


@mcp.tool()
def reset() -> Dict[str, str]:
    """Reset the chat agent to its initial state."""
    chat_agent.reset()
    return {"status": "success", "message": "Chat agent reset successfully"}


@mcp.tool()
def set_output_language(language: str) -> Dict[str, str]:
    """Set the output language for the chat agent."""
    chat_agent.output_language = language
    return {
        "status": "success",
        "message": f"Output language set to '{language}'",
    }


@mcp.resource("http://local/chat_history")
def get_chat_history() -> str:
    """Get the chat history for the agent."""
    history = chat_agent.chat_history
    return json.dumps(history, indent=2)


@mcp.resource("http://local/agent_info")
def get_agent_info() -> str:
    """Get information about the agent."""
    info = {
        "agent_id": chat_agent.agent_id,
        "role_name": chat_agent.role_name,
        "role_type": str(chat_agent.role_type),
        "model_type": str(chat_agent.model_type),
        "output_language": chat_agent.output_language,
    }
    return json.dumps(info, indent=2)


# @mcp.resource("available_tools")
# def get_available_tools() -> str:
#     """Get a list of available internal tools."""
#     tools = list(chat_agent.tool_dict.keys())
#     return json.dumps(tools, indent=2)


# @mcp.prompt()
# def system_prompt(content: str) -> str:
#     """Create a system prompt for the chat agent."""
#     chat_agent.reset()
#     chat_agent._original_system_message = BaseMessage(
#         role_name="System",
#         role_type=RoleType.DEFAULT,
#         meta_dict=None,
#         content=content,
#     )
#     chat_agent._system_message = (
#         chat_agent._generate_system_message_for_output_language()
#     )
#     chat_agent.init_messages()

#     return f"Set system prompt: {content}"


if __name__ == "__main__":
    mcp.run(transport='stdio')
