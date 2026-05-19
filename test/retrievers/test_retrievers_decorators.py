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
"""
Test that the following decorators are correctly applied to camel.retrievers:
@api_keys_required - should raise ValueError if value is missing
@dependencies_required - should raise ImportError if package/module is missing
"""

import os
from unittest.mock import patch

import pytest

fake_api_key = "fake_api_key"


def _mock_missing(module_name: str):
    """
    Patch is_module_available to return False for a specific module.
    """
    original = __import__(
        'camel.utils.commons', fromlist=['is_module_available']
    ).is_module_available

    def fake(m):
        if m == module_name:
            return False
        return original(m)

    return patch('camel.utils.commons.is_module_available', side_effect=fake)


def test_auto_retriever_missing_dependency():
    """
    Raises ImportError when specified module is in @dependencies_required
    """
    from camel.retrievers import AutoRetriever

    with _mock_missing('hashlib'):
        with pytest.raises(ImportError, match="hashlib"):
            AutoRetriever._collection_name_generator()

    with _mock_missing('os'):
        with pytest.raises(ImportError, match="os"):
            AutoRetriever._collection_name_generator()

    with _mock_missing('unstructured.documents.elements'):
        with pytest.raises(
            ImportError, match="unstructured.documents.elements"
        ):
            AutoRetriever._collection_name_generator()

    with _mock_missing('unstructured.documents.elements'):
        with pytest.raises(
            ImportError, match="unstructured.documents.elements"
        ):
            AutoRetriever.run_vector_retriever()


def test_bm25_retriever_missing_dependency():
    """
    Raises ImportError when specified module is in @dependencies_required
    """
    from camel.retrievers import BM25Retriever

    with _mock_missing('rank_bm25'):
        with pytest.raises(ImportError, match="rank_bm25"):
            BM25Retriever()

    with _mock_missing('numpy'):
        with pytest.raises(ImportError, match="numpy"):
            BM25Retriever.query()


def test_cohere_rerank_retriever_missing_dependency():
    """
    Raises ImportError when specified module is in @dependencies_required.
    Include fake_api_key if function also has an @api_keys_required decorator
    This prevents test from returning ValueError instead of expected
    Failed: DID NOT RAISE <class 'ImportError'>
    if module is not in @dependencies_required list.
    """
    from camel.retrievers import CohereRerankRetriever

    with _mock_missing('cohere'):
        with pytest.raises(ImportError, match="cohere"):
            CohereRerankRetriever(api_key=fake_api_key)


def test_hybrid_retrieval_missing_dependency():
    """
    Raises ImportError when specified module is in @dependencies_required
    """
    from camel.retrievers import HybridRetriever

    with _mock_missing('numpy'):
        with pytest.raises(ImportError, match="numpy"):
            HybridRetriever._sort_rrf_scores()


def test_jina_rerank_retriever_missing_dependency():
    """
    Raises ImportError when specified module is in @dependencies_required
    """
    from camel.retrievers import JinaRerankRetriever

    with _mock_missing('requests'):
        with pytest.raises(ImportError, match="requests"):
            JinaRerankRetriever.query()


def test_vector_retriever_missing_dependency():
    """
    Raises ImportError when specified module is in @dependencies_required
    """
    from camel.retrievers import VectorRetriever

    with _mock_missing('unstructured.documents.elements'):
        with pytest.raises(
            ImportError, match="unstructured.documents.elements"
        ):
            VectorRetriever.process()


def test_cohere_rerank_retriever_api_keys():
    """
    Patch os.environ to hold no Values, and
    Input no API keys as function arguments:
    Check ValueError is returned for specific API keys by match=.
    """
    from camel.retrievers import CohereRerankRetriever

    with patch.dict(os.environ, {}):
        with pytest.raises(ValueError, match='COHERE_API_KEY'):
            CohereRerankRetriever()


def test_jina_rerank_retriever_api_keys():
    """
    Patch os.environ to hold no Values, and
    Input no API keys as function arguments:
    Check ValueError is returned for specific API keys by match=.
    """
    from camel.retrievers import JinaRerankRetriever

    with patch.dict(os.environ, {}):
        with pytest.raises(ValueError, match='JINA_API_KEY'):
            JinaRerankRetriever()
