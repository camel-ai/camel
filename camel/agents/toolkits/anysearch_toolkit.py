"""
AnySearch Toolkit for CAMEL Agents.

This module provides a toolkit for integrating AnySearch API with CAMEL agents,
supporting web search, page extraction, and various search modes.
"""

from typing import Any, Dict, List, Optional

from camel.agents.toolkits.toolkit import Toolkit


class AnySearchToolkit(Toolkit):
    """A toolkit for AnySearch functionality.

    This toolkit provides search and page extraction capabilities through the
    AnySearch API, supporting authenticated and anonymous modes, parallel
    queries, and vertical search.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anysearch.com/v1",
    ):
        """Initialize the AnySearch toolkit.

        Args:
            api_key: Optional API key for authenticated requests.
            base_url: Base URL for the AnySearch API.
        """
        super().__init__()
        self._api_key = api_key
        self._base_url = base_url
        self._client = None

    def _get_client(self):
        """Get or create the AnySearch client."""
        if self._client is None:
            try:
                from anysearch import AnySearchClient
                self._client = AnySearchClient(
                    api_key=self._api_key,
                    base_url=self._base_url,
                )
            except ImportError:
                raise ImportError(
                    "Please install the anysearch package: "
                    "pip install anysearch"
                )
        return self._client

    def search(
        self,
        query: str,
        num_results: int = 10,
        mode: str = "web",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Perform a web search.

        Args:
            query: The search query.
            num_results: Number of results to return.
            mode: Search mode ('web', 'news', 'scholar', etc.).
            **kwargs: Additional arguments passed to the API.

        Returns:
            Dict containing search results.
        """
        client = self._get_client()
        return client.search(
            query=query,
            num_results=num_results,
            mode=mode,
            **kwargs,
        )

    def extract_page(
        self,
        url: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Extract content from a webpage.

        Args:
            url: The URL to extract content from.
            **kwargs: Additional arguments passed to the API.

        Returns:
            Dict containing extracted page content.
        """
        client = self._get_client()
        return client.extract_page(
            url=url,
            **kwargs,
        )

    def parallel_search(
        self,
        queries: List[str],
        num_results: int = 10,
        mode: str = "web",
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Perform parallel searches.

        Args:
            queries: List of search queries.
            num_results: Number of results per query.
            mode: Search mode.
            **kwargs: Additional arguments.

        Returns:
            List of result dicts.
        """
        client = self._get_client()
        return client.parallel_search(
            queries=queries,
            num_results=num_results,
            mode=mode,
            **kwargs,
        )

    def vertical_search(
        self,
        query: str,
        vertical: str,
        num_results: int = 10,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Perform a vertical search.

        Args:
            query: The search query.
            vertical: The search vertical (e.g., 'images', 'videos', 'news').
            num_results: Number of results.
            **kwargs: Additional arguments.

        Returns:
            Dict containing search results.
        """
        client = self._get_client()
        return client.vertical_search(
            query=query,
            vertical=vertical,
            num_results=num_results,
            **kwargs,
        )

    def get_tools(self) -> List[Any]:
        """Get the list of tools provided by this toolkit.

        Returns:
            List of tool instances.
        """
        # Return tool definitions - the actual functions are bound methods
        # that will be wrapped by CAMEL's tool system
        return [
            self.search,
            self.extract_page,
            self.parallel_search,
            self.vertical_search,
        ]
