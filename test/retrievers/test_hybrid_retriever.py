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
from unittest.mock import MagicMock

import pytest

from camel.loaders.unstructured_io import UnstructuredIO
from camel.retrievers.hybrid_retrival import HybridRetriever


@pytest.fixture
def mock_hybrid_retriever(monkeypatch):
    mock_element = UnstructuredIO.create_element_from_text(text='mock element')
    monkeypatch.setattr(os.path, 'exists', MagicMock(return_value=True))
    monkeypatch.setattr(
        UnstructuredIO,
        'parse_file_or_url',
        MagicMock(return_value=[mock_element]),
    )
    # Create an instance of HybridRetriever
    hybrid_retriever = HybridRetriever()
    hybrid_retriever.process(content_input_path="https://mock.com")
    # Mock bm25_retriever.query
    hybrid_retriever.bm25.query = MagicMock(
        return_value=[
            {'text': 'Document 2', 'similarity score': 0.7},
            {'text': 'Document 3', 'similarity score': 0.6},
        ]
    )
    # Mock auto_retriever.run_vector_retriever
    hybrid_retriever.vr.query = MagicMock(
        return_value=[
            {'text': 'Document 1', 'similarity score': 0.9},
            {'text': 'Document 2', 'similarity score': 0.8},
        ]
    )
    return hybrid_retriever


def test_sort_rrf_scores_integration(mock_hybrid_retriever):
    # Call the method that integrates _sort_rrf_scores
    # This is a hypothetical method that would use _sort_rrf_scores internally
    results = mock_hybrid_retriever.query(
        query="some query about document 1", top_k=2, return_detailed_info=True
    )

    # Verify the results after _sort_rrf_scores
    assert len(results['Retrieved Context']) == 2
    assert results['Retrieved Context'][0]['text'] == 'Document 2'
    assert results['Retrieved Context'][1]['text'] == 'Document 1'


def test_query_with_reranker(mock_hybrid_retriever):
    # A mock reranker that reverses the fused order and returns top_k items.
    def _rerank(query, retrieved_result, top_k):
        reranked = list(reversed(retrieved_result))[:top_k]
        for i, item in enumerate(reranked):
            item['similarity score'] = 1.0 - i * 0.1
        return reranked

    reranker = MagicMock()
    reranker.query = MagicMock(side_effect=_rerank)

    results = mock_hybrid_retriever.query(
        query="some query about document 1",
        top_k=2,
        return_detailed_info=True,
        reranker=reranker,
    )

    # Reranker must have been invoked once with the fused candidates.
    reranker.query.assert_called_once()
    _, kwargs = reranker.query.call_args
    assert kwargs['top_k'] == 2

    # The reranker receives the full fused candidate pool (Document 2,
    # Document 1, Document 3 by RRF), reverses it, and returns the top 2.
    _, kwargs = reranker.query.call_args
    assert len(kwargs['retrieved_result']) == 3

    # Final order should reflect the reranker's reordering, not the raw RRF.
    context = results['Retrieved Context']
    assert len(context) == 2
    assert context[0]['text'] == 'Document 3'
    assert context[1]['text'] == 'Document 1'


def test_default_bm25_top_k_with_small_corpus(monkeypatch):
    r"""The default ``bm25_retriever_top_k`` is 50; querying a corpus
    with fewer chunks than that must still work instead of raising a
    ``ValueError`` from ``np.argpartition``."""

    class _FakeVectorRetriever:
        def __init__(self, embedding_model=None, vector_storage=None):
            pass

        def query(self, query, top_k, similarity_threshold):
            return [{'text': 'gamma document', 'similarity score': 0.9}]

    monkeypatch.setattr(
        'camel.retrievers.hybrid_retrival.VectorRetriever',
        _FakeVectorRetriever,
    )

    chunks = [
        UnstructuredIO.create_element_from_text(
            text=text, filename=f'{name}.txt'
        )
        for text, name in (
            ('alpha document', 'alpha'),
            ('beta document', 'beta'),
            ('gamma document', 'gamma'),
        )
    ]
    monkeypatch.setattr(
        UnstructuredIO,
        'parse_file_or_url',
        MagicMock(return_value=chunks),
    )

    hybrid_retriever = HybridRetriever()
    hybrid_retriever.bm25.process(content_input_path="https://mock.com")
    # chunk_by_title may merge the elements; what matters is that the
    # corpus is far smaller than the default bm25_retriever_top_k=50.
    assert 1 <= len(hybrid_retriever.bm25.chunks) < 50

    results = hybrid_retriever.query(
        query="alpha", top_k=2, return_detailed_info=True
    )
    # The BM25 corpus is smaller than the default
    # bm25_retriever_top_k=50, so every chunk is a candidate alongside
    # the vector result and the fused output is truncated to top_k.
    assert len(results['Retrieved Context']) == 2
