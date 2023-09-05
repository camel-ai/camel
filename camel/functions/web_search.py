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

import requests
from bs4 import BeautifulSoup

import camel.agents
from camel.messages import BaseMessage

from .openai_function import OpenAIFunction


def search_google(query: str) -> List[Dict[str, Any]]:
    r"""using google search engine to search information for the given query.

    Args:
        query (string): The query to be searched.

    Returns:
        List[Dict[str, Any]]: A list of dictionary objects, each of which
        title, descrption, url of a website.
    """
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
        search_items = data.get("items")

        # Iterate over 10 results found
        for i, search_item in enumerate(search_items, start=1):
            try:
                long_description = \
                    search_item["pagemap"]["metatags"][0]["og:description"]
            except KeyError:
                long_description = "N/A"
            # Get the page title
            title = search_item.get("title")
            # Page snippet
            snippet = search_item.get("snippet")

            # Extract the page url
            link = search_item.get("link")
            response = {
                "Result_id": i,
                "Title": title,
                "Description": snippet,
                "Long_description": long_description,
                "URL": link
            }
            responses.append(response)

    except requests.RequestException:
        responses.append({"erro": "google search failed."})

    return responses


def text_extract_from_web(url: str) -> str:
    r"""Get the text information from given url.

    Args:
        url (string): The web site you want to search.

    Returns:
        string: All texts extract from the web.
    """
    try:
        # request the target page
        response_text = requests.get(url).text

        # parse the obtained page
        soup = BeautifulSoup(response_text, features="html.parser")

        for script in soup(["script", "style"]):
            script.extract()

        text = soup.get_text()
        # strip text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines
                  for phrase in line.split("  "))
        text = ".".join(chunk for chunk in chunks if chunk)

    except requests.RequestException:
        text = f"can't access {url}"

    return text


# Split a text into smaller chunks of size n
def create_chunks(text: str, n: int) -> List[str]:
    r"""Returns successive n-sized chunks from provided text."

    Args:
        text (string): The text to be split.
        n (int): The max length of a single chunk.

    Returns:
        List[str]: A list of splited texts.
    """

    chunks = []
    i = 0
    while i < len(text):
        # Find the nearest end of sentence within a range of 0.5 * n
        # and 1.5 * n tokens
        j = min(i + int(1.2 * n), len(text))
        while j > i + int(0.8 * n):
            # Decode the tokens and check for full stop or newline
            chunk = text[i:j]
            if chunk.endswith(".") or chunk.endswith("\n"):
                break
            j -= 1
        # If no end of sentence found, use n tokens as the chunk size
        if j == i + int(0.8 * n):
            j = min(i + n, len(text))
        chunks.append(text[i:j])
        i = j
    return chunks


def single_step_agent(prompt: str) -> str:
    """Single step agent. Summarise texts or answer a question."""

    assistant_sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful assistant.",
    )
    agent = camel.agents.ChatAgent(assistant_sys_msg)
    agent.reset()

    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content=prompt,
    )
    assistant_response = agent.step(user_msg)
    if assistant_response.msgs is not None:
        return assistant_response.msg.content
    return ""


def summarise_text(text: str, query: str) -> str:
    r"""Summarise the information from the text, base on the query if query is
    given.

    Args:
        text (string): text to summarise.
        query (string): what information you want.

    Returns:
        string: Strings with information.
    """
    summary_prompt = f"Gather information from this text that relative to " \
                     f"the question, but do not directly answer " \
                     f"the question.\nquestion: {query}\ntext "
    # Max length of each chunk
    max_len = 3000
    results = ""
    chunks = create_chunks(text, max_len)
    # Summarise
    for i, chunk in enumerate(chunks, start=1):
        prompt = summary_prompt + str(i) + ": " + chunk
        result = single_step_agent(prompt)
        results += result + "\n"

    # Final summarise
    final_prompt = f"Here are some summarised texts which split from one " \
                   f"text, Using the information to " \
                   f"answer the question: {query}.\n\nText: "
    prompt = final_prompt + results

    response = single_step_agent(prompt)

    return response


def search_web(query: str) -> str:
    r"""Search webs for information.

    Args:
        query (string): Question you want to be answered.

    Returns:
        string: Summarised information from webs.
    """
    # Google search will return a list of urls
    result = search_google(query)
    answer: str = ""
    for item in result:
        url = item.get("URL")
        # Extract text
        text = text_extract_from_web(str(url))
        # Using chatgpt summarise text
        answer = summarise_text(text, query)

        # Let chatgpt decide whether to continue search or not
        prompt = f"Do you think the answer: {answer} can answer the query: " \
                 f"{query}. Use only 'yes' or 'no' to answer."
        # Add the source
        answer += f"\nFrom: {url}"

        reply = single_step_agent(prompt)
        if "yes" in str(reply).lower():
            break

    return answer


WEB_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func) for func in [search_web, search_google]
]
