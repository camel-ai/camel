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

import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, List, Optional, Union

from camel.agents import ChatAgent
from camel.logger import get_logger

logger = get_logger(__name__)


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
        max_iterations (Optional[int]): Maximum number of message processing 
            iterations. If None, runs indefinitely until stopped.
            (default: :obj:`None`)
        process_interval (float): Time in seconds to wait between processing
            iterations. (default: :obj:`0.1`)
    """

    def __init__(
        self,
        name: str = "MailboxSociety",
        max_iterations: Optional[int] = None,
        process_interval: float = 0.1,
    ):
        r"""Initialize the mailbox society.

        Args:
            name (str): Name of the society.
            max_iterations (Optional[int]): Maximum number of message 
                processing iterations. If None, runs indefinitely until 
                stopped. (default: :obj:`None`)
            process_interval (float): Time in seconds to wait between
                processing iterations. (default: :obj:`0.1`)
        """
        self.name = name
        self.agents: Dict[str, ChatAgent] = {}
        self.agent_cards: Dict[str, AgentCard] = {}
        self.message_router: Dict[str, deque] = {}
        self.max_iterations = max_iterations
        self.process_interval = process_interval
        self._running = False
        self._stop_requested = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Initially not paused
        self._iteration_count = 0
        self._message_handlers: Dict[
            str, Callable[[ChatAgent, MailboxMessage], None]
        ] = {}

    def register_agent(
        self,
        agent: ChatAgent,
        agent_card: AgentCard,
    ) -> None:
        r"""Register an agent in the society.

        This method verifies that the agent_id is unique and automatically
        creates an empty mailbox (message queue) for the agent.

        Args:
            agent (ChatAgent): The agent to register.
            agent_card (AgentCard): The agent's card describing its
                capabilities. The agent_id from this card must be unique.

        Raises:
            ValueError: If an agent with the same ID is already registered,
                ensuring agent_id uniqueness across the society.
        """
        agent_id = agent_card.agent_id

        # Verify agent_id is unique
        if agent_id in self.agents:
            raise ValueError(
                f"Agent with ID '{agent_id}' is already registered. "
                f"Each agent must have a unique ID."
            )

        # Register agent and create its mailbox
        self.agents[agent_id] = agent
        self.agent_cards[agent_id] = agent_card
        self.message_router[agent_id] = deque()  # Create empty mailbox

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

    def set_message_handler(
        self,
        agent_id: str,
        handler: Callable[[ChatAgent, MailboxMessage], None],
    ) -> None:
        r"""Set a custom message handler for a specific agent.

        Args:
            agent_id (str): ID of the agent.
            handler (Callable): Function that takes (agent, message) and
                processes the message.

        Raises:
            ValueError: If the agent is not found.
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent '{agent_id}' not found.")

        self._message_handlers[agent_id] = handler

    def _default_message_handler(
        self, agent: ChatAgent, message: MailboxMessage
    ) -> None:
        r"""Default handler that has the agent step with the message content.

        Args:
            agent (ChatAgent): The agent to process the message.
            message (MailboxMessage): The message to process.
        """
        # Create a user message with the mailbox message content
        prompt = (
            f"You received a message from {message.sender_id}.\n"
            f"Subject: {message.subject or 'No subject'}\n"
            f"Content: {message.content}\n\n"
            "Please respond or take appropriate action."
        )

        try:
            # Have the agent process the message
            from camel.messages import BaseMessage

            user_msg = BaseMessage.make_user_message(
                role_name="System", content=prompt
            )
            agent.step(user_msg)
            logger.debug(
                f"Agent {message.recipient_id} processed message "
                f"from {message.sender_id}"
            )
        except Exception as e:
            logger.error(
                f"Error in agent {message.recipient_id} "
                f"processing message: {e}"
            )

    async def _process_messages_once(self) -> int:
        r"""Process one round of messages for all agents.

        Returns:
            int: Number of messages processed.
        """
        total_processed = 0

        for agent_id, agent in self.agents.items():
            mailbox = self.message_router.get(agent_id, deque())

            # Process all messages in the mailbox
            while mailbox:
                message = mailbox.popleft()
                total_processed += 1

                # Use custom handler if available, otherwise default
                handler = self._message_handlers.get(
                    agent_id, self._default_message_handler
                )

                try:
                    handler(agent, message)
                except Exception as e:
                    logger.error(
                        f"Error processing message for agent {agent_id}: {e}"
                    )

        return total_processed

    async def _process_messages_loop(self) -> None:
        r"""Main async loop for processing messages.

        This method continuously checks for messages and processes them
        until stopped or max iterations reached.
        """
        self._running = True
        self._stop_requested = False
        self._iteration_count = 0

        logger.info(
            f"Starting message processing for society '{self.name}' "
            f"(max_iterations={self.max_iterations})"
        )

        try:
            while not self._stop_requested and (
                self.max_iterations is None
                or self._iteration_count < self.max_iterations
            ):
                # Wait if paused
                await self._pause_event.wait()

                # Check if there are any messages to process
                has_messages = any(
                    len(mailbox) > 0
                    for mailbox in self.message_router.values()
                )

                if has_messages:
                    messages_processed = await self._process_messages_once()
                    logger.debug(
                        f"Iteration {self._iteration_count}: "
                        f"Processed {messages_processed} messages"
                    )

                self._iteration_count += 1

                # Wait before next iteration
                await asyncio.sleep(self.process_interval)

        except Exception as e:
            logger.error(f"Error in message processing loop: {e}")
            raise
        finally:
            self._running = False
            logger.info(
                f"Stopped message processing for society '{self.name}' "
                f"after {self._iteration_count} iterations"
            )

    async def run_async(
        self,
        initial_messages: Optional[
            Dict[str, Union[str, MailboxMessage]]
        ] = None,
    ) -> None:
        r"""Asynchronous entry point to start message processing.

        This method starts the message processing loop and runs until
        stopped or max iterations reached. Optionally sends initial messages
        to agents before starting the processing loop.

        Args:
            initial_messages (Optional[Dict[str, Union[str,
                MailboxMessage]]]):
                Optional initial messages to send to agents. Keys are
                agent IDs, values can be either string content or
                MailboxMessage objects. If string, a MailboxMessage will
                be created with sender "system". (default: :obj:`None`)
        """
        if self._running:
            logger.warning(f"Society '{self.name}' is already running")
            return

        # Send initial messages if provided
        if initial_messages:
            for agent_id, message in initial_messages.items():
                if agent_id not in self.agents:
                    logger.warning(
                        f"Agent '{agent_id}' not found, "
                        f"skipping initial message"
                    )
                    continue

                # Convert string to MailboxMessage if needed
                if isinstance(message, str):
                    message = MailboxMessage(
                        sender_id="system",
                        recipient_id=agent_id,
                        content=message,
                        subject="Initial Task",
                    )

                # Add to agent's mailbox
                if agent_id not in self.message_router:
                    self.message_router[agent_id] = deque()
                self.message_router[agent_id].append(message)
                logger.info(
                    f"Sent initial message to agent '{agent_id}': "
                    f"{message.subject or 'No subject'}"
                )

        await self._process_messages_loop()

    def run(
        self,
        initial_messages: Optional[
            Dict[str, Union[str, MailboxMessage]]
        ] = None,
    ) -> None:
        r"""Synchronous entry point to start message processing.

        This method wraps the async processing in a way that works with
        or without an existing event loop. Optionally sends initial messages
        to agents before starting the processing loop.

        Args:
            initial_messages (Optional[Dict[str, Union[str,
                MailboxMessage]]]):
                Optional initial messages to send to agents. Keys are
                agent IDs, values can be either string content or
                MailboxMessage objects. If string, a MailboxMessage will
                be created with sender "system". (default: :obj:`None`)
        """
        if self._running:
            logger.warning(f"Society '{self.name}' is already running")
            return

        try:
            # Check if there's already a running event loop
            asyncio.get_running_loop()
            # If we get here, we're in an async context
            # Use a thread to run the async code
            executor = ThreadPoolExecutor(max_workers=1)

            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(
                        self.run_async(initial_messages)
                    )
                finally:
                    new_loop.close()

            future = executor.submit(run_in_thread)
            return future.result()

        except RuntimeError:
            # No event loop running, create one
            return asyncio.run(self.run_async(initial_messages))

    def stop(self) -> None:
        r"""Stop the message processing loop.

        This method signals the processing loop to stop gracefully.
        """
        if not self._running:
            logger.warning(f"Society '{self.name}' is not running")
            return

        self._stop_requested = True
        logger.info(f"Stop requested for society '{self.name}'")

    def pause(self) -> None:
        r"""Pause the message processing loop.

        The loop will stop processing messages until resume() is called.
        """
        if not self._running:
            logger.warning(f"Society '{self.name}' is not running")
            return

        self._pause_event.clear()
        logger.info(f"Paused message processing for society '{self.name}'")

    def resume(self) -> None:
        r"""Resume the message processing loop after a pause.

        This method resumes message processing if it was paused.
        """
        if not self._running:
            logger.warning(f"Society '{self.name}' is not running")
            return

        self._pause_event.set()
        logger.info(f"Resumed message processing for society '{self.name}'")

    def reset(self) -> None:
        r"""Reset the society state.

        This clears all mailboxes and resets the iteration count.
        """
        if self._running:
            logger.warning(
                f"Cannot reset society '{self.name}' while running. "
                "Stop it first."
            )
            return

        for mailbox in self.message_router.values():
            mailbox.clear()

        self._iteration_count = 0
        self._stop_requested = False
        self._message_handlers.clear()
        logger.info(f"Reset society '{self.name}'")
