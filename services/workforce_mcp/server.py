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
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import RolePlayingWorker, SingleAgentWorker
from camel.tasks import Task
from camel.toolkits import CodeExecutionToolkit, SearchToolkit, ThinkingToolkit
from camel.types import ModelPlatformType

# Import the workforce from the config
from services.workforce_mcp.config import workforce

# Create the MCP server
mcp = FastMCP("WorkforceMCP", dependencies=["camel-ai[all]"])


@mcp.tool()
async def process_task(
    content: str,
    ctx: Context,
    additional_info: Optional[str] = None,
) -> Dict[str, Any]:
    """Process a task using the CAMEL Workforce system.

    Args:
        content: The content of the task to be processed
        additional_info: Additional information about the task
        ctx: The MCP context object

    Returns:
        Dict containing the task result and details
    """
    await ctx.info(f"Processing task: {content}")

    # Create a new task
    task = Task(content=content, additional_info=additional_info or "")

    # Process the task with the workforce system
    result_task = workforce.process_task(task)

    # Return the task details
    return {
        "status": "success" if result_task.state.name == "DONE" else "failed",
        "task_id": result_task.id,
        "content": result_task.content,
        "result": result_task.result,
        "subtasks": [
            {
                "id": subtask.id,
                "content": subtask.content,
                "state": subtask.state.name,
                "result": subtask.result,
            }
            for subtask in result_task.subtasks
        ],
    }


@mcp.resource("workforce://info")
@mcp.tool()
def get_workforce_info() -> Dict[str, Any]:
    """Get information about the current workforce configuration.

    Returns:
        Dict containing information about the workforce
    """
    child_info = []
    for child in workforce._children:
        if isinstance(child, SingleAgentWorker):
            child_type = "SingleAgentWorker"
            tools = []
            if hasattr(child.worker, "tool_dict"):
                tools = list(child.worker.tool_dict.keys())
        elif isinstance(child, RolePlayingWorker):
            child_type = "RolePlayingWorker"
            tools = []
        else:
            child_type = type(child).__name__
            tools = []

        child_info.append(
            {
                "id": child.node_id,
                "type": child_type,
                "description": child.description,
                "tools": tools,
            }
        )

    return {
        "id": workforce.node_id,
        "description": workforce.description,
        "children": child_info,
    }


@mcp.tool()
async def add_single_agent_worker(
    description: str,
    system_message: str,
    ctx: Context,
    model_name: Optional[str] = None,
    tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Add a new single agent worker to the workforce.

    Args:
        description: Description of the worker
        system_message: System message for the worker
        model_name: Name of the model to use (optional)
        tools: List of tool names to enable (optional)
        ctx: The MCP context object

    Returns:
        Dict containing the result of the operation
    """
    await ctx.info(f"Adding new single agent worker: {description}")

    # Set up the tools for the worker
    worker_tools = []
    if tools:
        if "search" in tools:
            worker_tools.extend([SearchToolkit().search_duckduckgo])
        if "code" in tools:
            worker_tools.extend(CodeExecutionToolkit().get_tools())
        if "thinking" in tools:
            worker_tools.extend(ThinkingToolkit().get_tools())

    # Create the worker agent
    worker_msg = BaseMessage.make_assistant_message(
        role_name="Worker",
        content=system_message,
    )

    # Use specified model or default
    worker_model = None
    if model_name:
        try:
            worker_model = ModelFactory.create(
                model_platform=ModelPlatformType.OPENAI,
                model_type=model_name,
            )
        except Exception:  # Replace bare except with Exception
            # Fallback to default
            pass

    worker_agent = ChatAgent(
        worker_msg,
        model=worker_model,
        tools=worker_tools,
    )

    # Add the worker to the workforce
    workforce.add_single_agent_worker(description, worker_agent)

    return {
        "status": "success",
        "message": f"Added worker '{description}' to the workforce",
        "node_id": workforce._children[-1].node_id,
    }


@mcp.tool()
async def add_role_playing_worker(
    description: str,
    assistant_role_name: str,
    user_role_name: str,
    ctx: Context,
    chat_turn_limit: int = 3,
) -> Dict[str, Any]:
    """Add a new role-playing worker to the workforce.

    Args:
        description: Description of the worker
        assistant_role_name: Role name for the assistant
        user_role_name: Role name for the user
        chat_turn_limit: Maximum number of chat turns
        ctx: The MCP context object
    Returns:
        Dict containing the result of the operation
    """
    await ctx.info(f"Adding new role-playing worker: {description}")

    workforce.add_role_playing_worker(
        description=description,
        assistant_role_name=assistant_role_name,
        user_role_name=user_role_name,
        chat_turn_limit=chat_turn_limit,
    )

    return {
        "status": "success",
        "message": f"Added role-playing worker '{description}'",
        "node_id": workforce._children[-1].node_id,
    }


@mcp.tool()
async def reset_workforce(ctx: Context) -> Dict[str, str]:
    """Reset the workforce to its initial state.

    Args:
        ctx: The MCP context object

    Returns:
        Dict containing the status of the reset operation
    """
    await ctx.info("Resetting workforce")

    workforce.reset()

    return {
        "status": "success",
        "message": "Workforce has been reset successfully",
    }


@mcp.tool()
async def clone_workforce(
    ctx: Context,
    with_memory: bool = False,
) -> Dict[str, Any]:
    """Create a clone of the current workforce.

    Args:
        with_memory: Whether to include memory in the clone
        ctx: The MCP context object

    Returns:
        Dict containing information about the cloned workforce
    """
    await ctx.info(f"Cloning workforce (with_memory={with_memory})")

    # Create a clone of the workforce
    cloned_workforce = workforce.clone(with_memory=with_memory)

    # Return information about the cloned workforce
    return {
        "status": "success",
        "message": "Workforce has been cloned successfully",
        "original_id": workforce.node_id,
        "clone_id": cloned_workforce.node_id,
        "with_memory": with_memory,
    }


if __name__ == "__main__":
    mcp.run(transport='stdio')
