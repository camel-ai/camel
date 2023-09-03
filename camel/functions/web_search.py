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
from typing import List

import openai
import requests
from bs4 import BeautifulSoup

from camel.functions import OpenAIFunction


def search_google(query: str):
    """
    using google search engine to search information for the given query.
    Args:
        query(string): what question to search.
    Returns:
        a list of web information, include title, descrption, url.
    """
    # key can find here https://developers.google.com/custom-search/v1/overview
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    # id can find here https://cse.google.com/cse/all
    # https://developers.google.com/custom-search/v1/overview
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    # https://cse.google.com/cse/all
    SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

    # using the first page
    start = 1
    # different language may get different result
    language = "en"
    # how many pages to return
    numbers = 10
    # constructing the URL
    # doc: https://developers.google.com/custom-search/v1/using_rest
    url = f"https://www.googleapis.com/customsearch/v1?" \
          f"key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&q={query}&start=" \
          f"{start}&lr={language}&num={numbers}"

    responses = []
    # make the get
    try:
        result = requests.get(url)
        data = result.json()

        # get the result items
        search_items = data.get("items")

        # iterate over 10 results found
        for i, search_item in enumerate(search_items, start=1):
            try:
                long_description = \
                    search_item["pagemap"]["metatags"][0]["og:description"]
            except KeyError:
                long_description = "N/A"
            # get the page title
            title = search_item.get("title")
            # page snippet
            snippet = search_item.get("snippet")

            # extract the page url
            link = search_item.get("link")
            response = {"Result_id": i,
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
    """
    Get the text information from given url.
    Args:
        url(string): The web site you want to search.

    Returns:
        All texts extract from the web.
    """
    text: str = ""
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
        chunks = (phrase.strip() for line in lines for phrase
                  in line.split("  "))
        text = ".".join(chunk for chunk in chunks if chunk)

    except requests.RequestException:
        print(f"can't get {url}")

    return text

# Split a text into smaller chunks of size n
def create_chunks(text, n):
    """Returns successive n-sized chunks from provided text."""

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
        yield text[i:j]
        i = j


def summarise_text(text: str, query: str) -> str:
    """
    Summarise the information from the text, base on the query if query is
    given.
    Args:
        text(string): text to summarise.
        query(string): what information you want.

    Returns:
        Strings with information.
    """
    summary_prompt = f"Gather information from this text that relative to " \
                     f"the question, but do not directly answer " \
                     f"the question.\nquestion: {query}\ntext "
    # max length of each chunk
    max_len = 3000
    results = ""
    chunks = create_chunks(text, max_len)
    # summarise
    for i, chunk in enumerate(chunks, start=1):
        prompt = summary_prompt + str(i) + ": " + chunk
        response = openai.ChatCompletion.create(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response["choices"][0]["message"]["content"]
        results += result + "\n"

    # final summarise
    final_prompt = f"Here are some summarised texts which split from one " \
                   f"text, Using the information to " \
                   f"answer the question: {query}.\n\nText: "
    prompt = final_prompt + results

    response = openai.ChatCompletion.create(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    return response["choices"][0]["message"]["content"]


def search_web(query: str) -> str:
    """
    search webs for information.
    Args:
        query(string): question you want to be answered.

    Returns:
        Summarised information from webs,
    """
    # google search will return a list of urls
    response = search_google(query)
    answer: str = ""
    for item in response:
        url = item.get("URL")
        # extract text
        text = text_extract_from_web(url)
        # using chatgpt summarise text
        answer = summarise_text(text, query)

        # let chatgpt decide whether to continue search or not
        prompt = f"Do you think the answer: {answer} can answer the query: " \
                 f"{query}. Use only 'yes' or 'no' to answer."
        response = openai.ChatCompletion.create(
            api_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        # add the source
        answer += f"\nFrom: {url}"

        reply = response["choices"][0]["message"]["content"]
        if 'yes' in reply.lower():
            break

    return answer


WEB_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func) for func in [search_web, search_google,
                                      text_extract_from_web, summarise_text]
]