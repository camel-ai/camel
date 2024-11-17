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
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Union

import requests

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import api_keys_required, dependencies_required


class SearchToolkit(BaseToolkit):
    r"""A class representing a toolkit for web search.

    This class provides methods for searching information on the web using
    search engines like Google, DuckDuckGo, Wikipedia and Wolfram Alpha.
    """

    @dependencies_required("wikipedia")
    def search_wiki(self, entity: str) -> str:
        r"""Search the entity in WikiPedia and return the summary of the
            required page, containing factual information about
            the given entity.

        Args:
            entity (str): The entity to be searched.

        Returns:
            str: The search result. If the page corresponding to the entity
                exists, return the summary of this entity in a string.
        """
        import wikipedia

        result: str

        try:
            result = wikipedia.summary(entity, sentences=5, auto_suggest=False)
        except wikipedia.exceptions.DisambiguationError as e:
            result = wikipedia.summary(
                e.options[0], sentences=5, auto_suggest=False
            )
        except wikipedia.exceptions.PageError:
            result = (
                "There is no page in Wikipedia corresponding to entity "
                f"{entity}, please specify another word to describe the"
                " entity to be searched."
            )
        except wikipedia.exceptions.WikipediaException as e:
            result = f"An exception occurred during the search: {e}"

        return result

    @dependencies_required("duckduckgo_search")
    def search_duckduckgo(
        self, query: str, source: str = "text", max_results: int = 5
    ) -> List[Dict[str, Any]]:
        r"""Use DuckDuckGo search engine to search information for
        the given query.

        This function queries the DuckDuckGo API for related topics to
        the given search term. The results are formatted into a list of
        dictionaries, each representing a search result.

        Args:
            query (str): The query to be searched.
            source (str): The type of information to query (e.g., "text",
                "images", "videos"). Defaults to "text".
            max_results (int): Max number of results, defaults to `5`.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each dictionary
                represents a search result.
        """
        from duckduckgo_search import DDGS
        from requests.exceptions import RequestException

        ddgs = DDGS()
        responses: List[Dict[str, Any]] = []

        if source == "text":
            try:
                results = ddgs.text(keywords=query, max_results=max_results)
            except RequestException as e:
                # Handle specific exceptions or general request exceptions
                responses.append({"error": f"duckduckgo search failed.{e}"})

            # Iterate over results found
            for i, result in enumerate(results, start=1):
                # Creating a response object with a similar structure
                response = {
                    "result_id": i,
                    "title": result["title"],
                    "description": result["body"],
                    "url": result["href"],
                }
                responses.append(response)

        elif source == "images":
            try:
                results = ddgs.images(keywords=query, max_results=max_results)
            except RequestException as e:
                # Handle specific exceptions or general request exceptions
                responses.append({"error": f"duckduckgo search failed.{e}"})

            # Iterate over results found
            for i, result in enumerate(results, start=1):
                # Creating a response object with a similar structure
                response = {
                    "result_id": i,
                    "title": result["title"],
                    "image": result["image"],
                    "url": result["url"],
                    "source": result["source"],
                }
                responses.append(response)

        elif source == "videos":
            try:
                results = ddgs.videos(keywords=query, max_results=max_results)
            except RequestException as e:
                # Handle specific exceptions or general request exceptions
                responses.append({"error": f"duckduckgo search failed.{e}"})

            # Iterate over results found
            for i, result in enumerate(results, start=1):
                # Creating a response object with a similar structure
                response = {
                    "result_id": i,
                    "title": result["title"],
                    "description": result["description"],
                    "embed_url": result["embed_url"],
                    "publisher": result["publisher"],
                    "duration": result["duration"],
                    "published": result["published"],
                }
                responses.append(response)

        # If no answer found, return an empty list
        return responses

    @api_keys_required("GOOGLE_API_KEY", "SEARCH_ENGINE_ID")
    def search_google(
        self, query: str, num_result_pages: int = 5
    ) -> List[Dict[str, Any]]:
        r"""Use Google search engine to search information for the given query.

        Args:
            query (str): The query to be searched.
            num_result_pages (int): The number of result pages to retrieve.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries where each dictionary
            represents a website.
                Each dictionary contains the following keys:
                - 'result_id': A number in order.
                - 'title': The title of the website.
                - 'description': A brief description of the website.
                - 'long_description': More detail of the website.
                - 'url': The URL of the website.

                Example:
                {
                    'result_id': 1,
                    'title': 'OpenAI',
                    'description': 'An organization focused on ensuring that
                    artificial general intelligence benefits all of humanity.',
                    'long_description': 'OpenAI is a non-profit artificial
                    intelligence research company. Our goal is to advance
                    digital intelligence in the way that is most likely to
                    benefit humanity as a whole',
                    'url': 'https://www.openai.com'
                }
            title, description, url of a website.
        """
        import requests

        # https://developers.google.com/custom-search/v1/overview
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        # https://cse.google.com/cse/all
        SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

        # Using the first page
        start_page_idx = 1
        # Different language may get different result
        search_language = "en"
        # How many pages to return
        num_result_pages = num_result_pages
        # Constructing the URL
        # Doc: https://developers.google.com/custom-search/v1/using_rest
        url = (
            f"https://www.googleapis.com/customsearch/v1?"
            f"key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&q={query}&start="
            f"{start_page_idx}&lr={search_language}&num={num_result_pages}"
        )

        responses = []
        # Fetch the results given the URL
        try:
            # Make the get
            result = requests.get(url)
            data = result.json()

            # Get the result items
            if "items" in data:
                search_items = data.get("items")

                # Iterate over 10 results found
                for i, search_item in enumerate(search_items, start=1):
                    # Check metatags are present
                    if "pagemap" not in search_item:
                        continue
                    if "metatags" not in search_item["pagemap"]:
                        continue
                    if (
                        "og:description"
                        in search_item["pagemap"]["metatags"][0]
                    ):
                        long_description = search_item["pagemap"]["metatags"][
                            0
                        ]["og:description"]
                    else:
                        long_description = "N/A"
                    # Get the page title
                    title = search_item.get("title")
                    # Page snippet
                    snippet = search_item.get("snippet")

                    # Extract the page url
                    link = search_item.get("link")
                    response = {
                        "result_id": i,
                        "title": title,
                        "description": snippet,
                        "long_description": long_description,
                        "url": link,
                    }
                    responses.append(response)
            else:
                responses.append({"error": "google search failed."})

        except requests.RequestException:
            # Handle specific exceptions or general request exceptions
            responses.append({"error": "google search failed."})
        # If no answer found, return an empty list
        return responses

    @dependencies_required("wolframalpha")
    def query_wolfram_alpha(
        self, query: str, is_detailed: bool = False
    ) -> Union[str, Dict[str, Any]]:
        r"""Queries Wolfram|Alpha and returns the result. Wolfram|Alpha is an
        answer engine developed by Wolfram Research. It is offered as an online
        service that answers factual queries by computing answers from
        externally sourced data.

        Args:
            query (str): The query to send to Wolfram Alpha.
            is_detailed (bool): Whether to include additional details
                including step by step information in the result.
                (default::obj:`False`)

        Returns:
            Union[str, Dict[str, Any]]: The result from Wolfram Alpha.
                Returns a string if `is_detailed` is False, otherwise returns
                a dictionary with detailed information.
        """
        import wolframalpha

        WOLFRAMALPHA_APP_ID = os.environ.get('WOLFRAMALPHA_APP_ID')
        if not WOLFRAMALPHA_APP_ID:
            raise ValueError(
                "`WOLFRAMALPHA_APP_ID` not found in environment "
                "variables. Get `WOLFRAMALPHA_APP_ID` here: "
                "`https://products.wolframalpha.com/api/`."
            )

        try:
            client = wolframalpha.Client(WOLFRAMALPHA_APP_ID)
            res = client.query(query)

        except Exception as e:
            return f"Wolfram Alpha wasn't able to answer it. Error: {e}"

        pased_result = self._parse_wolfram_result(res)

        if is_detailed:
            step_info = self._get_wolframalpha_step_by_step_solution(
                WOLFRAMALPHA_APP_ID, query
            )
            pased_result["steps"] = step_info
            return pased_result

        return pased_result["final_answer"]

    def _parse_wolfram_result(self, result) -> Dict[str, Any]:
        r"""Parses a Wolfram Alpha API result into a structured dictionary
        format.

        Args:
            result: The API result returned from a Wolfram Alpha
                query, structured with multiple pods, each containing specific
                information related to the query.

        Returns:
            dict: A structured dictionary with the original query and the
                final answer.
        """

        # Extract the original query
        query = result.get('@inputstring', '')

        # Initialize a dictionary to hold structured output
        output = {"query": query, "pod_info": [], "final_answer": None}

        # Loop through each pod to extract the details
        for pod in result.get('pod', []):
            # Handle the case where subpod might be a list
            subpod_data = pod.get('subpod', {})
            if isinstance(subpod_data, list):
                # If it's a list, get the first item for 'plaintext' and 'img'
                description, image_url = next(
                    (
                        (data['plaintext'], data['img'])
                        for data in subpod_data
                        if "plaintext" in data and "img" in data
                    ),
                    ("", ""),
                )
            else:
                # Otherwise, handle it as a dictionary
                description = subpod_data.get('plaintext', '')
                image_url = subpod_data.get('img', {}).get('@src', '')

            pod_info = {
                "title": pod.get('@title', ''),
                "description": description,
                "image_url": image_url,
            }

            # Add to steps list
            output["pod_info"].append(pod_info)

            # Get final answer
            if pod.get('@primary', False):
                output["final_answer"] = description

        return output

    def _get_wolframalpha_step_by_step_solution(
        self, app_id: str, query: str
    ) -> dict:
        r"""Retrieve a step-by-step solution from the Wolfram Alpha API for a
        given query.

        Args:
            app_id (str): Your Wolfram Alpha API application ID.
            query (str): The mathematical or computational query to solve.

        Returns:
            dict: The step-by-step solution response text from the Wolfram
                Alpha API.
        """
        # Define the base URL
        url = "https://api.wolframalpha.com/v2/query"

        # Set up the query parameters
        params = {
            'appid': app_id,
            'input': query,
            'podstate': ['Result__Step-by-step solution', 'Show all steps'],
            'format': 'plaintext',
        }

        # Send the request
        response = requests.get(url, params=params)
        root = ET.fromstring(response.text)

        # Extracting step-by-step steps, including 'SBSStep' and 'SBSHintStep'
        steps = []
        # Find all subpods within the 'Results' pod
        for subpod in root.findall(".//pod[@title='Results']//subpod"):
            # Check if the subpod has the desired stepbystepcontenttype
            content_type = subpod.find('stepbystepcontenttype')
            if content_type is not None and content_type.text in [
                'SBSStep',
                'SBSHintStep',
            ]:
                plaintext = subpod.find('plaintext')
                if plaintext is not None and plaintext.text:
                    step_text = plaintext.text.strip()
                    cleaned_step = step_text.replace(
                        'Hint: |', ''
                    ).strip()  # Remove 'Hint: |' if present
                    steps.append(cleaned_step)

        # Structuring the steps into a dictionary
        structured_steps = {}
        for i, step in enumerate(steps, start=1):
            structured_steps[f"step{i}"] = step

        return structured_steps

    def tavily_search(
        self, query: str, num_results: int = 5, **kwargs
    ) -> List[Dict[str, Any]]:
        r"""Use Tavily Search API to search information for the given query.

        Args:
            query (str): The query to be searched.
            num_results (int): The number of search results to retrieve
                (default is `5`).
            **kwargs: Additional optional parameters supported by Tavily's API:
                - search_depth (str): "basic" or "advanced" search depth.
                - topic (str): The search category, e.g., "general" or "news."
                - days (int): Time frame in days for news-related searches.
                - max_results (int): Max number of results to return
                  (overrides `num_results`).
                See https://docs.tavily.com/docs/python-sdk/tavily-search/
                api-reference for details.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing search
                results. Each dictionary contains:
                - 'result_id' (int): The result's index.
                - 'title' (str): The title of the result.
                - 'description' (str): A brief description of the result.
                - 'long_description' (str): Detailed information, if available.
                - 'url' (str): The URL of the result.
                - 'content' (str): Relevant content from the search result.
                - 'images' (list): A list of related images (if
                  `include_images` is True).
                - 'published_date' (str): Publication date for news topics
                  (if available).
        """
        from tavily import TavilyClient  # type: ignore[import-untyped]

        Tavily_API_KEY = os.getenv("TAVILY_API_KEY")
        if not Tavily_API_KEY:
            raise ValueError(
                "`TAVILY_API_KEY` not found in environment variables. "
                "Get `TAVILY_API_KEY` here: `https://www.tavily.com/api/`."
            )

        client = TavilyClient(Tavily_API_KEY)

        try:
            results = client.search(query, max_results=num_results, **kwargs)
            return results
        except Exception as e:
            return [{"error": f"An unexpected error occurred: {e!s}"}]

    def get_url_content(self, url: str) -> str:
        """Fetch the content of a URL using the r.jina.ai service.

        Args:
            url (str): The URL to fetch content from.

        Returns:
            str: The markdown content of the URL.
        """

        # Replace http with https and add https if not present
        if not url.startswith("https://"):
            url = "https://" + url.lstrip("https://").lstrip("http://")

        jina_url = f"https://r.jina.ai/{url}"
        headers = {}
        if os.environ.get('JINA_PROXY_URL'):
            headers['X-Proxy-Url'] = os.environ.get('JINA_PROXY_URL')

        auth_token = os.environ.get('JINA_AUTH_TOKEN')
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'
        try:
            response = requests.get(jina_url, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            return f"Error fetching URL content: {e!s}"

    def get_url_content_with_context(
        self,
        url: str,
        search_string: str,
        context_chars: int = 700,
        max_instances: int = 3,
    ) -> str:
        """Fetch the content of a URL and return context around all instances of a specific string.

        Args:
            url (str): The URL to fetch content from.
            search_string (str): The string to search for in the content.
            context_chars (int): Number of characters to return before and after each found string.
            max_instances (int): Maximum number of instances to return.

        Returns:
            str: The context around all found instances of the string, or an error message if not found.

        If there are no results, try again with a more likely search string. Start with a more likely string and only use a less likely string if the first one has too many results.
        """
        content = self.get_url_content(url)
        if content.startswith("Error fetching URL content"):
            return content

        instances = []
        start = 0
        while True:
            index = content.lower().find(search_string.lower(), start)
            if index == -1 or len(instances) >= max_instances:
                break

            context_start = max(0, index - context_chars)
            context_end = min(
                len(content), index + len(search_string) + context_chars
            )
            instance_context = content[context_start:context_end]
            instances.append(
                f"Instance {len(instances) + 1}:\n{instance_context}\n"
            )

            start = index + len(search_string)

        if instances:
            return (
                f"Found {len(instances)} instance(s) of '{search_string}':\n\n"
                + '\n'.join(instances)
            )
        else:
            return f"Search string '{search_string}' not found in the content."

    # TODO: Move elsewhere
    def planning(self, plan: str) -> str:
        """A function for planning

        This function takes a thought as a string parameter and returns the thought.
        Use this to think out loud before using any tools, and for planning. Call as many times, and with as many lines of thought, as needed.

        Args:
            plan (str): The thought
            explanation (str): An optional explanation

        Returns:
            str: An empty string.
        """
        print(f"Planning: {plan}")
        return "Planned"

    # Make a function for getting content from a URL, that skips the first n characters and gives the next m characters, up to a maximum of 1000 characters.
    def get_url_content_with_offset_updated(
        self, url: str, offset: int, length: int
    ) -> str:
        """Fetch the content of a URL and return the content starting from an offset and up to a given length.

        Args:
            url (str): The URL to fetch content from.
            offset (int): The number of characters to skip from the start of the content.
            length (int): The number of characters to return.

        Returns:
            str: The content starting from the offset and up to the length, or an error message if the URL content could not be fetched.
        """
        if offset < 0:
            return "Offset must be a non-negative integer."
        if length < 1:
            return "Length must be a positive integer."
        if length > 2000:
            return "Length must be at most 2000."

        content = self.get_url_content(url)
        if content.startswith("Error fetching URL content"):
            return content

        return content[offset : offset + length]

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of OpenAIFunction objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.search_wiki),
            FunctionTool(self.search_google),
            FunctionTool(self.search_duckduckgo),
            FunctionTool(self.query_wolfram_alpha),
            FunctionTool(self.get_url_content),
            FunctionTool(self.get_url_content_with_context),
            FunctionTool(self.get_url_content_with_offset_updated),
            FunctionTool(self.planning),
        ]
