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
# ============================================================================


from typing import List

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit

logger = get_logger(__name__)


class ThinkingToolkit(BaseToolkit):
    r"""A toolkit for recording and managing thoughts during reasoning
        processes.

    This toolkit provides functionality for recording thoughts and maintaining
    a thought log, useful for complex reasoning tasks or when a memory cache
    is needed. It does not modify any external state or fetch new
    information.

    Attributes:
        thoughts (List[str]): A list storing the recorded thoughts.
    """

    def __init__(self):
        r"""Initialize the ThinkingToolkit with an empty thought log."""
        self.thoughts: List[str] = []

    def think(self, thought: str) -> str:
        r"""Record a new thought and return the complete thought log.

        This method appends a new thought to the thought log and returns a
        formatted string containing all recorded thoughts. It's useful for
        complex reasoning tasks or when maintaining a chain of thoughts is
        needed.

        Args:
            thought (str): The new thought to be recorded.

        Returns:
            str: A formatted string containing all recorded thoughts, including
                the new one.
        """
        try:
            logger.debug(f"Recording thought: {thought}")
            self.thoughts.append(thought)

            # Format all thoughts into a readable string
            formatted_thoughts = "\n".join(f"- {t}" for t in self.thoughts)
            return f"Thoughts:\n{formatted_thoughts}"

        except Exception as e:
            error_msg = f"Error recording thought: {e}"
            logger.error(error_msg)
            return error_msg

    def clear_thoughts(self) -> str:
        r"""Clear all recorded thoughts from the thought log.

        Returns:
            str: A confirmation message indicating the thoughts were cleared.
        """
        try:
            self.thoughts.clear()
            return "All thoughts have been cleared."
        except Exception as e:
            error_msg = f"Error clearing thoughts: {e}"
            logger.error(error_msg)
            return error_msg

    def get_thought_history(self) -> str:
        r"""Retrieve the complete history of recorded thoughts.

        Returns:
            str: A formatted string containing all recorded thoughts.
        """
        if not self.thoughts:
            return "No thoughts recorded yet."

        formatted_thoughts = "\n".join(f"- {t}" for t in self.thoughts)
        return f"Thought History:\n{formatted_thoughts}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.think),
            FunctionTool(self.clear_thoughts),
            FunctionTool(self.get_thought_history),
        ]
