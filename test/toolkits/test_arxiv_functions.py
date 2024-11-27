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

from camel.toolkits import ArxivToolkit


@patch('arxiv.Client')
def test_arxiv_toolkit_init(mock_client):
    toolkit = ArxivToolkit()
    mock_client.assert_called_once()
    assert isinstance(toolkit.client, MagicMock)


@patch('arxiv.Search')
@patch('arxiv.Client')
def test_get_search_results(mock_client, mock_search):
    toolkit = ArxivToolkit()
    mock_client_instance = mock_client.return_value

    mock_client_instance.results.return_value = iter([MagicMock()])

    query = "multi-agent"
    result_generator = toolkit._get_search_results(query, max_results=1)

    mock_search.assert_called_once_with(query=query, id_list=[], max_results=1)
    assert list(result_generator)


@patch('arxiv2text.arxiv_to_text')
@patch('arxiv.Search')
@patch('arxiv.Client')
def test_search_papers(mock_client, mock_search, mock_arxiv_to_text):
    toolkit = ArxivToolkit()
    mock_client_instance = mock_client.return_value
    mock_arxiv_to_text.return_value = "Extracted text"

    # Mock paper data
    mock_paper = MagicMock()
    mock_paper.title = "Sample Paper"
    mock_paper.updated.date.return_value.isoformat.return_value = "2024-09-01"
    mock_paper.authors = [MagicMock(name="Guohao Li")]
    mock_paper.entry_id = "1234"
    mock_paper.summary = "This is a summary."
    mock_paper.pdf_url = "http://example.com/sample.pdf"

    mock_client_instance.results.return_value = iter([mock_paper])

    query = "multi-agent"
    papers = toolkit.search_papers(query, max_results=1)

    assert len(papers) == 1
    assert papers[0]["title"] == "Sample Paper"
    assert papers[0]["paper_text"] == "Extracted text"


@patch('arxiv.Client')
@patch('arxiv.Search')
def test_download_papers(mock_search, mock_client):
    toolkit = ArxivToolkit()
    mock_client_instance = mock_client.return_value

    # Mock paper with download_pdf method and proper title
    mock_paper = MagicMock()
    mock_paper.title = "Sample Paper"
    mock_client_instance.results.return_value = iter([mock_paper])

    query = "quantum computing"
    toolkit.download_papers(query, max_results=1, output_dir="./downloads")

    mock_paper.download_pdf.assert_called_once_with(
        dirpath="./downloads", filename="Sample Paper.pdf"
    )


def test_get_tools():
    toolkit = ArxivToolkit()
    tools = toolkit.get_tools()

    assert len(tools) == 2
    assert tools[0].func == toolkit.search_papers
    assert tools[1].func == toolkit.download_papers
