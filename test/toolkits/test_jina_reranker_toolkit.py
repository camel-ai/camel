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

from camel.toolkits.jina_reranker_toolkit import JinaRerankerToolkit

pytestmark = pytest.mark.heavy_dependency


@pytest.fixture
def mock_model():
    r"""Fixture for mocking the Jina Reranker model."""
    model = MagicMock()
    model.compute_score = MagicMock()
    return model


@pytest.fixture
def reranker_toolkit(mock_model):
    r"""Fixture for creating a JinaRerankerToolkit with a mocked model."""
    with patch(
        'transformers.AutoModel.from_pretrained', return_value=mock_model
    ):
        toolkit = JinaRerankerToolkit(use_api=False)
        # Replace the actual model with our mock
        toolkit.model = mock_model
        return toolkit


def test_init_with_default_params():
    r"""Test initialization with default parameters."""
    with patch(
        'transformers.AutoModel.from_pretrained'
    ) as mock_from_pretrained:
        with patch('torch.cuda.is_available', return_value=False):
            JinaRerankerToolkit(use_api=False)
            mock_from_pretrained.assert_called_once_with(
                'jinaai/jina-reranker-m0',
                torch_dtype="auto",
                trust_remote_code=True,
            )


def test_init_with_custom_device():
    r"""Test initialization with custom device."""
    with patch(
        'transformers.AutoModel.from_pretrained'
    ) as mock_from_pretrained:
        with patch('torch.cuda.is_available', return_value=True):
            model_mock = MagicMock()
            mock_from_pretrained.return_value = model_mock

            JinaRerankerToolkit(use_api=False, device="cpu")

            model_mock.to.assert_called_once_with("cpu")
            model_mock.eval.assert_called_once()


@pytest.mark.skip(
    reason="Skipping due to Hugging Face authentication issues in CI/CD"
)
def test_sort_documents():
    r"""Test the _sort_documents method."""
    toolkit = JinaRerankerToolkit(use_api=False)
    documents = ["doc1", "doc2", "doc3"]
    scores = [0.5, 0.9, 0.1]

    result = toolkit._sort_documents(documents, scores)

    # Should be sorted by score in descending order
    assert result == [
        {"document": "doc2", "score": 0.9},
        {"document": "doc1", "score": 0.5},
        {"document": "doc3", "score": 0.1},
    ]


@pytest.mark.skip(
    reason="Skipping due to Hugging Face authentication issues in CI/CD"
)
def test_sort_documents_with_mismatched_lengths():
    r"""Test _sort_documents with mismatched document and score lists."""
    toolkit = JinaRerankerToolkit(use_api=False)
    documents = ["doc1", "doc2"]
    scores = [0.5, 0.9, 0.1]

    with pytest.raises(
        ValueError, match="Number of documents must match number of scores"
    ):
        toolkit._sort_documents(documents, scores)


def test_rerank_text_documents(reranker_toolkit):
    r"""Test reranking text documents."""
    query = "test query"
    documents = ["doc1", "doc2", "doc3"]
    scores = [0.7, 0.3, 0.9]

    reranker_toolkit.model.compute_score.return_value = scores

    result = reranker_toolkit.rerank_text_documents(query, documents)

    # Check that compute_score was called with the correct parameters
    reranker_toolkit.model.compute_score.assert_called_once_with(
        [[query, doc] for doc in documents], max_length=1024, doc_type="text"
    )

    # Check that the result is sorted correctly
    assert result == [
        {'document': {'text': 'doc3'}, 'relevance_score': 0.9},
        {'document': {'text': 'doc1'}, 'relevance_score': 0.7},
        {'document': {'text': 'doc2'}, 'relevance_score': 0.3},
    ]


def test_rerank_text_documents_with_custom_max_length(reranker_toolkit):
    r"""Test reranking text documents with custom max_length."""
    query = "test query"
    documents = ["doc1", "doc2"]
    scores = [0.6, 0.8]

    reranker_toolkit.model.compute_score.return_value = scores

    result = reranker_toolkit.rerank_text_documents(
        query, documents, max_length=512
    )

    reranker_toolkit.model.compute_score.assert_called_once_with(
        [[query, doc] for doc in documents], max_length=512, doc_type="text"
    )

    assert result == [
        {'document': {'text': 'doc2'}, 'relevance_score': 0.8},
        {'document': {'text': 'doc1'}, 'relevance_score': 0.6},
    ]


