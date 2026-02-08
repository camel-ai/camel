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

from typing import TYPE_CHECKING, Dict

from camel.toolkits.base import BaseToolkit

if TYPE_CHECKING:
    from camel.societies.mailbox_society import AgentCard


class AgentDiscoveryToolkit(BaseToolkit):
    r"""A toolkit for discovering and querying information about other agents
    in the mailbox society.

    This toolkit provides methods for agents to:
    - List all available agents
    - Search for agents by capabilities, tags, or description
    - Get detailed information about specific agents

    Args:
        agent_id (str): Unique identifier for the agent using this toolkit.
        agent_registry (Dict[str, AgentCard]): Shared registry of agent cards.
    """

    def __init__(
        self,
        agent_id: str,
        agent_registry: Dict[str, 'AgentCard'],
    ):
        r"""Initialize the agent discovery toolkit.

        Args:
            agent_id (str): Unique identifier for the agent.
            agent_registry (Dict[str, AgentCard]): Shared registry of
                agent cards.
        """
        super().__init__()
        self.agent_id = agent_id
        self.agent_registry = agent_registry

    def list_all_agents(self) -> str:
        r"""List all available agents in the society.

        Returns:
            str: Formatted list of all agents with their basic information.
        """
        agents = [
            card
            for agent_id, card in self.agent_registry.items()
            if agent_id != self.agent_id
        ]

        if not agents:
            return "No other agents available in the society."

        lines = [f"Available agents ({len(agents)} total):\n"]
        for card in agents:
            lines.append(
                f"- {card.agent_id}: {card.description} "
                f"[{', '.join(card.tags[:3]) if card.tags else 'No tags'}]"
            )

        return "\n".join(lines)

    def search_agents_by_capability(self, capability: str) -> str:
        r"""Search for agents that have a specific capability.

        Args:
            capability (str): The capability to search for.

        Returns:
            str: List of agents with the specified capability.
        """
        matching_agents = []

        for agent_id, card in self.agent_registry.items():
            if agent_id == self.agent_id:
                continue

            if any(
                capability.lower() in cap.lower() for cap in card.capabilities
            ):
                matching_agents.append(card)

        if not matching_agents:
            return f"No agents found with capability matching '{capability}'."

        lines = [f"Agents with capability '{capability}':\n"]
        for card in matching_agents:
            caps = ', '.join(card.capabilities)
            lines.append(
                f"- {card.agent_id}: {card.description}\n  "
                f"Capabilities: {caps}"
            )

        return "\n".join(lines)

    def search_agents_by_tag(self, tag: str) -> str:
        r"""Search for agents that have a specific tag.

        Args:
            tag (str): The tag to search for.

        Returns:
            str: List of agents with the specified tag.
        """
        matching_agents = []

        for agent_id, card in self.agent_registry.items():
            if agent_id == self.agent_id:
                continue

            if any(tag.lower() in t.lower() for t in card.tags):
                matching_agents.append(card)

        if not matching_agents:
            return f"No agents found with tag matching '{tag}'."

        lines = [f"Agents with tag '{tag}':\n"]
        for card in matching_agents:
            tags = ', '.join(card.tags)
            lines.append(
                f"- {card.agent_id}: {card.description}\n  Tags: {tags}"
            )

        return "\n".join(lines)

    def search_agents_by_description(self, query: str) -> str:
        r"""Search for agents by description text.

        Args:
            query (str): Text to search for in agent descriptions.

        Returns:
            str: List of agents whose description matches the query.
        """
        matching_agents = []

        for agent_id, card in self.agent_registry.items():
            if agent_id == self.agent_id:
                continue

            if query.lower() in card.description.lower():
                matching_agents.append(card)

        if not matching_agents:
            return f"No agents found with description matching '{query}'."

        lines = [f"Agents matching '{query}':\n"]
        for card in matching_agents:
            lines.append(f"- {card.agent_id}: {card.description}")

        return "\n".join(lines)

    def get_agent_details(self, target_agent_id: str) -> str:
        r"""Get detailed information about a specific agent.

        Args:
            target_agent_id (str): ID of the agent to get details for.

        Returns:
            str: Detailed information about the agent.
        """
        if target_agent_id not in self.agent_registry:
            available = ', '.join(
                [
                    aid
                    for aid in self.agent_registry.keys()
                    if aid != self.agent_id
                ]
            )
            return (
                f"Agent '{target_agent_id}' not found. "
                f"Available agents: {available}"
            )

        card = self.agent_registry[target_agent_id]
        return str(card)

    def get_my_info(self) -> str:
        r"""Get information about the current agent.

        Returns:
            str: Information about this agent.
        """
        if self.agent_id not in self.agent_registry:
            return "Your agent card is not registered in the society."

        card = self.agent_registry[self.agent_id]
        return f"Your agent information:\n{card!s}"
