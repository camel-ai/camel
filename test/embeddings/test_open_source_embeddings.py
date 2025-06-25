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
import pytest
from sentence_transformers import SentenceTransformer

from camel.embeddings import SentenceTransformerEncoder

pytestmark = pytest.mark.heavy_dependency


def test_SentenceTransformerEmbedding_initialization():
    embedding = SentenceTransformerEncoder()
    assert embedding is not None
    assert isinstance(embedding.model, SentenceTransformer)


def test_embed_list_with_valid_input():
    embedding = SentenceTransformerEncoder()
    test_texts = ['Hello world', 'Testing sentence embeddings']
    embeddings = embedding.embed_list(test_texts)
    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    for e in embeddings:
        assert len(e) == embedding.get_output_dim()


def test_embed_list_with_empty_input():
    embedding = SentenceTransformerEncoder()
    with pytest.raises(ValueError):
        embedding.embed_list([])


def test_get_output_dim():
    embedding = SentenceTransformerEncoder()
    output_dim = embedding.get_output_dim()
    assert isinstance(output_dim, int)
    assert output_dim > 0
