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

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from camel.agents import ChatAgent


@dataclass
class MailboxMessage:
    r"""Represents a message in the mailbox system.

    Args:
        sender_id (str): ID of the agent sending the message.
        recipient_id (str): ID of the agent receiving the message.
        content (str): The message content.
        subject (Optional[str]): Optional subject line for the message.
            (default: :obj:`None`)
        timestamp (datetime): When the message was created.
            (default: :obj:`datetime.now()`)
    """

    sender_id: str
    recipient_id: str
    content: str
    subject: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        r"""Return a string representation of the message."""
        return (
            f"Message(from={self.sender_id}, to={self.recipient_id}, "
            f"subject={self.subject or 'None'}, time={self.timestamp})"
        )


@dataclass
class AgentCard:
    r"""Describes an agent's identity and capabilities.

    An agent card provides metadata about an agent, including its ID,
    description, capabilities, and how to communicate with it.

    Args:
        agent_id (str): Unique identifier for the agent.
        description (str): Human-readable description of what the agent does.
        capabilities (List[str]): List of capabilities or skills the agent
            has.
        tags (List[str]): Optional tags for categorizing the agent.
            (default: :obj:`[]`)
        metadata (Dict): Additional metadata about the agent.
            (default: :obj:`{}`)
    """

    agent_id: str
    description: str
    capabilities: List[str]
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        r"""Convert the agent card to a dictionary.

        Returns:
            Dict: Dictionary representation of the agent card.
        """
        return {
            'agent_id': self.agent_id,
            'description': self.description,
            'capabilities': self.capabilities,
            'tags': self.tags,
            'metadata': self.metadata,
        }

    def __str__(self) -> str:
        r"""Return a formatted string representation of the agent card."""
        caps = ', '.join(self.capabilities) if self.capabilities else 'None'
        tags_str = ', '.join(self.tags) if self.tags else 'None'
        return (
            f"Agent Card:\n"
            f"  ID: {self.agent_id}\n"
            f"  Description: {self.description}\n"
            f"  Capabilities: {caps}\n"
            f"  Tags: {tags_str}\n"
        )


class MailboxSociety:
    r"""A multi-agent system using mailbox-based communication.

    This class manages a society of agents that communicate through
    message passing. Each agent has its own mailbox and can send/receive
    messages to/from other agents.

    Args:
        name (str): Name of the society. (default: :obj:`"MailboxSociety"`)
    """

    def __init__(self, name: str = "MailboxSociety"):
        r"""Initialize the mailbox society.

        Args:
            name (str): Name of the society.
        """
        self.name = name
        self.agents: Dict[str, ChatAgent] = {}
        self.agent_cards: Dict[str, AgentCard] = {}
        self.message_router: Dict[str, deque] = {}
        self._running = False

    def register_agent(
        self,
        agent: ChatAgent,
        agent_card: AgentCard,
    ) -> None:
        r"""Register an agent in the society.

        Args:
            agent (ChatAgent): The agent to register.
            agent_card (AgentCard): The agent's card describing its
                capabilities.

        Raises:
            ValueError: If an agent with the same ID is already registered.
        """
        agent_id = agent_card.agent_id

        if agent_id in self.agents:
            raise ValueError(
                f"Agent with ID '{agent_id}' is already registered."
            )

        self.agents[agent_id] = agent
        self.agent_cards[agent_id] = agent_card
        self.message_router[agent_id] = deque()

    def unregister_agent(self, agent_id: str) -> None:
        r"""Unregister an agent from the society.

        Args:
            agent_id (str): ID of the agent to unregister.

        Raises:
            ValueError: If the agent is not found.
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent with ID '{agent_id}' not found.")

        del self.agents[agent_id]
        del self.agent_cards[agent_id]
        del self.message_router[agent_id]

    def get_agent(self, agent_id: str) -> Optional[ChatAgent]:
        r"""Get an agent by its ID.

        Args:
            agent_id (str): ID of the agent.

        Returns:
            Optional[ChatAgent]: The agent, or None if not found.
        """
        return self.agents.get(agent_id)

    def get_agent_card(self, agent_id: str) -> Optional[AgentCard]:
        r"""Get an agent's card by its ID.

        Args:
            agent_id (str): ID of the agent.

        Returns:
            Optional[AgentCard]: The agent card, or None if not found.
        """
        return self.agent_cards.get(agent_id)

    def get_all_agent_cards(self) -> List[AgentCard]:
        r"""Get all agent cards in the society.

        Returns:
            List[AgentCard]: List of all agent cards.
        """
        return list(self.agent_cards.values())

    def search_agents(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
    ) -> List[AgentCard]:
        r"""Search for agents based on query, tags, or capabilities.

        Args:
            query (Optional[str]): Text to search for in agent descriptions.
                (default: :obj:`None`)
            tags (Optional[List[str]]): Tags to filter by.
                (default: :obj:`None`)
            capabilities (Optional[List[str]]): Capabilities to filter by.
                (default: :obj:`None`)

        Returns:
            List[AgentCard]: List of matching agent cards.
        """
        results = []

        for card in self.agent_cards.values():
            # Check query match
            if query and query.lower() not in card.description.lower():
                continue

            # Check tags match
            if tags and not any(tag in card.tags for tag in tags):
                continue

            # Check capabilities match
            if capabilities and not any(
                cap in card.capabilities for cap in capabilities
            ):
                continue

            results.append(card)

        return results

    def broadcast_message(
        self,
        sender_id: str,
        content: str,
        subject: Optional[str] = None,
    ) -> int:
        r"""Broadcast a message from one agent to all other agents.

        Args:
            sender_id (str): ID of the sender agent.
            content (str): Message content.
            subject (Optional[str]): Optional message subject.
                (default: :obj:`None`)

        Returns:
            int: Number of agents the message was sent to.

        Raises:
            ValueError: If the sender agent is not found.
        """
        if sender_id not in self.agents:
            raise ValueError(f"Sender agent '{sender_id}' not found.")

        count = 0
        for agent_id in self.agents.keys():
            if agent_id != sender_id:
                message = MailboxMessage(
                    sender_id=sender_id,
                    recipient_id=agent_id,
                    content=content,
                    subject=subject,
                )
                self.message_router[agent_id].append(message)
                count += 1

        return count

    def get_mailbox_count(self, agent_id: str) -> int:
        r"""Get the number of messages in an agent's mailbox.

        Args:
            agent_id (str): ID of the agent.

        Returns:
            int: Number of messages in the mailbox.

        Raises:
            ValueError: If the agent is not found.
        """
        if agent_id not in self.message_router:
            raise ValueError(f"Agent '{agent_id}' not found.")

        return len(self.message_router[agent_id])

    def clear_mailbox(self, agent_id: str) -> int:
        r"""Clear all messages from an agent's mailbox.

        Args:
            agent_id (str): ID of the agent.

        Returns:
            int: Number of messages cleared.

        Raises:
            ValueError: If the agent is not found.
        """
        if agent_id not in self.message_router:
            raise ValueError(f"Agent '{agent_id}' not found.")

        count = len(self.message_router[agent_id])
        self.message_router[agent_id].clear()
        return count

    def __str__(self) -> str:
        r"""Return a string representation of the society."""
        agent_list = ', '.join(self.agents.keys())
        return (
            f"MailboxSociety(name={self.name}, "
            f"agents=[{agent_list}], "
            f"total={len(self.agents)})"
        )

    def __repr__(self) -> str:
        r"""Return a detailed string representation of the society."""
        return self.__str__()
