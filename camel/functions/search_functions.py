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
from typing import List

import requests
from bs4 import BeautifulSoup

from .openai_function import OpenAIFunction


def clean_str(p: str) -> str:
    r"""Cleans the input string by encoding and decoding it multiple times
    to ensure it can be properly read and processed by Python code

    Args:
        p (str): The input string to be cleaned, typically from the webpage

    Returns:
        str: The cleaned string
    """
    return p.encode().decode("unicode-escape")\
            .encode("latin1").decode("utf-8")


def get_page_obs(page):
    r"""Returns the first 5 pages in the fetched page.

    Returns:
        List[str]: The list of the first 5 sentences
    """
    paragraphs = page.split('\n')
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    # find all sentences
    sentences = []
    for p in paragraphs:
        sentences += p.split('. ')
    sentences = [s.strip() + '.' for s in sentences if s.strip()]

    return ' '.join(sentences[:5])


def search_wiki(entity: str) -> str:
    r"""Search the entity in WikiPedia and return (the first sentences of)
    the required page.

    Args:
        entity (string): The entity to be searched.

    Returns:
        string: search result. If the page corresponding to the entity
        exists, return the first 5 sentences in a string.
    """
    entity_ = entity.replace(" ", "+")
    search_url = f"https://en.wikipedia.org/w/index.php?search={entity_}"

    # request the target page
    response_text = requests.get(search_url).text

    # parse the obtained page
    soup = BeautifulSoup(response_text, features="html.parser")
    result_divs = soup.find_all("div", {"class": "mw-search-result-heading"})

    obs: str
    if result_divs:
        # only similar concepts exist
        result_titles = [
            clean_str(div.get_text().strip()) for div in result_divs
        ]
        obs = (f"Could not find {entity}. "
               f"Similar: {result_titles[:5]}.")
    else:
        # the page corresponding to the entity exists
        page = [
            p.get_text().strip()
            for p in soup.find_all("p") + soup.find_all("ul")
        ]

        if any("may refer to:" in p for p in page):
            return search_wiki("[" + entity + "]")
        else:
            res_page = ""
            for p in page:
                if len(p.split(" ")) > 2:
                    res_page += clean_str(p)
                    if not p.endswith("\n"):
                        res_page += "\n"

            obs = get_page_obs(res_page)

    return obs


SEARCH_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func) for func in [search_wiki]
]
