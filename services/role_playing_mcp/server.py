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
import uuid
from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context, FastMCP

from camel.messages.base import BaseMessage
from camel.societies.role_playing import RolePlaying
from camel.types import TaskType
from services.role_playing_mcp.config import (
    DEFAULT_ROLE_SCENARIOS,
    active_sessions,
    default_assistant_role,
    default_model,
    default_task_prompt,
    default_task_type,
    default_user_role,
)

# Create an MCP server for the RolePlaying module
mcp = FastMCP("RolePlaying")


@mcp.tool()
def get_available_scenarios() -> Dict[str, Dict[str, str]]:
    """Get a list of available role playing scenarios.

    Returns:
        Dict[str, Dict[str, str]]: A dictionary of available scenarios with
        their configurations (without the model objects).
    """
    result = {}
    for scenario_name, config in DEFAULT_ROLE_SCENARIOS.items():
        # Don't return the model in the response as it's not serializable
        scenario_info = {k: str(v) for k, v in config.items() if k != "model"}
        result[scenario_name] = scenario_info
    return result


@mcp.tool()
def create_session(
    assistant_role_name: Optional[str] = None,
    user_role_name: Optional[str] = None,
    task_prompt: Optional[str] = None,
    task_type: Optional[str] = None,
    scenario_name: Optional[str] = None,
    with_task_specify: bool = True,
    with_task_planner: bool = False,
    with_critic: bool = False,
    output_language: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new role playing session.

    Args:
        assistant_role_name: The name of the role played by the assistant.
        user_role_name: The name of the role played by the user.
        task_prompt: The prompt for the task to be performed.
        task_type: The type of task (CODE, AI_SOCIETY, CREATIVE_WRITING, etc.).
        scenario_name: Name of a predefined scenario to use.
        with_task_specify: Whether to use a task specify agent.
        with_task_planner: Whether to use a task planner agent.
        with_critic: Whether to include a critic in the loop.
        output_language: The language to use for output.

    Returns:
        Dict[str, Any]: A dictionary containing session information.
    """
    # If a scenario name is provided, use that configuration
    if scenario_name and scenario_name in DEFAULT_ROLE_SCENARIOS:
        scenario_config = DEFAULT_ROLE_SCENARIOS[scenario_name]
        assistant_role = scenario_config["assistant_role_name"]
        user_role = scenario_config["user_role_name"]
        prompt = scenario_config["task_prompt"]
        task_type_val = scenario_config["task_type"]
        model = scenario_config.get("model", default_model)
    else:
        # Otherwise use provided or default values
        assistant_role = assistant_role_name or default_assistant_role
        user_role = user_role_name or default_user_role
        prompt = task_prompt or default_task_prompt
        # Convert task_type string to TaskType enum if provided
        task_type_val = default_task_type
        if task_type:
            for t in TaskType:
                if t.name == task_type:
                    task_type_val = t
                    break
        model = default_model

    # Create a new RolePlaying instance
    new_session = RolePlaying(
        assistant_role_name=assistant_role,
        user_role_name=user_role,
        task_prompt=prompt,
        with_task_specify=with_task_specify,
        with_task_planner=with_task_planner,
        with_critic_in_the_loop=with_critic,
        task_type=task_type_val,
        model=model,
        output_language=output_language,
    )

    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = new_session

    # Initialize the chat
    init_msg = new_session.init_chat()

    return {
        "session_id": session_id,
        "assistant_role": assistant_role,
        "user_role": user_role,
        "task_prompt": prompt,
        "initial_message": init_msg.content,
    }


@mcp.tool()
def chat_step(
    session_id: str,
    message: str,
    ctx: Context,
) -> Dict[str, Any]:
    """Advances the conversation by taking a message from the user.

    Args:
        session_id: The ID of the session to use.
        message: The message to send to the role-playing session.
        ctx: MCP context object for progress reporting.

    Returns:
        Dict[str, Any]: A dictionary containing the response.
    """
    if session_id not in active_sessions:
        return {"error": f"Session ID {session_id} not found"}

    session = active_sessions[session_id]

    # Create a message from the assistant
    assistant_msg = BaseMessage.make_assistant_message(
        role_name=session.assistant_agent.role_name,
        content=message,
    )

    ctx.info("Processing message...")

    # Advance the conversation
    (assistant_response, user_response) = session.step(assistant_msg)

    # Check if the conversation was terminated
    if (
        assistant_response.terminated
        or user_response.terminated
        or not assistant_response.msgs
        or not user_response.msgs
    ):
        return {
            "terminated": True,
            "response": "Conversation terminated.",
            "assistant_info": assistant_response.info,
            "user_info": user_response.info,
        }

    # Return the response
    return {
        "terminated": False,
        "assistant_response": assistant_response.msgs[0].content,
        "user_response": user_response.msgs[0].content,
    }


@mcp.tool()
async def chat_step_async(
    session_id: str,
    message: str,
    ctx: Context,
) -> Dict[str, Any]:
    """Asynchronously advances the conversation by taking a message from the
    user.

    Args:
        session_id: The ID of the session to use.
        message: The message to send to the role-playing session.
        ctx: MCP context object for progress reporting.

    Returns:
        Dict[str, Any]: A dictionary containing the response.
    """
    if session_id not in active_sessions:
        return {"error": f"Session ID {session_id} not found"}

    session = active_sessions[session_id]

    # Create a message from the assistant
    assistant_msg = BaseMessage.make_assistant_message(
        role_name=session.assistant_agent.role_name,
        content=message,
    )

    await ctx.report_progress(0, 1)
    ctx.info("Processing message...")

    # Advance the conversation asynchronously
    result = await session.astep(assistant_msg)
    assistant_response, user_response = result
    await ctx.report_progress(1, 1)

    # Check if the conversation was terminated
    if (
        assistant_response.terminated
        or user_response.terminated
        or not assistant_response.msgs
        or not user_response.msgs
    ):
        return {
            "terminated": True,
            "response": "Conversation terminated.",
            "assistant_info": assistant_response.info,
            "user_info": user_response.info,
        }

    # Return the response
    return {
        "terminated": False,
        "assistant_response": assistant_response.msgs[0].content,
        "user_response": user_response.msgs[0].content,
    }


@mcp.tool()
def get_session_info(session_id: str) -> Dict[str, Any]:
    """Get information about a specific role playing session.

    Args:
        session_id: The ID of the session to retrieve information for.

    Returns:
        Dict[str, Any]: Session information or error message.
    """
    if session_id not in active_sessions:
        return {"error": f"Session ID {session_id} not found"}

    session = active_sessions[session_id]
    return {
        "assistant_role": session.assistant_agent.role_name,
        "user_role": session.user_agent.role_name,
        "task_prompt": session.task_prompt,
        "with_task_specify": session.with_task_specify,
        "with_task_planner": session.with_task_planner,
        "with_critic": session.with_critic_in_the_loop,
    }


@mcp.tool()
def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete a role playing session.

    Args:
        session_id: The ID of the session to delete.

    Returns:
        Dict[str, Any]: Success or error message.
    """
    if session_id not in active_sessions:
        return {"error": f"Session ID {session_id} not found"}

    del active_sessions[session_id]
    return {"success": f"Session {session_id} deleted"}


@mcp.tool()
def clone_session(
    session_id: str, new_task_prompt: str, with_memory: bool = False
) -> Dict[str, Any]:
    """Clone an existing role playing session with a new task prompt.

    Args:
        session_id: The ID of the session to clone.
        new_task_prompt: The new task prompt for the cloned session.
        with_memory: Whether to copy the conversation history.

    Returns:
        Dict[str, Any]: New session information or error message.
    """
    if session_id not in active_sessions:
        return {"error": f"Session ID {session_id} not found"}

    # Get the existing session
    existing_session = active_sessions[session_id]

    # Clone the session
    new_session = existing_session.clone(
        task_prompt=new_task_prompt,
        with_memory=with_memory,
    )

    # Generate a new session ID
    new_session_id = str(uuid.uuid4())
    active_sessions[new_session_id] = new_session

    # Initialize the chat for the new session
    init_msg = new_session.init_chat()

    return {
        "session_id": new_session_id,
        "assistant_role": new_session.assistant_agent.role_name,
        "user_role": new_session.user_agent.role_name,
        "task_prompt": new_task_prompt,
        "initial_message": init_msg.content,
    }


if __name__ == "__main__":
    mcp.run()
