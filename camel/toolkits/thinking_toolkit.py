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

from typing import List, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit

logger = get_logger(__name__)


class ThinkingToolkit(BaseToolkit):
    r"""A toolkit for recording thoughts during reasoning processes."""

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        r"""Initialize the ThinkingToolkit.

        Args:
            timeout (Optional[float]): The timeout for the toolkit.
                (default: :obj: `None`)
        """
        super().__init__(timeout=timeout)
        self.plans: List[str] = []
        self.thoughts: List[str] = []

    def plan(self, plan: str) -> str:
        r"""Use the tool to create a plan or strategy.
        This tool is for outlining the approach or steps to be taken before
        starting the actual thinking process. It helps in organizing the
        thought process beforehand.

        Args:
            plan (str): A forward-looking plan or strategy.

        Returns:
            str: The recorded plan.
        """
        try:
            logger.debug(f"Plan: {plan}")
            self.plans.append(plan)
            return f"Plan: {plan}"

        except Exception as e:
            error_msg = f"Error recording plan: {e}"
            logger.error(error_msg)
            return error_msg

    def think(self, thought: str) -> str:
        r"""Use the tool to think about something.
        It will not obtain new information or change the database, but just
        append the thought to the log. Use it when executing the planned
        steps and reasoning through the process.

        Args:
            thought (str): A thought to think about.

        Returns:
            str: The recorded thought.
        """
        try:
            logger.debug(f"Thought: {thought}")
            if not self.plans:
                return (
                    "Consider creating a plan before thinking "
                    "through the process."
                )
            self.thoughts.append(thought)
            return f"Thought: {thought}"

        except Exception as e:
            error_msg = f"Error recording thought: {e}"
            logger.error(error_msg)
            return error_msg

    def reflect(self, reflection: str) -> str:
        r"""Use the tool to reflect on previous thoughts and actions.
        This tool is for evaluating the thinking process after execution,
        analyzing what worked, what didn't, and what was learned.

        Args:
            reflection (str): An insight or analysis based on the executed plan
                and recorded thoughts.

        Returns:
            str: The recorded reflection.
        """
        try:
            logger.debug(f"Reflection: {reflection}")
            if not self.thoughts:
                return (
                    "No thoughts to reflect upon yet. Consider thinking "
                    "through the plan first."
                )
            return f"Reflection: {reflection}"

        except Exception as e:
            error_msg = f"Error recording reflection: {e}"
            logger.error(error_msg)
            return error_msg

    def get_tools(self) -> List[FunctionTool]:
        r"""Get all tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of tools.
        """
        return [
            FunctionTool(self.plan),
            FunctionTool(self.think),
            FunctionTool(self.reflect),
        ]
