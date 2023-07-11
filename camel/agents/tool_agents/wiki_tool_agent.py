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
from typing import Any, List

from camel.agents.tool_agents import BaseToolAgent

SEARCH_OP = "WikiSearch"
LOOKUP_OP = "WikiLookup"


def clean_str(p):
    return p.encode().decode("unicode-escape").encode("latin1").decode("utf-8")


class WikiToolAgent(BaseToolAgent):
    r"""Tool agent for searching contents in WikiPedia. 

    Args:
        name (str): The name of the agent.
    """

    def __init__(
        self,
        name: str,
    ) -> None:
        self.name = name

        # Search Related
        self.page = None
        self.obs = None
        self.result_titles = None

        # Lookup related
        self.lookup_keyword = None
        self.lookup_list = None
        self.lookup_cnt = 0

        # flake8: noqa :E501
        self.description = \
f"""{SEARCH_OP}[<entity>]
- input <entity>: the entity to be searched on Wikipedia
- This will search the exact entity on Wikipedia and returns the first paragraph of the corresponding page if it exists. The collected page will be buffered for potential lookup operations.
- When the returned result fails to offer valid information, do one of the following (index indicates the rank of priority):
    1. Change other available search engines if there is any in available actions
    2. Search related items in the 'Similar' list in the Observation if it exists
    3. Make the search item more general and shorter instead of making it finer
- Example usage: Search[Adam Clayton Powell (film)]
    - by which we can obtain an Observation: "Adam Clayton Powell is a 1989 American documentary film directed by Richard Kilberg."

{LOOKUP_OP}[<keyword>]
- input <keyword>: the keyword to be looked up in the buffered page
- This will return the next sentence containing the keyword in the current buffered passage.
- Example usage: Lookup[American]
"""

    def get_sentences(self) -> List[str]:
        r"""Returns all the sentences in the fetched page.

        Returns:
            List[str]: The list of sentences
        """
        paragraphs = self.page.split('\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # find all sentences
        sentences = []
        for p in paragraphs:
            sentences += p.split('. ')
        sentences = [s.strip() + '.' for s in sentences if s.strip()]

        return sentences

    def get_page_obs(self):
        r"""Returns the first 5 pages in the fetched page.

        Returns:
            List[str]: The list of the first 5 sentences
        """

        sentences = self.get_sentences()
        return ' '.join(sentences[:5])

    # --------------------- Lookup related ---------------------------
    def get_lookup_list(self, keyword: str) -> List[str]:
        r"""Returns the senteces containing the keyword in the fetched page

        Args:
            keyword (str): the keyword to be looked up

        Returns:
            List[str]: The list of sentences containing the keyword
        """

        if self.page is None:
            return []

        sentences = self.get_sentences()
        parts = [s for s in sentences if keyword.lower() in s]
        return parts

    def lookup(self, keyword: str) -> str:
        r"""Present the lookup result in the fetched page given the keyword

        Args:
            keyword (str): The keyword to be looked up in the current page

        Returns:
            str: string containing lookup information and the target sentence
            (if there exists one) 
        """

        # start new lookup operation
        if self.lookup_keyword != keyword:
            self.lookup_keyword = keyword
            self.lookup_list = self.get_lookup_list(keyword)
            self.lookup_cnt = 0

        if self.lookup_cnt >= len(self.lookup_list):
            self.obs = "No more result.\n"
        else:
            self.obs = \
                f"(Result {self.lookup_cnt + 1} / {len(self.lookup_list)}) " \
                + self.lookup_list[self.lookup_cnt]
            self.lookup_cnt += 1

        return self.obs

    # --------------------- Search related ---------------------------
    def search(self, entity: str) -> str:
        r"""Search the entity in WikiPedia and return (the first sentences of)
        the required page.

        Args:
            entity (str): The entity to be searched.

        Returns:
            str: search result. If the page corresponding to the entity
            exists, return the first 5 sentences in a string.
        """

        import requests
        from bs4 import BeautifulSoup

        entity_ = entity.replace(" ", "+")
        search_url = f"https://en.wikipedia.org/w/index.php?search={entity_}"

        # request the target page
        response_text = requests.get(search_url).text

        # parse the obtained page
        soup = BeautifulSoup(response_text, features="html.parser")
        result_divs = soup.find_all("div",
                                    {"class": "mw-search-result-heading"})

        if result_divs:
            # only similar concepts exist
            self.result_titles = [
                clean_str(div.get_text().strip()) for div in result_divs
            ]
            self.obs = (f"Could not find {entity}. "
                        f"Similar: {self.result_titles[:5]}.")
        else:
            # the page corresponding to the entity exists
            page = [
                p.get_text().strip()
                for p in soup.find_all("p") + soup.find_all("ul")
            ]

            if any("may refer to:" in p for p in page):
                self.search("[" + entity + "]")
            else:
                self.page = ""
                for p in page:
                    if len(p.split(" ")) > 2:
                        self.page += clean_str(p)
                        if not p.endswith("\n"):
                            self.page += "\n"

                self.obs = self.get_page_obs()

                # reset lookup
                self.lookup_keyword = self.lookup_list = self.lookup_cnt = None
        return self.obs

    def step(
        self,
        act_input: str,
        operation: str,
    ) -> str:
        r"""Do the search or lookup operation

        Args:
            act_input (str): The entity to be searched or the 
                keyword to be looked up
            operation (str): The operation to be done, which is 
                either search or look-up.

        Returns:
            str: the result of search or lookup.
        """
        if operation == SEARCH_OP:
            return self.search(act_input)
        elif operation == LOOKUP_OP:
            return self.lookup(act_input)
        else:
            raise ValueError(
                f"{self.__class__.__name__}: Undefined operation {operation}")
