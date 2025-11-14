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

from typing import Any, Dict, List, Optional, Union, cast

import requests

from camel.logger import get_logger
from camel.toolkits import BaseToolkit, FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class PubMedToolkit(BaseToolkit):
    r"""A toolkit for interacting with PubMed's E-utilities API to access
    MEDLINE data.

    This toolkit provides functionality to search and retrieve papers from the
    PubMed database, including abstracts, citations, and other metadata.

    Args:
        timeout (Optional[float]): The timeout for API requests in seconds.
            (default: :obj:`None`)
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, timeout: Optional[float] = None) -> None:
        r"""Initializes the PubMedToolkit."""
        super().__init__(timeout=timeout)

    def _make_request(
        self,
        endpoint: str,
        params: Dict[str, Union[str, int]],
        retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        r"""Makes a request to the PubMed/MEDLINE API with error handling and
        retries.

        Args:
            endpoint (str): The API endpoint to call.
            params (Dict[str, Union[str, int]]): Query parameters.
            retries (int, optional): Number of retry attempts.
                (default: :obj:`3`)

        Returns:
            Optional[Dict[str, Any]]: JSON response if successful, else None.
        """
        url = f"{self.BASE_URL}/{endpoint}"
        request_params = cast(Dict[str, Union[str, int]], params)

        for attempt in range(retries):
            try:
                response = requests.get(
                    url, params=request_params, timeout=self.timeout
                )
                response.raise_for_status()

                if not response.text:
                    logger.warning(
                        f"Empty response from PubMed API: {endpoint}"
                    )
                    return None

                return response.json()
            except requests.RequestException as e:
                if attempt == retries - 1:
                    logger.error(f"Failed to fetch data from PubMed: {e!s}")
                    return None
                logger.warning(f"Request attempt {attempt + 1} failed: {e!s}")
            except ValueError as e:
                logger.error(f"Failed to parse JSON response: {e!s}")
                return None
        return None

    def search_papers(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance",
        date_range: Optional[Dict[str, str]] = None,
        publication_type: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        r"""Search for biomedical papers in MEDLINE via PubMed with advanced
        filtering options.

        Args:
            query (str): The search query string.
            max_results (int, optional): Maximum number of results to return.
                (default: :obj:`10`)
            sort (str, optional): Sort order - 'relevance' or 'date'.
                (default: :obj:`"relevance"`)
            date_range (Optional[Dict[str, str]], optional): Date range filter
                with 'from' and 'to' dates in YYYY/MM/DD format.
                (default: :obj:`None`)
            publication_type (Optional[List[str]], optional): Filter by
                publication types (e.g., ["Journal Article", "Review"]).
                (default: :obj:`None`)

        Returns:
            List[Dict[str, str]]: List of papers with their metadata.
        """
        # Build query with filters
        filtered_query = query
        if publication_type:
            type_filter = " OR ".join(
                [f'"{pt}"[Publication Type]' for pt in publication_type]
            )
            filtered_query = f"({query}) AND ({type_filter})"
        if date_range:
            date_filter = (
                f"{date_range.get('from', '')}:"
                f"{date_range.get('to', '')}[Date - Publication]"
            )
            filtered_query = f"({filtered_query}) AND ({date_filter})"

        # Search for paper IDs
        search_params: Dict[str, Union[str, int]] = {
            "db": "pubmed",
            "term": filtered_query,
            "retmax": max_results,
            "sort": "relevance" if sort == "relevance" else "pub+date",
            "retmode": "json",
        }

        search_data = self._make_request("esearch.fcgi", search_params)
        if not search_data or "esearchresult" not in search_data:
            logger.error("Failed to retrieve search results")
            return []

        paper_ids = search_data["esearchresult"].get("idlist", [])
        if not paper_ids:
            return []

        # Fetch details for papers
        results = []
        for paper_id in paper_ids:
            paper_details = self.get_paper_details(paper_id)
            if paper_details:
                results.append(paper_details)

        return results

    def get_paper_details(
        self,
        paper_id: Union[str, int],
        include_references: bool = False,
    ) -> Optional[Dict[str, Any]]:
        r"""Get detailed information about a specific biomedical paper from
        MEDLINE/PubMed.

        Args:
            paper_id (Union[str, int]): PubMed ID of the paper.
            include_references (bool, optional): Whether to include referenced
                papers. (default: :obj:`False`)

        Returns:
            Optional[Dict[str, Any]]: Paper details including title, authors,
                abstract, etc., or None if retrieval fails.
        """
        # Fetch summary
        summary_params: Dict[str, Union[str, int]] = {
            "db": "pubmed",
            "id": str(paper_id),
            "retmode": "json",
        }
        summary_data = self._make_request("esummary.fcgi", summary_params)

        if not summary_data or "result" not in summary_data:
            logger.error(
                f"Failed to retrieve paper details for ID: {paper_id}"
            )
            return None

        paper_data = summary_data["result"][str(paper_id)]

        # Handle authors - they come as a list of dicts with 'name' key
        authors = paper_data.get("authors", [])
        author_names = []
        for author in authors:
            if isinstance(author, dict) and "name" in author:
                author_names.append(author["name"])
            elif isinstance(author, str):
                author_names.append(author)

        # Get abstract
        abstract = self.get_abstract(paper_id)

        # Get references if requested
        references = []
        if include_references:
            ref_params: Dict[str, Union[str, int]] = {
                "db": "pubmed",
                "id": str(paper_id),
                "linkname": "pubmed_pubmed_refs",
                "retmode": "json",
            }
            ref_data = self._make_request("elink.fcgi", ref_params)
            if ref_data and "linksets" in ref_data:
                try:
                    references = ref_data["linksets"][0]["linksetdbs"][0][
                        "links"
                    ]
                except (KeyError, IndexError):
                    logger.warning(
                        f"No references found for paper ID: {paper_id}"
                    )

        return cast(
            Dict[str, Any],
            {
                "id": str(paper_id),
                "title": paper_data.get("title", ""),
                "authors": ", ".join(author_names),
                "journal": paper_data.get("source", ""),
                "pub_date": paper_data.get("pubdate", ""),
                "abstract": abstract,
                "doi": paper_data.get("elocationid", ""),
                "keywords": paper_data.get("keywords", []),
                "mesh_terms": paper_data.get("mesh", []),
                "publication_types": paper_data.get("pubtype", []),
                "references": references if include_references else None,
            },
        )

    def get_abstract(self, paper_id: Union[str, int]) -> str:
        r"""Get the abstract of a specific biomedical paper from MEDLINE/
        PubMed.

        Args:
            paper_id (Union[str, int]): PubMed ID of the paper.

        Returns:
            str: The abstract text.
        """
        params: Dict[str, Union[str, int]] = {
            "db": "pubmed",
            "id": str(paper_id),
            "rettype": "abstract",
            "retmode": "text",
        }

        try:
            response = requests.get(
                f"{self.BASE_URL}/efetch.fcgi", params=params
            )
            response.raise_for_status()
            return response.text.strip()
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Failed to retrieve abstract for ID {paper_id}: {e!s}"
            )
            return ""

    def get_citation_count(self, paper_id: Union[str, int]) -> int:
        r"""Get the number of citations for a biomedical paper in MEDLINE/
        PubMed.

        Args:
            paper_id (Union[str, int]): PubMed ID of the paper.

        Returns:
            int: Number of citations, or 0 if retrieval fails.
        """
        params: Dict[str, Union[str, int]] = {
            "db": "pubmed",
            "id": str(paper_id),
            "linkname": "pubmed_pubmed_citedin",
            "retmode": "json",
        }

        data = self._make_request("elink.fcgi", params)
        if not data or "linksets" not in data:
            return 0

        try:
            return len(data["linksets"][0]["linksetdbs"][0]["links"])
        except (KeyError, IndexError):
            return 0

    def get_related_papers(
        self,
        paper_id: Union[str, int],
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        r"""Get biomedical papers related to a specific paper in MEDLINE/
        PubMed.

        Args:
            paper_id (Union[str, int]): PubMed ID of the paper.
            max_results (int, optional): Maximum number of results to return.
                (default: :obj:`10`)

        Returns:
            List[Dict[str, Any]]: List of related papers with their metadata.
        """
        params: Dict[str, Union[str, int]] = {
            "db": "pubmed",
            "id": str(paper_id),
            "linkname": "pubmed_pubmed",
            "retmode": "json",
        }

        data = self._make_request("elink.fcgi", params)
        if not data or "linksets" not in data:
            return []

        try:
            related_ids = data["linksets"][0]["linksetdbs"][0]["links"][
                :max_results
            ]
            related_papers: List[Dict[str, Any]] = []

            for pid in related_ids:
                if paper := self.get_paper_details(pid):
                    related_papers.append(paper)

            return related_papers
        except (KeyError, IndexError):
            return []

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the PubMed toolkit.

        Returns:
            List[FunctionTool]: List of available tools.
        """
        return [
            FunctionTool(self.search_papers),
            FunctionTool(self.get_paper_details),
            FunctionTool(self.get_abstract),
            FunctionTool(self.get_citation_count),
            FunctionTool(self.get_related_papers),
        ]
