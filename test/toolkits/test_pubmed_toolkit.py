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

from unittest.mock import MagicMock, patch

import pytest
import requests

from camel.toolkits import PubMedToolkit


def test_init():
    toolkit = PubMedToolkit()
    assert toolkit.BASE_URL == "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    assert toolkit.timeout is None

    toolkit_with_timeout = PubMedToolkit(timeout=30)
    assert toolkit_with_timeout.timeout == 30


def test_get_tools():
    toolkit = PubMedToolkit()
    tools = toolkit.get_tools()

    assert isinstance(tools, list)
    assert len(tools) == 5

    # Extract function names from FunctionTool objects
    tool_functions = {tool.func.__name__ for tool in tools}
    expected_functions = {
        "search_papers",
        "get_paper_details",
        "get_abstract",
        "get_citation_count",
        "get_related_papers",
    }
    assert tool_functions == expected_functions


@patch('requests.get')
def test_search_papers_success(mock_get):
    # Mock the search response
    mock_search_response = MagicMock()
    mock_search_response.json.return_value = {
        "esearchresult": {"idlist": ["12345", "67890"]}
    }
    mock_search_response.text = (
        '{"esearchresult": {"idlist": ["12345", "67890"]}}'
    )

    # Mock the summary responses for each paper ID
    mock_summary_response1 = MagicMock()
    mock_summary_response1.json.return_value = {
        "result": {
            "12345": {
                "title": "Test Paper 1",
                "authors": [{"name": "Author 1"}, {"name": "Author 2"}],
                "source": "Test Journal",
                "pubdate": "2024",
            }
        }
    }
    mock_summary_response1.text = (
        '{"result": {"12345": {"title": "Test Paper 1"}}}'
    )

    mock_summary_response2 = MagicMock()
    mock_summary_response2.json.return_value = {
        "result": {
            "67890": {
                "title": "Test Paper 2",
                "authors": [{"name": "Author 3"}],
                "source": "Another Journal",
                "pubdate": "2023",
            }
        }
    }
    mock_summary_response2.text = (
        '{"result": {"67890": {"title": "Test Paper 2"}}}'
    )

    # Mock the abstract responses
    mock_abstract_response1 = MagicMock()
    mock_abstract_response1.text = "Test abstract 1"

    mock_abstract_response2 = MagicMock()
    mock_abstract_response2.text = "Test abstract 2"

    # Set up the side effect sequence
    mock_get.side_effect = [
        mock_search_response,  # Search for papers
        mock_summary_response1,  # Get details for paper 12345
        mock_abstract_response1,  # Get abstract for paper 12345
        mock_summary_response2,  # Get details for paper 67890
        mock_abstract_response2,  # Get abstract for paper 67890
    ]

    toolkit = PubMedToolkit()
    results = toolkit.search_papers(
        query="test query",
        max_results=2,
        date_range={"from": "2023/01/01", "to": "2024/12/31"},
        publication_type=["Journal Article"],
    )

    assert len(results) == 2
    assert results[0]["title"] == "Test Paper 1"
    assert results[1]["title"] == "Test Paper 2"

    # Verify the search query construction
    first_call_args = mock_get.call_args_list[0][1]['params']
    assert "test query" in first_call_args['term']
    assert '"Journal Article"[Publication Type]' in first_call_args['term']
    assert (
        "2023/01/01:2024/12/31[Date - Publication]" in first_call_args['term']
    )


@patch('requests.get')
def test_search_papers_error(mock_get):
    mock_get.side_effect = requests.RequestException("API Error")

    toolkit = PubMedToolkit()
    results = toolkit.search_papers("test query")

    assert results == []


