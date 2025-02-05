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
from typing import List

import requests

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit


class SemanticScholarToolkit(BaseToolkit):
    """A toolkit for interacting with the Semantic Scholar
    API to fetch paper and author data."""

    def __init__(self):
        """Initializes the SemanticScholarToolkit."""
        self.base_url = "https://api.semanticscholar.org/graph/v1"

    def fetch_paper_data_title(
        self,
        paperTitle: str,
        fields: str = """title,abstract,authors,year,citationCount,
        publicationTypes,publicationDate,openAccessPdf""",
    ) -> dict:
        r"""Fetches a SINGLE paper from the Semantic Scholar
        API based on a paper title.

        Args:
            paperTitle (str): The title of the paper to fetch.
            fields (str): A comma-separated list of fields to include
            in the response (default includes title, abstract, authors, year,
            citation count, publicationTypes,publicationDate,openAccessPdf).

        Returns:
            dict: The response data from the API or error
            information if the request fails.
        """
        url = f"{self.base_url}/paper/search"
        query_params = {"query": paperTitle, "fields": fields}
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
        paperID: str,
        fields: str = """title,abstract,authors,year,citationCount,
        publicationTypes,publicationDate,openAccessPdf""",
    ) -> dict:
        r"""Fetches a SINGLE paper from the Semantic Scholar
         API based on a paper ID.

        Args:
            paperID (str): The ID of the paper to fetch.
            fields (str): A comma-separated list of fields to
            include in the response (default includes title, abstract,
            authors, year, citation count, publicationTypes,
            publicationDate, openAccessPdf).

        Returns:
            dict: The response data from the API or error information
            if the request fails.
        """
        url = f"{self.base_url}/paper/{paperID}"
        query_params = {"fields": fields}
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
        fields: str = """title,url,publicationTypes,
        publicationDate,openAccessPdf""",
    ) -> dict:
        r"""Fetches MULTIPLE papers at once from the Semantic Scholar
         API based on a related topic.
        Args:
            query (str):
                The text query to match against the paper's title
                and abstract.
                For example, you can use the following operators
                and techniques to construct your query:
                Example 1:
                    ((cloud computing) | virtualization)
                    +security -privacy This will match papers
                    whose title or abstract contains "cloud"
                    and "computing", or contains the word
                    "virtualization". The papers must also
                    include the term "security" but exclude
                    papers that contain the word "privacy".
            year (str): The year filter for papers (default is "2023-").
            fields (str): The fields to include in the response
            (e.g., 'title,url,publicationTypes,publicationDate,
            openAccessPdf').
        Returns:
            dict: The response data from the API or
            error information if the request fails.
        """
        url = f"{self.base_url}/paper/search/bulk"
        query_params = {"query": query, "fields": fields, "year": year}
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
        fields: str = """title,url,citationCount,authors,
        publicationTypes,publicationDate,openAccessPdf""",
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

            fields (str): The fields to include in the response
            (e.g., 'title,url,citationCount,authors,publicationTypes,
            publicationDate,openAccessPdf').

            limit (int): The maximum number of recommended papers to return.
            Default is 500.

            save_to_file (bool): If True, saves the response data to a file
            (default is False).

        Returns:
            dict: A dictionary containing recommended papers sorted by
            citation count.
        """
        url = "https://api.semanticscholar.org/recommendations/v1/papers"
        query_params = {"fields": fields, "limit": str(limit)}
        data = {
            "positivePaperIds": positive_paper_ids,
            "negativePaperIds": negative_paper_ids,
        }
        try:
            response = requests.post(url, params=query_params, json=data)
            response.raise_for_status()
            papers = response.json()
            if save_to_file:
                with open('recommended_papers.json', 'w') as output:
                    json.dump(papers, output)
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
        fields: str = "name,url,paperCount,hIndex,papers",
        save_to_file: bool = False,
    ) -> dict:
        r"""Fetches author information from the Semantic Scholar
        API based on author IDs.

        Args:
            ids (list): A list of author IDs (as strings) to fetch
            data for.

            fields (str): A comma-separated list of fields to include
            in the response (default includes name, URL, paper count,
            hIndex, and papers).

            save_to_file (bool): If True, saves the response data to
            a file (default is False).

        Returns:
            dict: The response data from the API or error information if
            the request fails.
        """
        url = f"{self.base_url}/author/batch"
        query_params = {"fields": fields}
        data = {"ids": ids}
        try:
            response = requests.post(url, params=query_params, json=data)
            response.raise_for_status()
            response_data = response.json()
            if save_to_file:
                with open('author_information.json', 'w') as output:
                    json.dump(response_data, output)
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
