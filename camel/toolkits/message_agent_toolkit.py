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

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

if TYPE_CHECKING:
    from camel.agents import ChatAgent
else:
    # For runtime, use Any to avoid circular import issues
    ChatAgent = Any

logger = get_logger(__name__)


class MessageAgentTool(BaseToolkit):
    r"""A toolkit for agent-to-agent communication.

    This toolkit allows agents to send messages to other agents by their IDs
    and receive responses, enabling multi-agent collaboration.

    Args:
        agents (Optional[Dict[str, ChatAgent]], optional): Dictionary mapping
            agent IDs to ChatAgent instances. (default: :obj:`None`)
        timeout (Optional[float], optional): Maximum execution time allowed for
            toolkit operations in seconds. If None, no timeout is applied.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        agents: Optional[Dict[str, ChatAgent]] = None,
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.agents = agents or {}
        logger.info(
            f"MessageAgentTool initialized with {len(self.agents)} agents"
        )

    def register_agent(self, agent_id: str, agent: ChatAgent) -> str:
        r"""Register a new agent for communication.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent (ChatAgent): The ChatAgent instance to register.

        Returns:
            str: Confirmation message.
        """
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already exists, overwriting")

        self.agents[agent_id] = agent
        logger.info(f"Registered agent: {agent_id}")
        return f"Agent {agent_id} registered successfully"

    def message_agent(self, message: str, receiver_agent_id: str) -> str:
        r"""Send a message to another agent and get the response.

        Args:
            message (str): The message to send to the target agent.
            receiver_agent_id (str): Unique identifier of the target agent.

        Returns:
            str: Response from the target agent or error message if the
                operation fails.
        """
        if receiver_agent_id not in self.agents:
            error_message = f"Agent {receiver_agent_id} not found"
            logger.error(error_message)
            return f"Error: {error_message}"

        try:
            target_agent = self.agents[receiver_agent_id]
            logger.info(
                f"Sending message to agent {receiver_agent_id}: "
                f"{message[:50]}..."
            )

            response = target_agent.step(message)

            # Extract response content based on response type
            if hasattr(response, 'msgs') and response.msgs:
                response_content = response.msgs[0].content
            else:
                response_content = str(response)

            logger.info(
                f"Received response from {receiver_agent_id}: "
                f"{response_content[:50]}..."
            )
            return response_content

        except Exception as e:
            error_message = (
                f"Failed to communicate with agent {receiver_agent_id}: {e!s}"
            )
            logger.error(error_message)
            return f"Error: {error_message}"

    def list_available_agents(self) -> str:
        r"""List all registered agents and their IDs.

        Returns:
            str: Formatted list of registered agent IDs or message if no
                agents are registered.
        """
        if not self.agents:
            return "No agents registered"

        agent_list = ", ".join(self.agents.keys())
        logger.info(f"Listed agents: {agent_list}")
        return f"Available agents: {agent_list}"

    def remove_agent(self, agent_id: str) -> str:
        r"""Remove an agent from the communication registry.

        Args:
            agent_id (str): Unique identifier of the agent to remove.

        Returns:
            str: Confirmation message or error message if agent not found.
        """
        if agent_id not in self.agents:
            error_message = f"Agent {agent_id} not found"
            logger.error(error_message)
            return f"Error: {error_message}"

        del self.agents[agent_id]
        logger.info(f"Removed agent: {agent_id}")
        return f"Agent {agent_id} removed successfully"

    def get_agent_count(self) -> str:
        r"""Get the number of registered agents.

        Returns:
            str: Number of currently registered agents.
        """
        count = len(self.agents)
        logger.info(f"Agent count requested: {count}")
        return f"Total registered agents: {count}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        communication functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects for agent
                communication and management.
        """
        return [
            FunctionTool(self.message_agent),
            FunctionTool(self.register_agent),
            FunctionTool(self.list_available_agents),
            FunctionTool(self.remove_agent),
            FunctionTool(self.get_agent_count),
        ]
