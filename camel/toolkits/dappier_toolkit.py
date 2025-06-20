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
import os
from typing import Dict, List, Literal, Optional, Union

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, api_keys_required, dependencies_required


@MCPServer()
class DappierToolkit(BaseToolkit):
    r"""A class representing a toolkit for interacting with the Dappier API.

    This class provides methods for searching real time data and fetching
    ai recommendations across key verticals like News, Finance, Stock Market,
    Sports, Weather and more.
    """

    @dependencies_required("dappier")
    @api_keys_required(
        [
            (None, "DAPPIER_API_KEY"),
        ]
    )
    def __init__(self, timeout: Optional[float] = None):
        r"""Initialize the DappierTookit with API clients.The API keys and
        credentials are retrieved from environment variables.
        """
        super().__init__(timeout=timeout)
        from dappier import Dappier

        dappier_api_key = os.environ.get("DAPPIER_API_KEY")

        self.dappier_client = Dappier(dappier_api_key)

    def search_real_time_data(
        self, query: str, ai_model_id: str = "am_01j06ytn18ejftedz6dyhz2b15"
    ) -> str:
        r"""Search real-time data using an AI model.

        This function accesses real-time information using the specified
        AI model based on the given query. Depending on the AI model ID,
        the data retrieved can vary between general web search results or
        financial news and stock prices.

        Supported AI Models:
            - `am_01j06ytn18ejftedz6dyhz2b15`:
            Access real-time Google web search results, including the latest
            news, weather updates, travel details, deals, and more.
            - `am_01j749h8pbf7ns8r1bq9s2evrh`:
            Access real-time financial news, stock prices, and trades from
            polygon.io, with AI-powered insights and up-to-the-minute updates.

        Args:
            query (str): The user-provided query. Examples include:
                - "How is the weather today in Austin, TX?"
                - "What is the latest news for Meta?"
                - "What is the stock price for AAPL?"
            ai_model_id (str, optional): The AI model ID to use for the query.
                The AI model ID always starts with the prefix "am_".
                (default: `am_01j06ytn18ejftedz6dyhz2b15`)

        Returns:
            str: The search result corresponding to the provided query and
                AI model ID. This may include real time search data,
                depending on the selected AI model.

        Note:
            Multiple AI model IDs are available, which can be found at:
            https://marketplace.dappier.com/marketplace
        """
        try:
            response = self.dappier_client.search_real_time_data(
                query=query, ai_model_id=ai_model_id
            )

            if response is None:
                return "An unknown error occurred"

            return response.message

        except Exception as e:
            return f"An unexpected error occurred: {e}"

    def get_ai_recommendations(
        self,
        query: str,
        data_model_id: str = "dm_01j0pb465keqmatq9k83dthx34",
        similarity_top_k: int = 9,
        ref: Optional[str] = None,
        num_articles_ref: int = 0,
        search_algorithm: Literal[
            "most_recent", "semantic", "most_recent_semantic", "trending"
        ] = "most_recent",
    ) -> Union[List[Dict[str, str]], Dict[str, str]]:
        r"""Retrieve AI-powered recommendations based on the provided query
        and data model.

        This function fetches real-time AI-generated recommendations using the
        specified data model and search algorithm. The results include
        personalized content based on the query and, optionally, relevance
        to a specific reference domain.

        Supported Data Models:
            - `dm_01j0pb465keqmatq9k83dthx34`:
            Real-time news, updates, and personalized content from top sports
            sources such as Sportsnaut, Forever Blueshirts, Minnesota Sports
            Fan, LAFB Network, Bounding Into Sports, and Ringside Intel.
            - `dm_01j0q82s4bfjmsqkhs3ywm3x6y`:
            Real-time updates, analysis, and personalized content from top
            sources like The Mix, Snipdaily, Nerdable, and Familyproof.

        Args:
            query (str): The user query for retrieving recommendations.
            data_model_id (str, optional): The data model ID to use for
                recommendations. Data model IDs always start with the prefix
                "dm_". (default: :obj:`dm_01j0pb465keqmatq9k83dthx34`)
            similarity_top_k (int, optional): The number of top documents to
                retrieve based on similarity. (default: :obj:`9`)
            ref (Optional[str], optional): The site domain where AI
                recommendations should be displayed. (default: :obj:`None`)
            num_articles_ref (int, optional): The minimum number of articles
                to return from the specified reference domain (`ref`). The
                remaining articles will come from other sites in the RAG
                model. (default: :obj:`0`)
            search_algorithm (Literal[
                "most_recent",
                "semantic",
                "most_recent_semantic",
                "trending",
                ], optional): The search algorithm to use for retrieving
                articles. (default: :obj:`most_recent`)

        Returns:
            List[Dict[str, str]]: A list of recommended articles or content
                based on the specified parameters, query, and data model.

        Note:
            Multiple data model IDs are available and can be found at:
            https://marketplace.dappier.com/marketplace
        """
        try:
            response = self.dappier_client.get_ai_recommendations(
                query=query,
                data_model_id=data_model_id,
                similarity_top_k=similarity_top_k,
                ref=ref,
                num_articles_ref=num_articles_ref,
                search_algorithm=search_algorithm,
            )

            if response is None or response.status != "success":
                return {"error": "An unknown error occurred."}

            # Collect only relevant information from the response.
            results = [
                {
                    "author": result.author,
                    "image_url": result.image_url,
                    "pubdate": result.pubdate,
                    "source_url": result.source_url,
                    "summary": result.summary,
                    "title": result.title,
                }
                for result in (
                    getattr(response.response, "results", None) or []
                )
            ]

            return results

        except Exception as e:
            return {"error": f"An unexpected error occurred: {e!s}"}

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.search_real_time_data),
            FunctionTool(self.get_ai_recommendations),
        ]
