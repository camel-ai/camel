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
from typing import List, Optional

from camel.toolkits import OpenAIFunction
from camel.toolkits.base import BaseToolkit


class GoogleScholarToolkit(BaseToolkit):
    r"""A toolkit for retrieving information about authors and their
    publications from Google Scholar.

    Attributes:
        author_name (str): The name of the author to search for.
        scholarly (module): The scholarly module for querying Google Scholar.
        first_author_result (dict): The first search result for the author.
    """

    def __init__(self, author_name: str) -> None:
        r"""Initializes the GoogleScholarToolkit with the author's name.

        Args:
            author_name (str): The name of the author to search for.
        """
        from scholarly import scholarly

        self.scholarly = scholarly
        search_query = scholarly.search_author(author_name)
        # Retrieve the first result from the iterator
        self.first_author_result = next(search_query)

    def get_author_detailed_info(
        self,
    ) -> dict:
        r"""Retrieves detailed information about the author.

        Returns:
            dict: A dictionary containing detailed information about the
                author.
        """
        author = self.scholarly.fill(self.first_author_result)
        return author

    def get_author_publications(
        self,
    ) -> List[str]:
        r"""Retrieves the titles of the author's publications.

        Returns:
            List[str]: A list of publication titles authored by the author.
        """
        author = self.get_author_detailed_info()
        publication_titles = [
            pub['bib']['title'] for pub in author['publications']
        ]
        return publication_titles

    def get_publication_by_title(
        self, publication_title: str
    ) -> Optional[dict]:
        r"""Retrieves detailed information about a specific publication by its
        title.

        Args:
            publication_title (str): The title of the publication to search
                for.

        Returns:
            Optional[dict]: A dictionary containing detailed information about
                the publication if found; otherwise, `None`.
        """
        author = self.get_author_detailed_info()
        publications = author['publications']
        for publication in publications:
            if publication['bib']['title'] == publication_title:
                return self.scholarly.fill(publication)
        return None  # Return None if not found

    def get_tools(self) -> List[OpenAIFunction]:
        r"""Returns a list of OpenAIFunction objects representing the
        functions in the toolkit.

        Returns:
            List[OpenAIFunction]: A list of OpenAIFunction objects
                representing the functions in the toolkit.
        """
        return [
            OpenAIFunction(self.get_author_detailed_info),
            OpenAIFunction(self.get_author_publications),
            OpenAIFunction(self.get_publication_by_title),
        ]