@patch('requests.get')
def test_get_paper_details_success(mock_get):
    # Mock the summary response
    mock_summary_response = MagicMock()
    mock_summary_response.json.return_value = {
        "result": {
            "12345": {
                "title": "Test Paper",
                "authors": [{"name": "Author 1"}, {"name": "Author 2"}],
                "source": "Test Journal",
                "pubdate": "2024",
                "mesh": ["Term 1", "Term 2"],
                "keywords": ["keyword1", "keyword2"],
                "pubtype": ["Journal Article"],
            }
        }
    }
    mock_summary_response.text = (
        '{"result": {"12345": {"title": "Test Paper"}}}'
    )

    # Mock the abstract response
    mock_abstract_response = MagicMock()
    mock_abstract_response.text = "Test abstract"

    mock_get.side_effect = [mock_summary_response, mock_abstract_response]

    toolkit = PubMedToolkit()
    result = toolkit.get_paper_details("12345")

    assert result["title"] == "Test Paper"
    assert result["authors"] == "Author 1, Author 2"
    assert result["abstract"] == "Test abstract"
    assert result["mesh_terms"] == ["Term 1", "Term 2"]
    assert result["keywords"] == ["keyword1", "keyword2"]
    assert result["publication_types"] == ["Journal Article"]


@patch('requests.get')
def test_get_paper_details_with_references(mock_get):
    # Mock responses
    mock_summary_response = MagicMock()
    mock_summary_response.json.return_value = {
        "result": {
            "12345": {
                "title": "Test Paper",
                "authors": [{"name": "Author 1"}],
                "source": "Test Journal",
                "pubdate": "2024",
            }
        }
    }
    mock_summary_response.text = (
        '{"result": {"12345": {"title": "Test Paper"}}}'
    )

    mock_abstract_response = MagicMock()
    mock_abstract_response.text = "Test abstract"

    mock_ref_response = MagicMock()
    mock_ref_response.json.return_value = {
        "linksets": [{"linksetdbs": [{"links": ["67890", "11111"]}]}]
    }
    mock_ref_response.text = (
        '{"linksets": [{"linksetdbs": [{"links": ["67890", "11111"]}]}]}'
    )

    mock_get.side_effect = [
        mock_summary_response,
        mock_abstract_response,
        mock_ref_response,
    ]

    toolkit = PubMedToolkit()
    result = toolkit.get_paper_details("12345", include_references=True)

    assert result["references"] == ["67890", "11111"]


@patch('requests.get')
def test_get_citation_count(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "linksets": [{"linksetdbs": [{"links": ["1", "2", "3"]}]}]
    }
    mock_response.text = (
        '{"linksets": [{"linksetdbs": [{"links": ["1", "2", "3"]}]}]}'
    )

    mock_get.return_value = mock_response

    toolkit = PubMedToolkit()
    count = toolkit.get_citation_count("12345")

    assert count == 3


@patch('requests.get')
def test_get_related_papers(mock_get):
    # Mock the related papers response
    mock_related_response = MagicMock()
    mock_related_response.json.return_value = {
        "linksets": [{"linksetdbs": [{"links": ["12345"]}]}]
    }
    mock_related_response.text = (
        '{"linksets": [{"linksetdbs": [{"links": ["12345"]}]}]}'
    )

    # Mock the paper details response
    mock_details_response = MagicMock()
    mock_details_response.json.return_value = {
        "result": {
            "12345": {
                "title": "Related Paper",
                "authors": [{"name": "Author 1"}],
                "source": "Test Journal",
                "pubdate": "2024",
            }
        }
    }
    mock_details_response.text = (
        '{"result": {"12345": {"title": "Related Paper"}}}'
    )

    # Mock the abstract response
    mock_abstract_response = MagicMock()
    mock_abstract_response.text = "Test abstract"

    mock_get.side_effect = [
        mock_related_response,
        mock_details_response,
        mock_abstract_response,
    ]

    toolkit = PubMedToolkit()
    results = toolkit.get_related_papers("67890", max_results=1)

    assert len(results) == 1
    assert results[0]["title"] == "Related Paper"


def test_invalid_timeout():
    with pytest.raises(ValueError):
        PubMedToolkit(timeout=-1)
