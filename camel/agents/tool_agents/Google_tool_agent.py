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
from typing import Any, Optional

from camel.agents.tool_agents import BaseToolAgent


class GoogleToolAgent(BaseToolAgent):
    def __init__(
        self,
        name: str,
        *args: Any,
    ) -> None:
        try:
            from langchain.utilities import SerpAPIWrapper
        except ImportError:
            raise ValueError("Could not import langchain agents"
                             "Please use pip install langchain")

        SAK = os.getenv('SERPAPI_KEY')

        # TODO to replace the LangChain wrapper with self-implemented one
        # Define LangHChain-implemented agent which can access Wiki
        self.search = SerpAPIWrapper(serpapi_api_key=SAK)

        self.name = name
        self.description = \
f"""
GoogleSearch[<keyword>]
- input <keyword>: the information to be searched using Google search engine
- Keep a rule in mind: if the current search does not return valid page, try to make the search item more general and shorter, instead of making it finer
- Example usage: GoogleSearch[What is the current weather of London?]
    - by which we can obtain the weather information in London through Google
"""

    def reset(self) -> None:
        pass

    def step(
        self,
        question,
        **kwargs: Any,
    ) -> Any:
        return self.search.run(question, **kwargs)
