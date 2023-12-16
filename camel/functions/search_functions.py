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
from typing import Any, Dict, List

from camel.utils import Chromadb
from camel.functions import OpenAIFunction


def search_wiki(entity: str) -> str:
    r"""Search the entity in WikiPedia and return the summary of the
    required page, containing factual information about the given entity.

    Args:
        entity (string): The entity to be searched.

    Returns:
        string: The search result. If the page corresponding to the entity
            exists, return the summary of this entity in a string.
    """
    try:
        import wikipedia
    except ImportError:
        raise ImportError(
            "Please install `wikipedia` first. You can install it by running "
            "`pip install wikipedia`.")

    result: str

    try:
        result = wikipedia.summary(entity, sentences=5, auto_suggest=False)
    except wikipedia.exceptions.DisambiguationError as e:
        result = wikipedia.summary(e.options[0], sentences=5,
                                   auto_suggest=False)
    except wikipedia.exceptions.PageError:
        result = ("There is no page in Wikipedia corresponding to entity "
                  f"{entity}, please specify another word to describe the"
                  " entity to be searched.")
    except wikipedia.exceptions.WikipediaException as e:
        result = f"An exception occurred during the search: {e}"

    return result


def search_google(query: str) -> List[Dict[str, Any]]:
    r"""Use Google search engine to search information for the given query.

    Args:
        query (string): The query to be searched.

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
                 intelligence research company. Our goal is to advance digital
                intelligence in the way that is most likely to benefit humanity
                as a whole',
                'url': 'https://www.openai.com'
            }
        title, descrption, url of a website.
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
    num_result_pages = 10
    # Constructing the URL
    # Doc: https://developers.google.com/custom-search/v1/using_rest
    url = f"https://www.googleapis.com/customsearch/v1?" \
          f"key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&q={query}&start=" \
          f"{start_page_idx}&lr={search_language}&num={num_result_pages}"

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
                if "og:description" in search_item["pagemap"]["metatags"][0]:
                    long_description = \
                        search_item["pagemap"]["metatags"][0]["og:description"]
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
                    "url": link
                }
                responses.append(response)
        else:
            responses.append({"error": "google search failed."})

    except requests.RequestException:
        responses.append({"error": "google search failed."})

    return responses


def text_extract_from_web(url: str) -> str:
    r"""Get the text information from given url.

    Args:
        url (string): The web site you want to search.

    Returns:
        string: All texts extract from the web.
    """
    import requests
    from bs4 import BeautifulSoup

    try:
        # Request the target page
        response_text = requests.get(url).text

        # Parse the obtained page
        soup = BeautifulSoup(response_text, features="html.parser")

        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text()
        # Strip text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines
                  for phrase in line.split("  "))
        text = ".".join(chunk for chunk in chunks if chunk)

    except requests.RequestException:
        text = f"can't access {url}"

    return text


def search_google_and_summarize(query: str) -> str:
    r"""Search webs for information. Given a query, this function will use
    the Google search engine to search for related information from the
    internet, and then return a summarized answer.

    Args:
        query (string): Question you want to be answered.

    Returns:
        string: Summarized information from webs.
    """
    # Google search will return a list of urls
    responses = search_google(query)
    # Using database store the information, in-memory chroma by default
    db = Chromadb()
    for item in responses:
        if "url" in item:
            url = item.get("url")
            # Extract text
            text = text_extract_from_web(str(url))
            # store the text
            db.add_text(text)
    # Retrive the reletive information about the query
    # Each result contains about 512 words
    answer = db.query_texts(query, n_results=5)

    return answer['documents']


SEARCH_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func)
    for func in [search_google_and_summarize]
]
