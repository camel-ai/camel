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
Tests that @dependencies_required is correctly applied to embedding classes.
When a required package is unavailable, calling __init__ should raise
ImportError before any API key check occurs.
"""

from unittest.mock import patch

import pytest


def _mock_missing(module_name: str):
    """Patch is_module_available to return False for a specific module."""
    original = __import__(
        'camel.utils.commons', fromlist=['is_module_available']
    ).is_module_available

    def fake(m):
        if m == module_name:
            return False
        return original(m)

    return patch('camel.utils.commons.is_module_available', side_effect=fake)


def test_openai_embedding_missing_dependency():
    from camel.embeddings import OpenAIEmbedding

    with _mock_missing('openai'):
        with pytest.raises(ImportError, match="openai"):
            OpenAIEmbedding()


def test_jina_embedding_missing_dependency():
    from camel.embeddings import JinaEmbedding

    with _mock_missing('requests'):
        with pytest.raises(ImportError, match="requests"):
            JinaEmbedding()


def test_mistral_embedding_missing_dependency():
    from camel.embeddings import MistralEmbedding

    with _mock_missing('mistralai'):
        with pytest.raises(ImportError, match="mistralai"):
            MistralEmbedding()


def test_together_embedding_missing_dependency():
    from camel.embeddings import TogetherEmbedding

    with _mock_missing('openai'):
        with pytest.raises(ImportError, match="openai"):
            TogetherEmbedding()


def test_azure_embedding_missing_dependency():
    from camel.embeddings import AzureEmbedding

    with _mock_missing('openai'):
        with pytest.raises(ImportError, match="openai"):
            AzureEmbedding()


def test_gemini_embedding_missing_dependency():
    from camel.embeddings import GeminiEmbedding

    with _mock_missing('google.genai'):
        with pytest.raises(ImportError, match=r"google\.genai"):
            GeminiEmbedding()


def test_openai_compatible_embedding_missing_dependency():
    from camel.embeddings import OpenAICompatibleEmbedding

    with _mock_missing('openai'):
        with pytest.raises(ImportError, match="openai"):
            OpenAICompatibleEmbedding(
                model_type="text-embed",
            )


def test_sentence_transformer_missing_dependency():
    from camel.embeddings import SentenceTransformerEncoder

    with _mock_missing('sentence_transformers'):
        with pytest.raises(ImportError, match="sentence_transformers"):
            SentenceTransformerEncoder()


def test_vlm_embedding_missing_dependency():
    from camel.embeddings import VisionLanguageEmbedding

    with _mock_missing('transformers'):
        with pytest.raises(ImportError, match="transformers"):
            VisionLanguageEmbedding()
