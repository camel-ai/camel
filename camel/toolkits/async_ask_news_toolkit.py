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
from typing import List, Literal, Optional, Tuple, Union
from warnings import warn

from camel.toolkits.base import BaseToolkit
from camel.toolkits.openai_function import OpenAIFunction


class AsyncAskNewsToolkit(BaseToolkit):
    r"""A class representing a toolkit for interacting with the AskNews API
    asynchronously.

    This class provides methods for fetching news, stories, and other content
    based on user queries using the AskNews API.
    """

    def __init__(self, scopes: Optional[List[str]] = None):
        r"""Initialize the AsyncAskNewsToolkit with API clients.

        Args:
            scopes (Optional[List[str]]): A list of API scopes to specify which
                functionalities the client should access.
                (default: :list:`["chat", "news", "stories"]`)

        The API keys and credentials are retrieved from environment variables.
        """
        from asknews_sdk import AsyncAskNewsSDK  # type: ignore[import]

        if scopes is None:
            scopes = ["chat", "news", "stories", "analytics"]
        client_id = os.environ.get("ASKNEWS_CLIENT_ID")
        client_secret = os.environ.get("ASKNEWS_CLIENT_SECRET")
        if not client_id or not client_secret:
            warn(
                "`client_id` or `client_secret` not found in environment "
                + "variables. Get `client_id & client_secret` here: "
                + "`https://docs.asknews.app/`."
            )
        self.asknews_client = AsyncAskNewsSDK(
            client_id,
            client_secret,
            scopes=scopes,
        )

    def _process_response(self, response, return_type: str):
        r"""Process the response based on the specified return type.

        This helper method processes the API response and returns the content
        in the specified format, which could be a string, a dictionary, or
        both.

        Args:
            response: The response object returned by the API call.
            return_type (str): Specifies the format of the return value. It
            can be "string" to return the response as a string, "dicts" to
            return it as a dictionary, or "both" to return both formats as a
            tuple.

        Returns:
            Union[str, dict, Tuple[str, dict]]: The processed response,
            formatted according to the return_type argument. If "string",
            returns the response as a string. If "dicts", returns the response
            as a dictionary. If "both", returns a tuple containing both
            formats.

        Raises:
            ValueError: If the return_type provided is invalid.
        """
        if return_type == "string":
            return response.as_string
        elif return_type == "dicts":
            return response.as_dicts
        elif return_type == "both":
            return (response.as_string, response.as_dicts)
        else:
            raise ValueError(f"Invalid return_type: {return_type}")

    async def get_news(
        self,
        query: str,
        n_articles: int = 10,
        return_type: Literal["string", "dicts", "both"] = "string",
        method: Literal["nl", "kw"] = "kw",
    ) -> Union[str, dict, Tuple[str, dict]]:
        r"""Fetch news or stories based on a user query.

        Args:
            query (str): The search query for fetching relevant news or
            stories.
            n_articles (int): Number of articles to include in the response.
                (default: :obj:`10`)
            return_type (Literal["string", "dicts", "both"]): The format of the
                return value. (default: :obj:`"string"`)
            method (Literal["nl", "kw"]): The search method, either "nl" for
                natural language or "kw" for keyword search. (default:
                :obj:`"kw"`)

        Returns:
            Union[str, dict, Tuple[str, dict]]: A string, dictionary, or both
            containing the news or story content, or an error message if the
            process fails.
        """
        try:
            response = await self.asknews_client.news.search_news(
                query=query,
                n_articles=n_articles,
                return_type=return_type,
                method=method,
            )

            return self._process_response(response, return_type)

        except Exception as e:
            raise Exception(
                f"An error occurred while fetching news for '{query}': {e!s}."
            )

    async def search_reddit(
        self,
        keywords: list,
        n_threads: int = 5,
        return_type: Literal["string", "dicts", "both"] = "string",
        method: Literal["nl", "kw"] = "kw",
    ) -> Union[str, dict, Tuple[str, dict]]:
        r"""Search Reddit based on the provided keywords.

        Args:
            keywords (list): The keywords to search for on Reddit.
            n_threads (int): Number of Reddit threads to summarize and return.
                (default: :obj:`5`)
            return_type (Literal["string", "dicts", "both"]): The format of the
                return value. (default: :obj:`"string"`)
            method (Literal["nl", "kw"]): The search method, either "nl" for
            natural language or "kw" for keyword search. (default:
            :obj:`"kw"`)

        Returns:
            Union[str, dict, Tuple[str, dict]]: The Reddit search results as a
            string, dictionary, or both.

        Raises:
            Exception: If there is an error while searching Reddit.
        """
        try:
            response = await self.asknews_client.news.search_reddit(
                keywords=keywords, n_threads=n_threads, method=method
            )

            return self._process_response(response, return_type)

        except Exception as e:
            raise Exception(
                f"An error occurred while searching Reddit: {e!s}."
            )

    async def get_stories(
        self,
        categories: list,
        continent: str,
        sort_by: str = "coverage",
        reddit: int = 3,
        expand_updates: bool = True,
        max_updates: int = 2,
        max_articles: int = 10,
    ) -> dict:
        r"""Fetch stories based on the provided parameters.

        Args:
            categories (list): The categories to filter stories by.
            continent (str): The continent to filter stories by.
            sort_by (str): The field to sort the stories by.
            (default: :obj:`"coverage"`)
            reddit (int): Number of Reddit threads to include.
            (default: :obj:`3`)
            expand_updates (bool): Whether to include detailed updates.
            (default: :obj:`True`)
            max_updates (int): Maximum number of recent updates per story.
            (default: :obj:`2`)
            max_articles (int): Maximum number of articles associated with
            each update. (default: :obj:`10`)

        Returns:
            dict: A dictionary containing the stories and their associated
             data.

        Raises:
            Exception: If there is an error while fetching the stories.
        """
        try:
            response = await self.asknews_client.stories.search_stories(
                categories=categories,
                continent=continent,
                sort_by=sort_by,
                reddit=reddit,
                expand_updates=expand_updates,
                max_updates=max_updates,
                max_articles=max_articles,
            )

            # Collect only the headline and story content from the updates
            stories_data = {
                "stories": [
                    {
                        "headline": story.updates[0].headline,
                        "updates": [
                            {
                                "headline": update.headline,
                                "story": update.story,
                            }
                            for update in story.updates[:max_updates]
                        ],
                    }
                    for story in response.stories
                ]
            }

            return stories_data

        except Exception as e:
            raise Exception(
                f"An error occurred while fetching stories: {e!s}."
            )

    async def finance_query(
        self,
        asset: str,
        metric: str,
        date_from: str,
        date_to: str,
        return_type: Literal["list", "string"] = "string",
    ) -> Union[list, str]:
        r"""Fetch asset sentiment data for a given asset, metric, and date
        range.

        Args:
            asset (str): The asset for which to fetch sentiment data.
            metric (str): The sentiment metric to analyze.
            date_from (str): The start date and time for the data in ISO 8601
            format.
            date_to (str): The end date and time for the data in ISO 8601
            format.
            return_type (Literal["list", "string"]): The format of the return
            value. (default: :obj:`"string"`)

        Returns:
            Union[list, str]: A list of dictionaries containing the datetime
            and value or a string describing all datetime and value pairs for
            providing quantified time-series data for news sentiment on topics
            of interest.

        Raises:
            Exception: If there is an error while fetching the sentiment data.
        """
        try:
            response = await self.asknews_client.analytics.get_asset_sentiment(
                asset=asset,
                metric=metric,
                date_from=date_from,
                date_to=date_to,
            )

            time_series_data = response.data.timeseries

            if return_type == "list":
                return time_series_data
            elif return_type == "string":
                header = (
                    f"This is the sentiment analysis for '{asset}' based "
                    + f"on the '{metric}' metric from {date_from} to {date_to}"
                    + ". The values reflect the aggregated sentiment from news"
                    + " sources for each given time period.\n"
                )
                descriptive_text = "\n".join(
                    [
                        f"On {entry.datetime}, the sentiment value was "
                        f"{entry.value}."
                        for entry in time_series_data
                    ]
                )
                return header + descriptive_text

        except Exception as e:
            raise Exception(
                f"An error occurred while fetching asset sentiment "
                f"data: {e!s}."
            )

    async def chat_query(
        self, query: str, model: str = "meta-llama/Meta-Llama-3-70B-Instruct"
    ) -> str:
        r"""Send a chat query to the API and retrieve the response.

        Args:
            query (str): The content of the user's message.
            model (str): The model to use for generating the chat response.
            (default: :obj:`"meta-llama/Meta-Llama-3-70B-Instruct"`)

        Returns:
            str: The content of the response message.

        Raises:
            Exception: If there is an error while processing the chat query.
        """
        try:
            response = await self.asknews_client.chat.get_chat_completions(
                model=model,
                messages=[{"role": "user", "content": query}],
                stream=False,
            )

            # Return the content of the first choice's message
            return response.choices[0].message.content

        except Exception as e:
            raise Exception(
                f"An error occurred while processing the chat query: {e!s}."
            )

    async def get_web_search(
        self,
        queries: List[str],
        return_type: Literal["string", "dicts", "both"] = "string",
    ) -> Union[str, dict, Tuple[str, dict]]:
        r"""Perform a live web search based on the given queries.

        Args:
            queries (List[str]): A list of search queries.
            return_type (Literal["string", "dicts", "both"]): The format of the
                return value. (default: :obj:`"string"`)

        Returns:
            Union[str, dict, Tuple[str, dict]]: A string, dictionary, or both
            containing the search results, or an error message if the process
            fails.
        """
        try:
            response = await self.asknews_client.chat.live_web_search(
                queries=queries
            )

            if return_type == "string":
                search_content = response.as_string
            elif return_type == "dicts":
                search_content = response.as_dicts
            elif return_type == "both":
                search_content = (response.as_string, response.as_dicts)

            return search_content

        except Exception as e:
            raise Exception(
                "An error occurred while performing the web search for "
                + f"'{queries}': {e!s}."
            )

    def get_tools(self) -> List[OpenAIFunction]:
        r"""Returns a list of OpenAIFunction objects representing the functions
          in the toolkit.

        Returns:
            List[OpenAIFunction]: A list of OpenAIFunction objects representing
             the functions in the toolkit.
        """
        return [
            OpenAIFunction(self.get_news),
            OpenAIFunction(self.search_reddit),
            OpenAIFunction(self.get_stories),
            OpenAIFunction(self.finance_query),
            OpenAIFunction(self.chat_query),
            OpenAIFunction(self.get_web_search),
        ]


ASYNC_ASKNEWS_FUNCS: List[OpenAIFunction] = AsyncAskNewsToolkit().get_tools()
