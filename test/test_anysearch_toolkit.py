"""Tests for the AnySearch toolkit."""

import pytest
from unittest.mock import MagicMock, patch

from camel.agents.toolkits.anysearch_toolkit import AnySearchToolkit


class TestAnySearchToolkit:
    """Tests for AnySearchToolkit."""

    @patch.dict("sys.modules", {"anysearch": MagicMock()})
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        toolkit = AnySearchToolkit(api_key="test_key")
        assert toolkit._api_key == "test_key"
        assert toolkit._base_url == "https://api.anysearch.com/v1"

    @patch.dict("sys.modules", {"anysearch": MagicMock()})
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        toolkit = AnySearchToolkit()
        assert toolkit._api_key is None

    @patch.dict("sys.modules", {"anysearch": MagicMock()})
    def test_get_tools(self):
        """Test getting tools list."""
        toolkit = AnySearchToolkit()
        tools = toolkit.get_tools()
        assert len(tools) == 4
        assert callable(tools[0])  # search
        assert callable(tools[1])  # extract_page
        assert callable(tools[2])  # parallel_search
        assert callable(tools[3])  # vertical_search


class TestAnySearchMethods:
    """Tests for AnySearch toolkit methods."""

    @patch.dict("sys.modules", {"anysearch": MagicMock()})
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.toolkit = AnySearchToolkit(api_key="test_key")
        self.toolkit._client = self.mock_client

    def test_search(self):
        """Test search method."""
        self.mock_client.search.return_value = {"results": []}
        result = self.toolkit.search(query="test query")
        self.mock_client.search.assert_called_once_with(
            query="test query", num_results=10, mode="web"
        )
        assert result == {"results": []}

    def test_extract_page(self):
        """Test extract_page method."""
        self.mock_client.extract_page.return_value = {"content": "test"}
        result = self.toolkit.extract_page(url="https://example.com")
        self.mock_client.extract_page.assert_called_once_with(
            url="https://example.com"
        )
        assert result == {"content": "test"}

    def test_parallel_search(self):
        """Test parallel_search method."""
        self.mock_client.parallel_search.return_value = [{"results": []}]
        result = self.toolkit.parallel_search(queries=["q1", "q2"])
        self.mock_client.parallel_search.assert_called_once_with(
            queries=["q1", "q2"], num_results=10, mode="web"
        )
        assert result == [{"results": []}]

    def test_vertical_search(self):
        """Test vertical_search method."""
        self.mock_client.vertical_search.return_value = {"results": []}
        result = self.toolkit.vertical_search(
            query="test", vertical="news"
        )
        self.mock_client.vertical_search.assert_called_once_with(
            query="test", vertical="news", num_results=10
        )
        assert result == {"results": []}

    def test_import_error(self):
        """Test ImportError when anysearch is not installed."""
        toolkit = AnySearchToolkit(api_key="test_key")
        with patch.dict("sys.modules", {}, clear=True):
            with pytest.raises(ImportError, match="anysearch"):
                toolkit._get_client()
