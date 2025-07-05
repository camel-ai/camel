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
import time
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.types import RoleType

if TYPE_CHECKING:
    from camel.agents import ChatAgent

logger = get_logger(__name__)


class AgentMessage(BaseMessage):
    r"""Represents a message between agents, extending BaseMessage.

    This class extends the standard CAMEL BaseMessage with additional
    attributes needed for inter-agent communication.
    """

    def __init__(
        self,
        message_id: str,
        sender_id: str,
        receiver_id: str,
        content: str,
        timestamp: float,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        # Initialize BaseMessage with standard fields
        super().__init__(
            role_name=sender_id,
            role_type=RoleType.ASSISTANT,
            meta_dict=metadata or {},
            content=content,
        )

        # Add agent-specific fields
        self.id = message_id
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.timestamp = timestamp
        self.reply_to = reply_to
        self.metadata = metadata or {}


class AgentCommunicationToolkit(BaseToolkit):
    r"""A toolkit for agent-to-agent communication in multi-agent systems.

    Enables agents to send messages to each other with message history tracking
    and integration with the CAMEL workforce system.

    Args:
        agents (Optional[Dict[str, ChatAgent]]): Dictionary mapping agent IDs
            to ChatAgent instances. (default: :obj:`None`)
        timeout (Optional[float]): Maximum execution time for operations in
            seconds. (default: :obj:`None`)
        max_message_history (int): Maximum messages to keep per agent.
            (default: :obj:`100`)
        get_response (bool): Whether to get responses from receiving agents
            by default. (default: :obj:`False`)

    Example:
        >>> msg_toolkit = AgentCommunicationToolkit(get_response=False)
        >>> msg_toolkit.register_agent("agent1", agent1)
        >>> msg_toolkit.register_agent("agent2", agent2)
        >>>
        >>> # Add tools to agents
        >>> for tool in msg_toolkit.get_tools():
        ...     agent1.add_tool(tool)
        ...     agent2.add_tool(tool)
    """

    def __init__(
        self,
        agents: Optional[Dict[str, "ChatAgent"]] = None,
        timeout: Optional[float] = None,
        max_message_history: int = 100,
        get_response: bool = False,
    ) -> None:
        super().__init__(timeout=timeout)
        self.agents = agents or {}
        self.max_message_history = max_message_history
        self.get_response = get_response

        # Message management
        self._message_history: Dict[str, List[AgentMessage]] = {}
        self._conversation_threads: Dict[str, List[str]] = {}

        logger.info(
            f"AgentCommunicationToolkit initialized with {len(self.agents)} "
            f"agents. "
            f"Max history: {max_message_history}, Get response: {get_response}"
        )

    def register_agent(self, agent_id: str, agent: "ChatAgent") -> str:
        r"""Register a new agent for communication.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent (ChatAgent): The ChatAgent instance to register.

        Returns:
            str: Confirmation message with registration details.

        Raises:
            ValueError: If agent_id is empty or agent is None.
        """
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already exists, overwriting")

        self.agents[agent_id] = agent

        # Initialize message history for new agent
        if agent_id not in self._message_history:
            self._message_history[agent_id] = []

        logger.info(f"Registered agent: {agent_id}")
        return (
            f"Agent {agent_id} registered successfully. "
            f"Total agents: {len(self.agents)}"
        )

    def _find_agent_id(self, agent_id: str) -> Optional[str]:
        r"""Find agent ID with flexible matching (case-insensitive, partial
        matches).
        """
        # First try exact match
        if agent_id in self.agents:
            return agent_id

        # Try case-insensitive exact match
        agent_id_lower = agent_id.lower()
        for registered_id in self.agents.keys():
            if registered_id.lower() == agent_id_lower:
                return registered_id

        # Try partial matching for common patterns like "writer_01" -> "Writer"
        # Remove common suffixes and prefixes
        clean_id = agent_id_lower

        # Remove common patterns: _01, _123, _agent, etc.
        import re

        clean_id = re.sub(r'_\d+$', '', clean_id)  # Remove trailing _numbers
        clean_id = re.sub(r'_agent$', '', clean_id)  # Remove trailing _agent
        clean_id = re.sub(r'^agent_', '', clean_id)  # Remove leading agent_

        # Try to match cleaned ID
        for registered_id in self.agents.keys():
            if registered_id.lower() == clean_id:
                return registered_id
            # Also try if the registered ID starts with our cleaned ID
            if registered_id.lower().startswith(clean_id):
                return registered_id

        return None

    def send_message(
        self,
        message: str,
        receiver_id: str,
        sender_id: str = "system",
        reply_to: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> str:
        r"""Sends a message to a specific agent.

        This function allows one agent to communicate directly with another by
        sending a message. The toolkit's get_response setting determines
        whether to get an immediate response or just send a notification. To
        get the `receiver_id` of the agent you want to communicate with, you
        can use the `list_available_agents` tool.

        Args:
            message (str): The content of the message to send.
            receiver_id (str): The unique identifier of the agent to receive
                the message. Use `list_available_agents()` to find the ID of
                the agent you want to talk to.
            sender_id (str): The unique identifier of the agent sending the
                message. This is typically your agent's ID.
                (default: :obj:`"system"`)
            reply_to (Optional[str]): The ID of a previous message this new
                message is a reply to. This helps create conversation threads.
                (default: :obj:`None`)
            metadata_json (Optional[str]): A JSON string containing extra
                information about the message.
                (default: :obj:`None`)

        Returns:
            str: A confirmation that the message was sent. If the toolkit's
                get_response setting is True, includes the response from the
                receiving agent.
        """
        if not message or not message.strip():
            raise ValueError("Message content cannot be empty")

        # Find the actual agent ID (case-insensitive)
        actual_receiver_id = self._find_agent_id(receiver_id)
        if not actual_receiver_id:
            available_agents = ", ".join(self.agents.keys())
            error_msg = (
                f"Agent {receiver_id} not found. "
                f"Available agents: {available_agents}"
            )
            logger.error(error_msg)
            return f"Error: {error_msg}"

        # Parse metadata from JSON string
        metadata = {}
        if metadata_json:
            try:
                metadata = json.loads(metadata_json)
                if not isinstance(metadata, dict):
                    logger.warning(
                        "Metadata must be a JSON object, using empty dict"
                    )
                    metadata = {}
            except json.JSONDecodeError:
                logger.warning(
                    "Invalid JSON in metadata_json, using empty dict"
                )
                metadata = {}

        # Create message
        agent_message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=actual_receiver_id,  # Use the resolved agent ID
            content=message,
            timestamp=time.time(),
            reply_to=reply_to,
            metadata=metadata,
        )

        # Handle threading
        if reply_to:
            self._update_conversation_thread(reply_to, agent_message.id)

        # Deliver message (with or without response)
        return self._deliver_message(agent_message, self.get_response)

    def _deliver_message(
        self, message: AgentMessage, get_response: bool
    ) -> str:
        r"""Deliver a message to the target agent, optionally getting a
        response.
        """
        try:
            target_agent = self.agents[message.receiver_id]
            logger.info(
                f"Delivering message {message.id} to agent "
                f"{message.receiver_id}"
            )

            self._add_to_history(message)

            # Create a clear, structured message for the agent
            structured_message = (
                f"A message has been received from agent with "
                f"ID '{message.sender_id}'.\n\n"
                "--- Message Content ---\n"
                f"{message.content}\n"
                "--- End of Message ---"
            )
            response = target_agent.step(structured_message)

            if get_response:
                # Extract and return response content
                if hasattr(response, 'msgs') and response.msgs:
                    response_content = response.msgs[0].content
                else:
                    response_content = str(response)

                logger.info(
                    f"Message {message.id} delivered with response. "
                    f"Response length: {len(response_content)}"
                )

                return (
                    f"Message {message.id} delivered to "
                    f"{message.receiver_id}. "
                    f"Response: {response_content[:100]}"
                    f"{'...' if len(response_content) > 100 else ''}"
                )
            else:
                # Message delivered but response not requested
                logger.info(
                    f"Message {message.id} delivered to agent "
                    f"{message.receiver_id} (response not requested)"
                )

                return (
                    f"Message {message.id} delivered to "
                    f"{message.receiver_id}. "
                    f"Message: '{message.content[:50]}"
                    f"{'...' if len(message.content) > 50 else ''}'"
                )

        except Exception as e:
            error_msg = f"Failed to deliver message {message.id}: {e!s}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

    def broadcast_message(
        self,
        message: str,
        sender_id: str = "system",
        exclude_agents: Optional[List[str]] = None,
    ) -> str:
        r"""Sends a message to all other agents in the system.

        This function is useful for making announcements or sending information
        that every agent needs. The message will be sent to all registered
        agents except for the sender and any agents specified in the
        `exclude_agents` list.

        Args:
            message (str): The content of the message to broadcast.
            sender_id (str): The unique identifier of the agent sending the
                message. This is typically your agent's ID.
                (default: :obj:`"system"`)
            exclude_agents (Optional[List[str]]): A list of agent IDs to
                exclude from the broadcast. The sender is automatically
                excluded.
                (default: :obj:`None`)

        Returns:
            str: A summary of the broadcast, showing which agents received the
                message and their responses.
        """
        if not message or not message.strip():
            return "Error: Message content cannot be empty"

        exclude_set = set(exclude_agents or [])
        if sender_id:
            exclude_set.add(sender_id)  # Don't send to self

        target_agents = [
            agent_id
            for agent_id in self.agents.keys()
            if agent_id not in exclude_set
        ]

        if not target_agents:
            return "No target agents available for broadcast"

        results = []
        for agent_id in target_agents:
            try:
                result = self.send_message(
                    message=message,
                    receiver_id=agent_id,
                    sender_id=sender_id,
                    metadata_json='{"broadcast": true}',
                )
                results.append(f"{agent_id}: {result}")
            except Exception as e:
                results.append(f"{agent_id}: Error - {e}")

        logger.info(f"Broadcast sent to {len(target_agents)} agents")
        return "Broadcast completed. Results:\n" + "\n".join(results)

    def get_message_history(
        self, agent_id: str, limit: Optional[int] = None
    ) -> str:
        r"""Retrieves the message history for a specific agent.

        This function allows you to see the messages sent and received by a
        particular agent, which can be useful for understanding past
        conversations. To get the `agent_id` for another agent, use the
        `list_available_agents` tool. You can also use this tool to get
        your own message history by providing your agent ID.

        Args:
            agent_id (str): The unique identifier of the agent whose message
                history you want to retrieve. Use `list_available_agents()`
                to find available agent IDs.
            limit (Optional[int]): The maximum number of recent messages to
                return. If not specified, it will return all messages up to
                the system's limit.
                (default: :obj:`None`)

        Returns:
            str: A formatted string containing the message history for the
                specified agent, or an error if the agent is not found.
        """
        actual_agent_id = self._find_agent_id(agent_id)
        if not actual_agent_id:
            return f"No message history found for agent {agent_id}"

        history = self._message_history.get(actual_agent_id, [])
        if limit:
            history = history[-limit:]

        if not history:
            return f"No messages in history for agent {agent_id}"

        formatted_history = []
        for msg in history:
            timestamp_str = time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(msg.timestamp)
            )
            formatted_history.append(
                f"[{timestamp_str}] {msg.sender_id} -> {msg.receiver_id}: "
                f"{msg.content[:100]}{'...' if len(msg.content) > 100 else ''}"
            )

        return (
            f"Message history for {agent_id} "
            f"({len(formatted_history)} messages):\n"
            + "\n".join(formatted_history)
        )

    def get_conversation_thread(self, message_id: str) -> str:
        r"""Retrieves a full conversation thread based on a message ID.

        When you send a message that is a reply to another, it creates a
        conversation thread. This function lets you retrieve all messages
        that are part of that thread. You can find message IDs in the
        message history or from the output of the `send_message` tool.

        Args:
            message_id (str): The unique identifier of any message within the
                conversation thread you want to retrieve.

        Returns:
            str: A formatted string containing all messages in the
                conversation, sorted by time, or an error if the thread is
                not found.
        """
        if message_id not in self._conversation_threads:
            return f"No conversation thread found for message {message_id}"

        thread_ids = self._conversation_threads[message_id]
        thread_messages = []

        # Find messages in history
        for agent_history in self._message_history.values():
            for msg in agent_history:
                if msg.id in thread_ids:
                    thread_messages.append(msg)

        # Sort by timestamp
        thread_messages.sort(key=lambda x: x.timestamp)

        if not thread_messages:
            return f"No messages found in thread for {message_id}"

        formatted_thread = []
        for msg in thread_messages:
            timestamp_str = time.strftime(
                '%H:%M:%S', time.localtime(msg.timestamp)
            )
            formatted_thread.append(
                f"[{timestamp_str}] {msg.sender_id}: {msg.content}"
            )

        return (
            f"Conversation thread ({len(formatted_thread)} messages):\n"
            + "\n".join(formatted_thread)
        )

    def list_available_agents(self) -> str:
        r"""Lists all agents currently available for communication.

        Call this function to discover which other agents are in the system
        that you can communicate with. The returned list will contain the
        unique IDs for each agent, which you can then use with tools like
        `send_message` and `get_message_history`.

        Returns:
            str: A formatted string listing the IDs and status of all
                available agents.
        """
        if not self.agents:
            return "No agents registered"

        agent_info = []
        for agent_id, agent in self.agents.items():
            # Get message count for this agent
            msg_count = len(self._message_history.get(agent_id, []))

            # Check if agent has pause support
            has_pause = hasattr(agent, 'pause_event')

            status_info = f"Messages: {msg_count}"
            if has_pause:
                status_info += ", Workforce-compatible"

            agent_info.append(f"  - {agent_id}: {status_info}")

        return f"Available agents ({len(self.agents)}):\n" + "\n".join(
            agent_info
        )

    def remove_agent(self, agent_id: str) -> str:
        r"""Remove an agent from the communication registry.

        Args:
            agent_id (str): Unique identifier of the agent to remove.

        Returns:
            str: Confirmation message with cleanup details.
        """
        if agent_id not in self.agents:
            return f"Error: Agent {agent_id} not found"

        del self.agents[agent_id]

        # Keep message history for audit purposes but note agent removal
        if agent_id in self._message_history:
            logger.info(
                f"Preserved {len(self._message_history[agent_id])} "
                f"messages for removed agent {agent_id}"
            )

        logger.info(f"Removed agent: {agent_id}")
        return (
            f"Agent {agent_id} removed successfully. "
            f"Remaining agents: {len(self.agents)}"
        )

    def get_toolkit_status(self) -> str:
        r"""Get comprehensive status of the message toolkit.

        Returns:
            str: Detailed status information including metrics and queue state.
        """
        total_messages = sum(
            len(history) for history in self._message_history.values()
        )

        status_info = [
            "AgentCommunicationToolkit Status:",
            f"  - Registered agents: {len(self.agents)}",
            f"  - Total message history: {total_messages}",
            f"  - Max history per agent: {self.max_message_history}",
        ]

        return "\n".join(status_info)

    def _add_to_history(self, message: AgentMessage) -> None:
        r"""Add a message to the history with size management."""
        # Add to sender's history
        sender_history = self._message_history.setdefault(
            message.sender_id, []
        )
        sender_history.append(message)

        # Add to receiver's history
        receiver_history = self._message_history.setdefault(
            message.receiver_id, []
        )
        receiver_history.append(message)

        # Trim history if needed
        for agent_id, history in self._message_history.items():
            if len(history) > self.max_message_history:
                self._message_history[agent_id] = history[
                    -self.max_message_history :
                ]

    def _update_conversation_thread(self, parent_id: str, new_id: str) -> None:
        r"""Update conversation threading."""
        if parent_id in self._conversation_threads:
            self._conversation_threads[parent_id].append(new_id)
        else:
            self._conversation_threads[new_id] = [parent_id, new_id]

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        communication functions in the toolkit.

        Note: Only includes functions that are safe and useful for LLMs to
        call. Administrative functions like register_agent and remove_agent are
        excluded as they should only be called programmatically.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects for agent
                communication and management.
        """
        return [
            FunctionTool(self.send_message),
            FunctionTool(self.broadcast_message),
            FunctionTool(self.list_available_agents),
            FunctionTool(self.get_message_history),
            FunctionTool(self.get_conversation_thread),
        ]
