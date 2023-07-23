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
from typing import Any, Dict

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
            from serpapi import GoogleSearch
        except ImportError:
            raise ValueError("Could not import SerpAPI package"
                             "Please use `pip install google-search-results`")

        self.engine = GoogleSearch
        self.params: dict = {
            "engine": "google",
            "google_domain": "google.com",
            "gl": "us",
            "hl": "en",
        }

        # TODO to replace the LangChain wrapper with self-implemented one
        # Define LangHChain-implemented agent which can access Wiki
        SAK = os.getenv('SERPAPI_API_KEY')
        if not SAK:
            raise ValueError(
                "No SerpAPI key detected. "
                "Please specify one in environment variable 'SERPAPI_API_KEY'")
        self.serpapi_api_key = SAK

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
        query: str,
        **kwargs: Any,
    ) -> str:
        r"""Do the search operation

        Args:
            query (str): The query to be searched
            **kwargs (Any): Any extra query arguments passed to the
            search wrapper

        Returns:
            str: the result of this search
        """
        res = self.get_results(query)
        return self.process_result(res)

    def get_results(self, query: str) -> dict:
        r"""Get search result using the Google search engine.

        Args:
            query (str): The query to be searched
        
        Returns:
            dict: search result in dictionary to be processed
        """
        search_params = self.get_params(query)

        res = self.engine(search_params)
        res = res.get_dict()

        return res

    def get_params(self, query: str) -> Dict[str, str]:
        r"""Format the parameter dictionary to be passed to SerpAPI

        Args:
            query (str): The query to be searched
        
        Returns:
            dict: parameters for using SerpAPI
        """
        search_params = {
            "api_key": self.serpapi_api_key,
            "q": query,
        }
        params = {**self.params, **search_params}
        return params

    @staticmethod
    def process_result(res: dict) -> str:
        r"""Post-process the search results in dictionary to str

        Args:
            res (dict): the result dictionary
        
        Returns:
            str: search result in string format
        """
        if "error" in res.keys():
            raise ValueError(f"Got error from SerpAPI: {res['error']}")

        if "answer_box" in res.keys() and type(res["answer_box"]) == list:
            res["answer_box"] = res["answer_box"][0]

        if ("answer_box" in res.keys()
                and "answer" in res["answer_box"].keys()):
            result = res["answer_box"]["answer"]

        elif ("answer_box" in res.keys()
              and "snippet" in res["answer_box"].keys()):
            result = res["answer_box"]["snippet"]

        elif ("answer_box" in res.keys()
              and "snippet_highlighted_words" in res["answer_box"].keys()):
            result = res["answer_box"]["snippet_highlighted_words"][0]

        elif ("sports_results" in res.keys()
              and "game_spotlight" in res["sports_results"].keys()):
            result = res["sports_results"]["game_spotlight"]

        elif ("shopping_results" in res.keys()
              and "title" in res["shopping_results"][0].keys()):
            result = res["shopping_results"][:3]

        elif ("knowledge_graph" in res.keys()
              and "description" in res["knowledge_graph"].keys()):
            result = res["knowledge_graph"]["description"]

        elif "snippet" in res["organic_results"][0].keys():
            result = res["organic_results"][0]["snippet"]

        elif "link" in res["organic_results"][0].keys():
            result = res["organic_results"][0]["link"]

        else:
            result = "No good search result found"

        return result
