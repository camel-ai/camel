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

import json
from typing import List, Optional

import requests

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer


@MCPServer()
class SemanticScholarToolkit(BaseToolkit):
    r"""A toolkit for interacting with the Semantic Scholar
    API to fetch paper and author data.
    """

    def __init__(self, timeout: Optional[float] = None):
        r"""Initializes the SemanticScholarToolkit."""
        super().__init__(timeout=timeout)
        self.base_url = "https://api.semanticscholar.org/graph/v1"

    def fetch_paper_data_title(
        self,
        paper_title: str,
        fields: Optional[List[str]] = None,
    ) -> dict:
        r"""Fetches a SINGLE paper from the Semantic Scholar
        API based on a paper title.

        Args:
            paper_title (str): The title of the paper to fetch.
            fields (Optional[List[str]], optional): The fields to include in
                the response (default: :obj:`None`). If not provided defaults
                to ["title", "abstract", "authors", "year", "citationCount",
                "publicationTypes", "publicationDate", "openAccessPdf"].

        Returns:
            dict: The response data from the API or error information if the
                 request fails.
        """
        if fields is None:
            fields = [
                "title",
                "abstract",
                "authors",
                "year",
                "citationCount",
                "publicationTypes",
                "publicationDate",
                "openAccessPdf",
            ]

        url = f"{self.base_url}/paper/search"
        query_params = {"query": paper_title, "fields": ",".join(fields)}
        try:
            response = requests.get(url, params=query_params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Request failed: {e!s}",
                "message": str(e),
            }
        except ValueError:
            return {
                "error": "Response is not valid JSON",
                "message": response.text,
            }

    def fetch_paper_data_id(
        self,
        paper_id: str,
        fields: Optional[List[str]] = None,
    ) -> dict:
        r"""Fetches a SINGLE paper from the Semantic Scholar
        API based on a paper ID.

        Args:
            paper_id (str): The ID of the paper to fetch.
            fields (Optional[List[str]], optional): The fields to include in
                the response (default: :obj:`None`). If not provided defaults
                to ["title", "abstract", "authors", "year", "citationCount",
                "publicationTypes", "publicationDate", "openAccessPdf"].

        Returns:
            dict: The response data from the API or error information
                if the request fails.
        """
        if fields is None:
            fields = [
                "title",
                "abstract",
                "authors",
                "year",
                "citationCount",
                "publicationTypes",
                "publicationDate",
                "openAccessPdf",
            ]

        url = f"{self.base_url}/paper/{paper_id}"
        query_params = {"fields": ",".join(fields)}
        try:
            response = requests.get(url, params=query_params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Request failed: {e!s}",
                "message": str(e),
            }
        except ValueError:
            return {
                "error": "Response is not valid JSON",
                "message": response.text,
            }

    def fetch_bulk_paper_data(
        self,
        query: str,
        year: str = "2023-",
        fields: Optional[List[str]] = None,
    ) -> dict:
        r"""Fetches MULTIPLE papers at once from the Semantic Scholar
        API based on a related topic.

        Args:
            query (str): The text query to match against the paper's title and
                abstract. For example, you can use the following operators and
                techniques to construct your query: Example 1: ((cloud
                computing) | virtualization) +security -privacy This will
                match papers whose title or abstract contains "cloud" and
                "computing", or contains the word "virtualization". The papers
                must also include the term "security" but exclude papers that
                contain the word "privacy".
            year (str, optional): The year filter for papers (default:
                :obj:`"2023-"`).
            fields (Optional[List[str]], optional): The fields to include in
                the response (default: :obj:`None`). If not provided defaults
                to ["title", "url", "publicationTypes", "publicationDate",
                "openAccessPdf"].

        Returns:
            dict: The response data from the API or error information if the
                request fails.
        """
        if fields is None:
            fields = [
                "title",
                "url",
                "publicationTypes",
                "publicationDate",
                "openAccessPdf",
            ]

        url = f"{self.base_url}/paper/search/bulk"
        query_params = {
            "query": query,
            "fields": ",".join(fields),
            "year": year,
        }
        try:
            response = requests.get(url, params=query_params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": f"Request failed: {e!s}",
                "message": str(e),
            }
        except ValueError:
            return {
                "error": "Response is not valid JSON",
                "message": response.text,
            }

    def fetch_recommended_papers(
        self,
        positive_paper_ids: List[str],
        negative_paper_ids: List[str],
        fields: Optional[List[str]] = None,
        limit: int = 500,
        save_to_file: bool = False,
    ) -> dict:
        r"""Fetches recommended papers from the Semantic Scholar
        API based on the positive and negative paper IDs.

        Args:
            positive_paper_ids (list): A list of paper IDs (as strings)
                that are positively correlated to the recommendation.
            negative_paper_ids (list): A list of paper IDs (as strings)
                that are negatively correlated to the recommendation.
            fields (Optional[List[str]], optional): The fields to include in
                the response (default: :obj:`None`). If not provided defaults
                to ["title", "url", "citationCount", "authors",
                "publicationTypes", "publicationDate", "openAccessPdf"].
            limit (int, optional): The maximum number of recommended papers to
                return (default: :obj:`500`).
            save_to_file (bool, optional): If True, saves the response data to
                a file (default: :obj:`False`).

        Returns:
            dict: A dictionary containing recommended papers sorted by
                citation count.
        """
        if fields is None:
            fields = [
                "title",
                "url",
                "citationCount",
                "authors",
                "publicationTypes",
                "publicationDate",
                "openAccessPdf",
            ]

        url = "https://api.semanticscholar.org/recommendations/v1/papers"
        query_params = {"fields": ",".join(fields), "limit": str(limit)}
        data = {
            "positive_paper_ids": positive_paper_ids,
            "negative_paper_ids": negative_paper_ids,
        }
        try:
            response = requests.post(url, params=query_params, json=data)
            response.raise_for_status()
            papers = response.json()
            if save_to_file:
                with open('recommended_papers.json', 'w') as output:
                    json.dump(papers, output, ensure_ascii=False)
            return papers
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
        except ValueError:
            return {
                "error": "Response is not valid JSON",
                "message": response.text,
            }

    def fetch_author_data(
        self,
        ids: List[str],
        fields: Optional[List[str]] = None,
        save_to_file: bool = False,
    ) -> dict:
        r"""Fetches author information from the Semantic Scholar
        API based on author IDs.

        Args:
            ids (list): A list of author IDs (as strings) to fetch
                data for.
            fields (Optional[List[str]], optional): The fields to include in
                the response (default: :obj:`None`). If not provided defaults
                to ["name", "url", "paperCount", "hIndex", "papers"].
            save_to_file (bool, optional): Whether to save the results to a
                file (default: :obj:`False`).

        Returns:
            dict: The response data from the API or error information if
                the request fails.
        """
        if fields is None:
            fields = ["name", "url", "paperCount", "hIndex", "papers"]

        url = f"{self.base_url}/author/batch"
        query_params = {"fields": ",".join(fields)}
        data = {"ids": ids}
        try:
            response = requests.post(url, params=query_params, json=data)
            response.raise_for_status()
            response_data = response.json()
            if save_to_file:
                with open('author_information.json', 'w') as output:
                    json.dump(response_data, output, ensure_ascii=False)
            return response_data
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
        except ValueError:
            return {
                "error": "Response is not valid JSON",
                "message": response.text,
            }

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.fetch_paper_data_title),
            FunctionTool(self.fetch_paper_data_id),
            FunctionTool(self.fetch_bulk_paper_data),
            FunctionTool(self.fetch_recommended_papers),
            FunctionTool(self.fetch_author_data),
        ]
