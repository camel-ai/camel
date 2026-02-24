# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import os
from unittest.mock import MagicMock, patch

import pytest

from camel.retrievers import JinaRerankRetriever


def test_initialization():
    with patch.dict(os.environ, {"JINA_API_KEY": "test_key"}):
        retriever = JinaRerankRetriever()
        assert retriever.model_name == "jina-reranker-v2-base-multilingual"
        assert retriever.api_key == "test_key"


def test_initialization_with_custom_model():
    with patch.dict(os.environ, {"JINA_API_KEY": "test_key"}):
        retriever = JinaRerankRetriever(model_name="jina-reranker-v1-base-en")
        assert retriever.model_name == "jina-reranker-v1-base-en"


def test_initialization_without_api_key():
    with patch.dict(os.environ, {}, clear=True):
        # Remove the JINA_API_KEY if it exists
        os.environ.pop("JINA_API_KEY", None)
        with pytest.raises(ValueError, match="Must pass in Jina API key"):
            JinaRerankRetriever()


def test_initialization_with_explicit_api_key():
    retriever = JinaRerankRetriever(api_key="explicit_key")
    assert retriever.api_key == "explicit_key"


@pytest.fixture
def jina_rerank():
    return JinaRerankRetriever(api_key="test_key")


@pytest.fixture
def mock_retrieved_result():
    return [
        {
            'similarity score': 0.85,
            'content path': "/path/to/doc1.pdf",
            'metadata': {
                'filetype': 'application/pdf',
                'page_number': 1,
            },
            'text': """CAMEL is a framework for building multi-agent systems.
            It provides tools for creating autonomous AI agents that can
            collaborate and communicate effectively.""",
        },
        {
            'similarity score': 0.75,
            'content path': "/path/to/doc2.pdf",
            'metadata': {
                'filetype': 'application/pdf',
                'page_number': 5,
            },
            'text': """The weather today is sunny with a high of 75 degrees.
            Perfect conditions for outdoor activities.""",
        },
        {
            'similarity score': 0.70,
            'content path': "/path/to/doc3.pdf",
            'metadata': {
                'filetype': 'application/pdf',
                'page_number': 10,
            },
            'text': """Developing aligned AI systems is crucial for achieving
            desired objectives while avoiding unintended consequences.
            Research in AI alignment focuses on safety and ethics.""",
        },
    ]


@patch('requests.post')
def test_query(mock_post, jina_rerank, mock_retrieved_result):
    # Create mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"index": 2, "relevance_score": 0.95},
            {"index": 0, "relevance_score": 0.88},
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    query = "AI alignment and safety research"
    result = jina_rerank.query(
        query=query, retrieved_result=mock_retrieved_result, top_k=2
    )

    # Verify the request was called correctly
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "https://api.jina.ai/v1/rerank"
    assert call_args[1]["headers"]["Authorization"] == "Bearer test_key"
    assert call_args[1]["json"]["query"] == query
    assert call_args[1]["json"]["top_n"] == 2
    assert (
        call_args[1]["json"]["model"] == "jina-reranker-v2-base-multilingual"
    )

    # Verify results
    assert len(result) == 2
    assert result[0]["similarity score"] == 0.95
    assert "AI alignment" in result[0]["text"]
    assert result[1]["similarity score"] == 0.88
    assert "CAMEL" in result[1]["text"]


@patch('requests.post')
def test_query_with_content_key(mock_post, jina_rerank):
    # Test with 'content' key instead of 'text'
    retrieved_result = [
        {'content': 'Document about machine learning', 'id': 1},
        {'content': 'Document about deep learning', 'id': 2},
    ]

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"index": 0, "relevance_score": 0.9}]
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    result = jina_rerank.query(
        query="machine learning", retrieved_result=retrieved_result, top_k=1
    )

    assert len(result) == 1
    assert result[0]["similarity score"] == 0.9


@patch('requests.post')
def test_query_default_top_k(mock_post, jina_rerank, mock_retrieved_result):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"index": 0, "relevance_score": 0.85}]
    }
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value = mock_response

    # Don't pass top_k, should default to 1
    result = jina_rerank.query(
        query="test query", retrieved_result=mock_retrieved_result
    )

    call_args = mock_post.call_args
    assert call_args[1]["json"]["top_n"] == 1
    assert len(result) == 1
