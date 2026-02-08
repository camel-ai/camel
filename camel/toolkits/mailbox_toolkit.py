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
from typing import TYPE_CHECKING, Dict, Optional

from camel.toolkits.base import BaseToolkit

if TYPE_CHECKING:
    pass


class MailboxToolkit(BaseToolkit):
    r"""A toolkit for managing an agent's mailbox for sending and receiving
    messages in a multi-agent system.

    This toolkit provides methods for agents to:
    - Send messages to other agents
    - Receive messages from their mailbox
    - Check if they have unread messages
    - Get the number of messages in their mailbox

    Args:
        agent_id (str): Unique identifier for the agent that owns this mailbox.
        message_router (Optional[Dict[str, deque]]): Shared message routing
            dictionary that maps agent IDs to their message queues.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        agent_id: str,
        message_router: Optional[Dict[str, deque]] = None,
    ):
        r"""Initialize the mailbox toolkit.

        Args:
            agent_id (str): Unique identifier for the agent.
            message_router (Optional[Dict[str, deque]]): Shared message
                routing dictionary.
        """
        super().__init__()
        self.agent_id = agent_id
        self.message_router = message_router or {}
        # Initialize this agent's mailbox if not exists
        if agent_id not in self.message_router:
            self.message_router[agent_id] = deque()

    def send_message(
        self,
        recipient_id: str,
        content: str,
        subject: Optional[str] = None,
    ) -> str:
        r"""Send a message to another agent.

        Args:
            recipient_id (str): The ID of the recipient agent.
            content (str): The message content.
            subject (Optional[str]): Optional subject line for the message.
                (default: :obj:`None`)

        Returns:
            str: Confirmation message.
        """
        from camel.societies.mailbox_society import MailboxMessage

        if recipient_id not in self.message_router:
            return (
                f"Error: Agent '{recipient_id}' not found. "
                f"Available agents: {list(self.message_router.keys())}"
            )

        message = MailboxMessage(
            sender_id=self.agent_id,
            recipient_id=recipient_id,
            content=content,
            subject=subject,
        )

        self.message_router[recipient_id].append(message)
        return (
            f"Message sent successfully to '{recipient_id}'. "
            f"Subject: '{subject or 'No subject'}'"
        )

    def receive_messages(self, max_messages: int = 10) -> str:
        r"""Receive messages from the mailbox.

        Args:
            max_messages (int): Maximum number of messages to retrieve.
                (default: :obj:`10`)

        Returns:
            str: Formatted string containing the messages, or a message
                indicating no messages are available.
        """
        mailbox = self.message_router.get(self.agent_id, deque())

        if not mailbox:
            return "No messages in mailbox."

        messages = []
        count = min(max_messages, len(mailbox))

        for _ in range(count):
            if mailbox:
                msg = mailbox.popleft()
                messages.append(
                    f"From: {msg.sender_id}\n"
                    f"Subject: {msg.subject or 'No subject'}\n"
                    f"Content: {msg.content}\n"
                    f"Timestamp: {msg.timestamp}\n"
                )

        return (
            f"Received {len(messages)} message(s):\n\n"
            + "\n---\n".join(messages)
        )

    def check_messages(self) -> str:
        r"""Check the number of unread messages in the mailbox.

        Returns:
            str: Information about unread messages.
        """
        mailbox = self.message_router.get(self.agent_id, deque())
        count = len(mailbox)

        if count == 0:
            return "No unread messages."
        elif count == 1:
            return "You have 1 unread message."
        else:
            return f"You have {count} unread messages."

    def peek_messages(self, max_messages: int = 5) -> str:
        r"""Peek at messages without removing them from the mailbox.

        Args:
            max_messages (int): Maximum number of messages to peek at.
                (default: :obj:`5`)

        Returns:
            str: Formatted string containing the messages.
        """
        mailbox = self.message_router.get(self.agent_id, deque())

        if not mailbox:
            return "No messages in mailbox."

        messages = []
        count = min(max_messages, len(mailbox))

        for i in range(count):
            msg = mailbox[i]
            messages.append(
                f"From: {msg.sender_id}\n"
                f"Subject: {msg.subject or 'No subject'}\n"
                f"Preview: {msg.content[:100]}...\n"
            )

        return (
            f"Peeking at {len(messages)} message(s) "
            f"(of {len(mailbox)} total):\n\n" + "\n---\n".join(messages)
        )

    def get_available_agents(self) -> str:
        r"""Get a list of all available agents in the system.

        Returns:
            str: List of available agent IDs.
        """
        agents = [
            aid for aid in self.message_router.keys() if aid != self.agent_id
        ]

        if not agents:
            return "No other agents available."

        return f"Available agents: {', '.join(agents)}"
