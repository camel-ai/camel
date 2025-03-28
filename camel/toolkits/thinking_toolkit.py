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
    r"""A toolkit for recording thoughts during reasoning processes.

    Attributes:
        thoughts (List[str]): A list to store the recorded thoughts.
    """

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
        self.thoughts: List[str] = []

    def think(self, thought: str) -> str:
        r"""Use the tool to think about something.
        It will not obtain new information or change the database, but just
        append the thought to the log. Use it when complex reasoning or some
        cache memory is needed.

        Args:
            thought (str): A thought to think about.

        Returns:
            str: The full log of thoughts including the new thought.
        """
        try:
            logger.debug(f"Thought: {thought}")
            self.thoughts.append(thought)

            thoughts = "\n".join([f"- {t}" for t in self.thoughts])
            return f"Thoughts:\n{thoughts}"

        except Exception as e:
            error_msg = f"Error recording thought: {e}"
            logger.error(error_msg)
            return error_msg

    def get_tools(self) -> List[FunctionTool]:
        r"""Get all tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of tools.
        """
        return [FunctionTool(self.think)]
