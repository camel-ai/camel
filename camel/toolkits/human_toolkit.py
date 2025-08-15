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

import logging
from typing import List

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

logger = logging.getLogger(__name__)


class HumanToolkit(BaseToolkit):
    r"""A class representing a toolkit for human interaction.

    Note:
        This toolkit should be called to send a tidy message to the user to
        keep them informed.
    """

    def ask_human_via_console(self, question: str) -> str:
        r"""Use this tool to ask a question to the user when you are stuck,
        need clarification, or require a decision to be made. This is a
        two-way communication channel that will wait for the user's response.
        You should use it to:
        - Clarify ambiguous instructions or requirements.
        - Request missing information that you cannot find (e.g., login
        credentials, file paths).
        - Ask for a decision when there are multiple viable options.
        - Seek help when you encounter an error you cannot resolve on your own.

        Args:
            question (str): The question to ask the user.

        Returns:
            str: The user's response to the question.
        """
        print(f"Question: {question}")
        logger.info(f"Question: {question}")
        reply = input("Your reply: ")
        logger.info(f"User reply: {reply}")
        return reply

    def send_message_to_user(self, message: str) -> str:
        r"""Use this tool to send a tidy message to the user in one short
        sentence.

        This one-way tool keeps the user informed about your progress,
        decisions, or actions. It does not require a response.
        You should use it to:
        - Announce what you are about to do (e.g., "I will now search for
          papers on GUI Agents.").
        - Report the result of an action (e.g., "I have found 15 relevant
          papers.").
        - State a decision (e.g., "I will now analyze the top 10 papers.").
        - Give a status update during a long-running task.

        Args:
            message (str): The tidy and informative message for the user.

        Returns:
            str: Confirmation that the message was successfully sent.
        """
        print(f"\nAgent Message:\n{message}")
        logger.info(f"\nAgent Message:\n{message}")
        return f"Message successfully sent to user: '{message}'"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.ask_human_via_console),
            FunctionTool(self.send_message_to_user),
        ]
