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
from typing import List, Literal

from asknews_sdk import AskNewsSDK

from camel.toolkits.openai_function import OpenAIFunction


class AskNewsToolkit:
    r"""A class representing a toolkit for interacting with the AskNews API.

    This class provides methods for fetching news, stories, and other content
    based on user queries using the AskNews API.
    """

    def __init__(self):
        r"""Initialize the AskNewsToolkit with API clients.

        The API keys and credentials are retrieved from environment variables.
        """
        # Initialize the AskNews client using API keys and credentials from
        # environment variables.
        self.asknews_client = AskNewsSDK(
            client_id=os.environ.get("ASKNEWS_CLIENT_ID"),
            client_secret=os.environ.get("ASKNEWS_CLIENT_SECRET"),
            scopes=["chat", "news", "stories"],
        )

    def get_news(
        self,
        query: str,
        n_articles: int = 10,
        return_type: Literal["string", "dict"] = "string",
        method: Literal["nl", "kw"] = "nl",
    ) -> str:
        r"""Fetch news or stories based on a user query.

        Args:
            query (str): The search query for fetching relevant news or
                stories.
            n_articles (int): Number of articles to include in the response.
                Default is 10.
            return_type (Literal["string", "dict"]): The format of the return
                value. Default is "string".
            method (Literal["nl", "kw"]): The search method, either "nl" for
                natural language or "kw" for keyword search. Default is "nl".

        Returns:
            str: A string containing the news or story content, or an error
                message if the process fails.
        """
        try:
            response = self.asknews_client.news.search_news(
                query=query,
                n_articles=n_articles,
                return_type=return_type,
                method=method,
            )

            if return_type == "string":
                news_content = response.as_string
            else:
                news_content = response.as_dict

            return news_content

        except Exception as e:
            error_message = (
                f"An error occurred while fetching news for '{query}': {e!s}."
            )
            return error_message

    def get_tools(self) -> List[OpenAIFunction]:
        r"""Returns a list of OpenAIFunction objects representing the functions
          in the toolkit.

        Returns:
            List[OpenAIFunction]: A list of OpenAIFunction objects representing
             the functions in the toolkit.
        """
        return [
            OpenAIFunction(self.get_news),
        ]


ASKNEWS_FUNCS: List[OpenAIFunction] = AskNewsToolkit().get_tools()

if __name__ == '__main__':
    # Example usage:
    ask = AskNewsToolkit()
    news = ask.get_news("tell me a story")
    print(news)
