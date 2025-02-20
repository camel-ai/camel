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
