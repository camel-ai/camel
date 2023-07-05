# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import os
from typing import Any

from camel.agents.tool_agents import BaseToolAgent


class GoogleToolAgent(BaseToolAgent):
    r"""Tool agent for searching contents using Goole search engine.

    Args:
        name (str): The name of the agent.
    """

    def __init__(
        self,
        name: str,
    ) -> None:
        try:
            from langchain.utilities import SerpAPIWrapper
        except ImportError:
            raise ValueError("Could not import langchain agents"
                             "Please use pip install langchain")

        # TODO to replace the LangChain wrapper with self-implemented one
        # Define LangHChain-implemented agent which can access Wiki
        SAK = os.getenv('SERPAPI_KEY')
        self.search = SerpAPIWrapper(serpapi_api_key=SAK)

        self.name = name

        # flake8: noqa :E501
        self.description = """GoogleSearch[<keyword>]
- input <keyword>: the information to be searched using Google search engine
- Keep a rule in mind: if the current search does not return valid page, try to make the search item more general and shorter, instead of making it finer
- Example usage: GoogleSearch[What is the current weather of London?]
    - by which we can obtain the weather information in London through Google
"""

    def step(
        self,
        keyword: str,
        **kwargs: Any,
    ) -> str:
        r"""Do the search operation

        Args:
            keyword (str): The keyword to be searched
            **kwargs (Any): Any extra keyword arguments passed to the
            search wrapper

        Returns:
            str: the result of this search
        """
        return self.search.run(keyword, **kwargs)