@pytest.mark.skip(
    reason="Skipping due to Hugging Face authentication issues in CI/CD"
)
def test_rerank_text_documents_model_not_initialized():
    r"""Test reranking text documents when model is not initialized."""
    toolkit = JinaRerankerToolkit(use_api=False)
    toolkit.model = None

    with pytest.raises(
        ValueError,
        match="Model has not been initialized or failed to initialize.",
    ):
        toolkit.rerank_text_documents("query", ["doc1"])


def test_rerank_image_documents(reranker_toolkit):
    r"""Test reranking image documents."""
    query = "test query"
    documents = ["image1.jpg", "image2.jpg"]
    scores = [0.4, 0.8]

    reranker_toolkit.model.compute_score.return_value = scores

    result = reranker_toolkit.rerank_image_documents(query, documents)

    reranker_toolkit.model.compute_score.assert_called_once_with(
        [[query, doc] for doc in documents], max_length=2048, doc_type="image"
    )

    assert result == [
        {'document': {'text': 'image2.jpg'}, 'relevance_score': 0.8},
        {'document': {'text': 'image1.jpg'}, 'relevance_score': 0.4},
    ]


def test_rerank_image_documents_custom_max_length(reranker_toolkit):
    r"""Test reranking image documents with custom max_length."""
    query = "test query"
    documents = ["image1.jpg", "image2.jpg"]
    scores = [0.4, 0.8]

    reranker_toolkit.model.compute_score.return_value = scores

    result = reranker_toolkit.rerank_image_documents(
        query, documents, max_length=1024
    )

    reranker_toolkit.model.compute_score.assert_called_once_with(
        [[query, doc] for doc in documents], max_length=1024, doc_type="image"
    )

    assert result == [
        {'document': {'text': 'image2.jpg'}, 'relevance_score': 0.8},
        {'document': {'text': 'image1.jpg'}, 'relevance_score': 0.4},
    ]


def test_image_query_text_documents(reranker_toolkit):
    r"""Test reranking text documents with an image query."""
    image_query = "image_query.jpg"
    documents = ["doc1", "doc2"]
    scores = [0.3, 0.7]

    reranker_toolkit.model.compute_score.return_value = scores

    result = reranker_toolkit.image_query_text_documents(
        image_query, documents
    )

    reranker_toolkit.model.compute_score.assert_called_once_with(
        [[image_query, doc] for doc in documents],
        max_length=2048,
        query_type="image",
        doc_type="text",
    )

    assert result == [
        {'document': {'text': 'doc2'}, 'relevance_score': 0.7},
        {'document': {'text': 'doc1'}, 'relevance_score': 0.3},
    ]


def test_image_query_image_documents(reranker_toolkit):
    r"""Test reranking image documents with an image query."""
    image_query = "image_query.jpg"
    documents = ["image1.jpg", "image2.jpg"]
    scores = [0.6, 0.2]

    reranker_toolkit.model.compute_score.return_value = scores

    result = reranker_toolkit.image_query_image_documents(
        image_query, documents
    )

    reranker_toolkit.model.compute_score.assert_called_once_with(
        [[image_query, doc] for doc in documents],
        max_length=2048,
        query_type="image",
        doc_type="image",
    )

    assert result == [
        {'document': {'text': 'image1.jpg'}, 'relevance_score': 0.6},
        {'document': {'text': 'image2.jpg'}, 'relevance_score': 0.2},
    ]


def test_with_inference_mode(reranker_toolkit):
    r"""Test that torch.inference_mode is used correctly."""
    with patch('torch.inference_mode') as mock_inference_mode:
        mock_context = MagicMock()
        mock_inference_mode.return_value = mock_context

        reranker_toolkit.model.compute_score.return_value = [0.5]

        reranker_toolkit.rerank_text_documents("query", ["doc"])

        mock_inference_mode.assert_called_once()
        mock_context.__enter__.assert_called_once()
        mock_context.__exit__.assert_called_once()
