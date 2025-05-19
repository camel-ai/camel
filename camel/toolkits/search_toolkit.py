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
from typing import Any, Dict, List, Literal, Optional, TypeAlias, Union, cast

import requests

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, api_keys_required, dependencies_required


@MCPServer()
class SearchToolkit(BaseToolkit):
    r"""A class representing a toolkit for web search.

    This class provides methods for searching information on the web using
    search engines like Google, DuckDuckGo, Wikipedia and Wolfram Alpha, Brave.
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

    @dependencies_required("linkup")
    @api_keys_required(
        [
            (None, "LINKUP_API_KEY"),
        ]
    )
    def search_linkup(
        self,
        query: str,
        depth: Literal["standard", "deep"] = "standard",
        output_type: Literal[
            "searchResults", "sourcedAnswer", "structured"
        ] = "searchResults",
        structured_output_schema: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Search for a query in the Linkup API and return results in various
        formats.

        Args:
            query (str): The search query.
            depth (Literal["standard", "deep"]): The depth of the search.
                "standard" for a straightforward search, "deep" for a more
                comprehensive search.
            output_type (Literal["searchResults", "sourcedAnswer",
                "structured"]): The type of output:
                - "searchResults" for raw search results,
                - "sourcedAnswer" for an answer with supporting sources,
                - "structured" for output based on a provided schema.
            structured_output_schema (Optional[str]): If `output_type` is
                "structured", specify the schema of the output. Must be a
                string representing a valid object JSON schema.

        Returns:
            Dict[str, Any]: A dictionary representing the search result. The
                structure depends on the `output_type`. If an error occurs,
                returns an error message.
        """
        try:
            from linkup import LinkupClient

            # Initialize the Linkup client with the API key
            LINKUP_API_KEY = os.getenv("LINKUP_API_KEY")
            client = LinkupClient(api_key=LINKUP_API_KEY)

            # Perform the search using the specified output_type
            response = client.search(
                query=query,
                depth=depth,
                output_type=output_type,
                structured_output_schema=structured_output_schema,
            )

            if output_type == "searchResults":
                results = [
                    item.__dict__
                    for item in response.__dict__.get('results', [])
                ]
                return {"results": results}

            elif output_type == "sourcedAnswer":
                answer = response.__dict__.get('answer', '')
                sources = [
                    item.__dict__
                    for item in response.__dict__.get('sources', [])
                ]
                return {"answer": answer, "sources": sources}

            elif output_type == "structured" and structured_output_schema:
                return response.__dict__

            else:
                return {"error": f"Invalid output_type: {output_type}"}

        except Exception as e:
            return {"error": f"An unexpected error occurred: {e!s}"}

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

    @api_keys_required(
        [
            (None, 'BRAVE_API_KEY'),
        ]
    )
    def search_brave(
        self,
        q: str,
        country: str = "US",
        search_lang: str = "en",
        ui_lang: str = "en-US",
        count: int = 20,
        offset: int = 0,
        safesearch: str = "moderate",
        freshness: Optional[str] = None,
        text_decorations: bool = True,
        spellcheck: bool = True,
        result_filter: Optional[str] = None,
        goggles_id: Optional[str] = None,
        units: Optional[str] = None,
        extra_snippets: Optional[bool] = None,
        summary: Optional[bool] = None,
    ) -> Dict[str, Any]:
        r"""This function queries the Brave search engine API and returns a
        dictionary, representing a search result.
        See https://api.search.brave.com/app/documentation/web-search/query
        for more details.

        Args:
            q (str): The user's search query term. Query cannot be empty.
                Maximum of 400 characters and 50 words in the query.
            country (str): The search query country where results come from.
                The country string is limited to 2 character country codes of
                supported countries. For a list of supported values, see
                Country Codes. (default: :obj:`US `)
            search_lang (str): The search language preference. The 2 or more
                character language code for which search results are provided.
                For a list of possible values, see Language Codes.
            ui_lang (str): User interface language preferred in response.
                Usually of the format '<language_code>-<country_code>'. For
                more, see RFC 9110. For a list of supported values, see UI
                Language Codes.
            count (int): The number of search results returned in response.
                The maximum is 20. The actual number delivered may be less than
                requested. Combine this parameter with offset to paginate
                search results.
            offset (int): The zero based offset that indicates number of search
                results per page (count) to skip before returning the result.
                The maximum is 9. The actual number delivered may be less than
                requested based on the query. In order to paginate results use
                this parameter together with count. For example, if your user
                interface displays 20 search results per page, set count to 20
                and offset to 0 to show the first page of results. To get
                subsequent pages, increment offset by 1 (e.g. 0, 1, 2). The
                results may overlap across multiple pages.
            safesearch (str): Filters search results for adult content.
                The following values are supported:
                - 'off': No filtering is done.
                - 'moderate': Filters explicit content, like images and videos,
                    but allows adult domains in the search results.
                - 'strict': Drops all adult content from search results.
            freshness (Optional[str]): Filters search results by when they were
                discovered:
                - 'pd': Discovered within the last 24 hours.
                - 'pw': Discovered within the last 7 Days.
                - 'pm': Discovered within the last 31 Days.
                - 'py': Discovered within the last 365 Days.
                - 'YYYY-MM-DDtoYYYY-MM-DD': Timeframe is also supported by
                    specifying the date range e.g. '2022-04-01to2022-07-30'.
            text_decorations (bool): Whether display strings (e.g. result
                snippets) should include decoration markers (e.g. highlighting
                characters).
            spellcheck (bool): Whether to spellcheck provided query. If the
                spellchecker is enabled, the modified query is always used for
                search. The modified query can be found in altered key from the
                query response model.
            result_filter (Optional[str]): A comma delimited string of result
                types to include in the search response. Not specifying this
                parameter will return back all result types in search response
                where data is available and a plan with the corresponding
                option is subscribed. The response always includes query and
                type to identify any query modifications and response type
                respectively. Available result filter values are:
                - 'discussions'
                - 'faq'
                - 'infobox'
                - 'news'
                - 'query'
                - 'summarizer'
                - 'videos'
                - 'web'
                - 'locations'
            goggles_id (Optional[str]): Goggles act as a custom re-ranking on
                top of Brave's search index. For more details, refer to the
                Goggles repository.
            units (Optional[str]): The measurement units. If not provided,
                units are derived from search country. Possible values are:
                - 'metric': The standardized measurement system
                - 'imperial': The British Imperial system of units.
            extra_snippets (Optional[bool]): A snippet is an excerpt from a
                page you get as a result of the query, and extra_snippets
                allow you to get up to 5 additional, alternative excerpts. Only
                available under Free AI, Base AI, Pro AI, Base Data, Pro Data
                and Custom plans.
            summary (Optional[bool]): This parameter enables summary key
                generation in web search results. This is required for
                summarizer to be enabled.

        Returns:
            Dict[str, Any]: A dictionary representing a search result.
        """

        import requests

        BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Content-Type": "application/json",
            "X-BCP-APIV": "1.0",
            "X-Subscription-Token": BRAVE_API_KEY,
        }

        ParamsType: TypeAlias = Dict[
            str,
            Union[str, int, float, List[Union[str, int, float]], None],
        ]

        params: ParamsType = {
            "q": q,
            "country": country,
            "search_lang": search_lang,
            "ui_lang": ui_lang,
            "count": count,
            "offset": offset,
            "safesearch": safesearch,
            "freshness": freshness,
            "text_decorations": text_decorations,
            "spellcheck": spellcheck,
            "result_filter": result_filter,
            "goggles_id": goggles_id,
            "units": units,
            "extra_snippets": extra_snippets,
            "summary": summary,
        }

        response = requests.get(url, headers=headers, params=params)
        data = response.json()["web"]
        return data

    @api_keys_required(
        [
            (None, 'GOOGLE_API_KEY'),
            (None, 'SEARCH_ENGINE_ID'),
        ]
    )
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

    @api_keys_required([(None, 'BOCHA_API_KEY')])
    def search_bocha(
        self,
        query: str,
        freshness: str = "noLimit",
        summary: bool = False,
        count: int = 10,
        page: int = 1,
    ) -> Dict[str, Any]:
        r"""Query the Bocha AI search API and return search results.

        Args:
            query (str): The search query.
            freshness (str): Time frame filter for search results. Default
                is "noLimit". Options include:
                - 'noLimit': no limit (default).
                - 'oneDay': past day.
                - 'oneWeek': past week.
                - 'oneMonth': past month.
                - 'oneYear': past year.
            summary (bool): Whether to include text summaries in results.
                Default is False.
            count (int): Number of results to return (1-50). Default is 10.
            page (int): Page number of results. Default is 1.

        Returns:
            Dict[str, Any]: A dictionary containing search results, including
                web pages, images, and videos if available. The structure
                follows the Bocha AI search API response format.
        """
        import json

        BOCHA_API_KEY = os.getenv("BOCHA_API_KEY")

        url = "https://api.bochaai.com/v1/web-search"
        headers = {
            "Authorization": f"Bearer {BOCHA_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = json.dumps(
            {
                "query": query,
                "freshness": freshness,
                "summary": summary,
                "count": count,
                "page": page,
            },
            ensure_ascii=False,
        )
        try:
            response = requests.post(url, headers=headers, data=payload)
            if response.status_code != 200:
                return {
                    "error": (
                        f"Bocha API failed with {response.status_code}: "
                        f"{response.text}"
                    )
                }
            return response.json()["data"]
        except requests.exceptions.RequestException as e:
            return {"error": f"Bocha AI search failed: {e!s}"}

    def search_baidu(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        r"""Search Baidu using web scraping to retrieve relevant search
        results. This method queries Baidu's search engine and extracts search
        results including titles, descriptions, and URLs.

        Args:
            query (str): Search query string to submit to Baidu.
            max_results (int): Maximum number of results to return.
                (default: :obj:`5`)

        Returns:
            Dict[str, Any]: A dictionary containing search results or error
                message.
        """
        from bs4 import BeautifulSoup

        try:
            url = "https://www.baidu.com/s"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Referer": "https://www.baidu.com",
            }
            params = {"wd": query, "rn": str(max_results)}

            response = requests.get(url, headers=headers, params=params)
            response.encoding = "utf-8"

            soup = BeautifulSoup(response.text, "html.parser")

            results = []
            for idx, item in enumerate(soup.select(".result"), 1):
                title_element = item.select_one("h3 > a")
                title = (
                    title_element.get_text(strip=True) if title_element else ""
                )

                link = title_element["href"] if title_element else ""

                desc_element = item.select_one(".c-abstract, .c-span-last")
                desc = (
                    desc_element.get_text(strip=True) if desc_element else ""
                )

                results.append(
                    {
                        "result_id": idx,
                        "title": title,
                        "description": desc,
                        "url": link,
                    }
                )
                if len(results) >= max_results:
                    break

            if not results:
                print(
                    "Warning: No results found. Check "
                    "if Baidu HTML structure has changed."
                )

            return {"results": results}

        except Exception as e:
            return {"error": f"Baidu scraping error: {e!s}"}

    def search_bing(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        r"""Use Bing search engine to search information for the given query.

        This function queries the Chinese version of Bing search engine (cn.
        bing.com) using web scraping to retrieve relevant search results. It
        extracts search results including titles, snippets, and URLs. This
        function is particularly useful when the query is in Chinese or when
        Chinese search results are desired.

        Args:
            query (str): The search query string to submit to Bing. Works best
                with Chinese queries or when Chinese results are preferred.
            max_results (int): Maximum number of results to return.
                (default: :obj:`5`)

        Returns:
            Dict ([str, Any]): A dictionary containing either:
                - 'results': A list of dictionaries, each with:
                    - 'result_id': The index of the result.
                    - 'snippet': A brief description of the search result.
                    - 'title': The title of the search result.
                    - 'link': The URL of the search result.
                - or 'error': An error message if something went wrong.
        """
        from typing import Any, Dict, List, cast
        from urllib.parse import urlencode

        from bs4 import BeautifulSoup, Tag

        try:
            query = urlencode({"q": query})
            url = f'https://cn.bing.com/search?{query}'
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
            # Add timeout to prevent hanging
            response = requests.get(url, headers=headers, timeout=10)

            # Check if the request was successful
            if response.status_code != 200:
                return {
                    "error": (
                        f"Bing returned status code: "
                        f"{response.status_code}"
                    )
                }

            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            b_results_element = soup.find("ol", id="b_results")
            if b_results_element is None:
                return {"results": []}

            # Ensure b_results is a Tag and find all li elements
            b_results_tag = cast(Tag, b_results_element)
            result_items = b_results_tag.find_all("li")

            results: List[Dict[str, Any]] = []
            for i in range(min(len(result_items), max_results)):
                row = result_items[i]
                if not isinstance(row, Tag):
                    continue

                h2_element = row.find("h2")
                if h2_element is None:
                    continue
                h2_tag = cast(Tag, h2_element)

                title = h2_tag.get_text().strip()

                link_tag_element = h2_tag.find("a")
                if link_tag_element is None:
                    continue
                link_tag = cast(Tag, link_tag_element)

                link = link_tag.get("href")
                if link is None:
                    continue

                content_element = row.find("p", class_="b_algoSlug")
                content_text = ""
                if content_element is not None and isinstance(
                    content_element, Tag
                ):
                    content_text = content_element.get_text()

                row_data = {
                    "result_id": i + 1,
                    "snippet": content_text,
                    "title": title,
                    "link": link,
                }
                results.append(row_data)

            if not results:
                return {
                    "warning": "No results found. Check if "
                    "Bing HTML structure has changed."
                }

            return {"results": results}

        except Exception as e:
            return {"error": f"Bing scraping error: {e!s}"}

    @api_keys_required([(None, 'EXA_API_KEY')])
    def search_exa(
        self,
        query: str,
        search_type: Literal["auto", "neural", "keyword"] = "auto",
        category: Optional[
            Literal[
                "company",
                "research paper",
                "news",
                "pdf",
                "github",
                "tweet",
                "personal site",
                "linkedin profile",
                "financial report",
            ]
        ] = None,
        num_results: int = 10,
        include_text: Optional[List[str]] = None,
        exclude_text: Optional[List[str]] = None,
        use_autoprompt: bool = True,
        text: bool = False,
    ) -> Dict[str, Any]:
        r"""Use Exa search API to perform intelligent web search with optional
        content extraction.

        Args:
            query (str): The search query string.
            search_type (Literal["auto", "neural", "keyword"]): The type of
                search to perform. "auto" automatically decides between keyword
                and neural search. (default: :obj:`"auto"`)
            category (Optional[Literal]): Category to focus the search on, such
                as "research paper" or "news". (default: :obj:`None`)
            num_results (int): Number of results to return (max 100).
                (default: :obj:`10`)
            include_text (Optional[List[str]]): Strings that must be present in
                webpage text. Limited to 1 string of up to 5 words.
                (default: :obj:`None`)
            exclude_text (Optional[List[str]]): Strings that must not be
                present in webpage text. Limited to 1 string of up to 5 words.
                (default: :obj:`None`)
            use_autoprompt (bool): Whether to use Exa's autoprompt feature to
                enhance the query. (default: :obj:`True`)
            text (bool): Whether to include webpage contents in results.
                (default: :obj:`False`)

        Returns:
            Dict[str, Any]: A dict containing search results and metadata:
                - requestId (str): Unique identifier for the request
                - autopromptString (str): Generated autoprompt if enabled
                - autoDate (str): Timestamp of autoprompt generation
                - resolvedSearchType (str): The actual search type used
                - results (List[Dict]): List of search results with metadata
                - searchType (str): The search type that was selected
                - costDollars (Dict): Breakdown of API costs
        """
        from exa_py import Exa

        EXA_API_KEY = os.getenv("EXA_API_KEY")

        try:
            exa = Exa(EXA_API_KEY)

            if num_results is not None and not 0 < num_results <= 100:
                raise ValueError("num_results must be between 1 and 100")

            if include_text is not None:
                if len(include_text) > 1:
                    raise ValueError("include_text can only contain 1 string")
                if len(include_text[0].split()) > 5:
                    raise ValueError(
                        "include_text string cannot be longer than 5 words"
                    )

            if exclude_text is not None:
                if len(exclude_text) > 1:
                    raise ValueError("exclude_text can only contain 1 string")
                if len(exclude_text[0].split()) > 5:
                    raise ValueError(
                        "exclude_text string cannot be longer than 5 words"
                    )

            # Call Exa API with direct parameters
            if text:
                results = cast(
                    Dict[str, Any],
                    exa.search_and_contents(
                        query=query,
                        type=search_type,
                        category=category,
                        num_results=num_results,
                        include_text=include_text,
                        exclude_text=exclude_text,
                        use_autoprompt=use_autoprompt,
                        text=True,
                    ),
                )
            else:
                results = cast(
                    Dict[str, Any],
                    exa.search(
                        query=query,
                        type=search_type,
                        category=category,
                        num_results=num_results,
                        include_text=include_text,
                        exclude_text=exclude_text,
                        use_autoprompt=use_autoprompt,
                    ),
                )

            return results

        except Exception as e:
            return {"error": f"Exa search failed: {e!s}"}

    @api_keys_required([(None, 'TONGXIAO_API_KEY')])
    def search_alibaba_tongxiao(
        self,
        query: str,
        time_range: Literal[
            "OneDay", "OneWeek", "OneMonth", "OneYear", "NoLimit"
        ] = "NoLimit",
        industry: Optional[
            Literal[
                "finance",
                "law",
                "medical",
                "internet",
                "tax",
                "news_province",
                "news_center",
            ]
        ] = None,
        page: int = 1,
        return_main_text: bool = False,
        return_markdown_text: bool = True,
        enable_rerank: bool = True,
    ) -> Dict[str, Any]:
        r"""Query the Alibaba Tongxiao search API and return search results.

        A powerful search API optimized for Chinese language queries with
        features:
        - Enhanced Chinese language understanding
        - Industry-specific filtering (finance, law, medical, etc.)
        - Structured data with markdown formatting
        - Result reranking for relevance
        - Time-based filtering

        Args:
            query (str): The search query string (length >= 1 and <= 100).
            time_range (Literal["OneDay", "OneWeek", "OneMonth", "OneYear",
                "NoLimit"]): Time frame filter for search results.
                (default: :obj:`"NoLimit"`)
            industry (Optional[Literal["finance", "law", "medical",
                "internet", "tax", "news_province", "news_center"]]):
                Industry-specific search filter. When specified, only returns
                results from sites in the specified industries. Multiple
                industries can be comma-separated.
                (default: :obj:`None`)
            page (int): Page number for results pagination.
                (default: :obj:`1`)
            return_main_text (bool): Whether to include the main text of the
                webpage in results. (default: :obj:`True`)
            return_markdown_text (bool): Whether to include markdown formatted
                content in results. (default: :obj:`True`)
            enable_rerank (bool): Whether to enable result reranking. If
                response time is critical, setting this to False can reduce
                response time by approximately 140ms. (default: :obj:`True`)

        Returns:
            Dict[str, Any]: A dictionary containing either search results with
                'requestId' and 'results' keys, or an 'error' key with error
                message. Each result contains title, snippet, url and other
                metadata.
        """
        TONGXIAO_API_KEY = os.getenv("TONGXIAO_API_KEY")

        # Validate query length
        if not query or len(query) > 100:
            return {
                "error": "Query length must be between 1 and 100 characters"
            }

        # API endpoint and parameters
        base_url = "https://cloud-iqs.aliyuncs.com/search/genericSearch"
        headers = {
            "X-API-Key": TONGXIAO_API_KEY,
        }

        # Convert boolean parameters to string for compatibility with requests
        params: Dict[str, Union[str, int]] = {
            "query": query,
            "timeRange": time_range,
            "page": page,
            "returnMainText": str(return_main_text).lower(),
            "returnMarkdownText": str(return_markdown_text).lower(),
            "enableRerank": str(enable_rerank).lower(),
        }

        # Only add industry parameter if specified
        if industry is not None:
            params["industry"] = industry

        try:
            # Send GET request with proper typing for params
            response = requests.get(
                base_url, headers=headers, params=params, timeout=10
            )

            # Check response status
            if response.status_code != 200:
                return {
                    "error": (
                        f"Alibaba Tongxiao API request failed with status "
                        f"code {response.status_code}: {response.text}"
                    )
                }

            # Parse JSON response
            data = response.json()

            # Extract and format pageItems
            page_items = data.get("pageItems", [])
            results = []
            for idx, item in enumerate(page_items):
                # Create a simplified result structure
                result = {
                    "result_id": idx + 1,
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "hostname": item.get("hostname", ""),
                }

                # Only include additional fields if they exist and are
                # requested
                if "summary" in item and item.get("summary"):
                    result["summary"] = item["summary"]
                elif (
                    return_main_text
                    and "mainText" in item
                    and item.get("mainText")
                ):
                    result["summary"] = item["mainText"]

                if (
                    return_main_text
                    and "mainText" in item
                    and item.get("mainText")
                ):
                    result["main_text"] = item["mainText"]

                if (
                    return_markdown_text
                    and "markdownText" in item
                    and item.get("markdownText")
                ):
                    result["markdown_text"] = item["markdownText"]

                if "score" in item:
                    result["score"] = item["score"]

                if "publishTime" in item:
                    result["publish_time"] = item["publishTime"]

                results.append(result)

            # Return a simplified structure
            return {
                "request_id": data.get("requestId", ""),
                "results": results,
            }

        except requests.exceptions.RequestException as e:
            return {"error": f"Alibaba Tongxiao search request failed: {e!s}"}
        except Exception as e:
            return {
                "error": f"Unexpected error during Alibaba Tongxiao "
                f"search: {e!s}"
            }

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.search_wiki),
            FunctionTool(self.search_linkup),
            FunctionTool(self.search_google),
            FunctionTool(self.search_duckduckgo),
            FunctionTool(self.tavily_search),
            FunctionTool(self.search_brave),
            FunctionTool(self.search_bocha),
            FunctionTool(self.search_baidu),
            FunctionTool(self.search_bing),
            FunctionTool(self.search_exa),
            FunctionTool(self.search_alibaba_tongxiao),
        ]
