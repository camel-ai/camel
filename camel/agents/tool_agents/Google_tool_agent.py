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

        # Obtain OpenAI API Key from the environment
        # OAK = os.getenv('OPENAI_API_KEY')
        SAK = os.getenv('SERPAPI_KEY')

        # Define LangHChain-implemented agent which can access Wiki
        search = SerpAPIWrapper(serpapi_api_key=SAK)

        self.name = name
        self.description = f"""The `{self.name}` is a tool agent that can perform Google search when external information is needed.
        Here are some python code examples of what you can do with this agent:
        # Ask commonsense information:
        ans = {self.name}.step("What is the name of the 45th President of the United States?")

        # Ask real-time information like weather
        ans = {self.name}.step("What is the current weather of London?")
        """

    def reset(self) -> None:
        pass

    def step(
        self,
        question,
        **kwargs: Any,
    ) -> Any:
        return self.search.run(question, **kwargs)
