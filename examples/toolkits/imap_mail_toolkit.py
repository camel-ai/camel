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


from camel.agents.chat_agent import ChatAgent
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import IMAPMailToolkit
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


def main() -> None:
    r"""Simple example using IMAP Mail Toolkit with a chat agent."""

    # Example 1: Basic usage (connections auto-managed with idle timeout)
    # The toolkit will automatically close idle connections after 5 minutes
    # and clean up on object destruction
    mail_toolkit = IMAPMailToolkit(
        imap_server="imap.gmail.com",
        smtp_server="smtp.gmail.com",
        username="your.email@gmail.com",
        password="your_app_password",
        connection_idle_timeout=300.0,  # 5 minutes (default)
    )
    tools = mail_toolkit.get_tools()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        model=model,
        system_message=BaseMessage.make_assistant_message(
            role_name="Email Assistant",
            content="You are an email assistant. "
            "Help users with their emails.",
        ),
        tools=tools,
    )

    # Fetch emails
    logger.info("Fetching recent emails...")
    response = agent.step(
        BaseMessage.make_user_message(
            role_name="User", content="Get my 2 most recent emails"
        )
    )
    logger.info(f"Assistant: {response.msgs[0].content}\n")

    # Send email
    logger.info("Sending test email...")
    response = agent.step(
        BaseMessage.make_user_message(
            role_name="User",
            content="""Send an email to yourself with
            subject 'Test' and body 'Hello from CAMEL'""",
        )
    )
    logger.info(f"Assistant: {response.msgs[0].content}")

    # Connections will be auto-closed after idle timeout or when
    # mail_toolkit is destroyed
    mail_toolkit.close()  # Explicit cleanup (optional)


def main_with_context_manager() -> None:
    r"""Example using context manager for explicit cleanup."""

    # Example 2: Using context manager (recommended for long-running tasks)
    # Connections are guaranteed to close when exiting the context
    with IMAPMailToolkit(
        imap_server="imap.gmail.com",
        smtp_server="smtp.gmail.com",
        username="your.email@gmail.com",
        password="your_app_password",
    ) as mail_toolkit:
        tools = mail_toolkit.get_tools()

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )

        agent = ChatAgent(
            model=model,
            system_message=BaseMessage.make_assistant_message(
                role_name="Email Assistant",
                content="You are an email assistant.",
            ),
            tools=tools,
        )

        # Use the agent
        response = agent.step(
            BaseMessage.make_user_message(
                role_name="User", content="Get my recent emails"
            )
        )
        logger.info(f"Assistant: {response.msgs[0].content}")

    # Connections automatically closed here


if __name__ == "__main__":
    main()

"""
==============================================================
Fetching recent emails...
Assistant: Here are your two most recent emails (newest first):

1) From: "Example Brand" <news@example-brand.com>
   ID: 2620
   Date: Tue, 22 Nov 2024 07:07:16 -0600
   Subject: Get an exclusive experience in Dubai
   Size: 87,767 bytes
   Snippet: "WELCOME TO THE FAMILY HOUSE - A truly
   interactive experience... Join raffle on app to
   win an exclusive opportunity for you and 10 friends..."

2) From: "Service Provider" <noreply@service-provider.com>
   ID: 2619
   Date: Mon, 21 Nov 2024 03:34:39 -0800
   Subject: Updates to Terms of Service
   Size: 19,175 bytes
   Snippet: "On December 21, 2024, we're making some changes to
    our Terms of Service... You can review the new terms here..."

Would you like me to open/read either message in full, reply,
archive/move, or delete one of them? If so, tell me which
email (by number or ID) and the action.

Sending test email...
Assistant: Do you mean send it to your email (user@example.com)?
 If yes, I'll send an email with:

Subject: Test
Body: Hello from CAMEL

Any CC/BCC or HTML formatting needed?
===============================================================================
"""
