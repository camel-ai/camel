# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import numpy as np
import pytest
from sentence_transformers import SentenceTransformer  # type: ignore

from camel.embeddings import SentenceTransformerEmbedding


def test_e5_large_v2_embedding_initialization():
    embedding = SentenceTransformerEmbedding()
    assert embedding is not None
    assert isinstance(embedding.model, SentenceTransformer)


def test_embed_list_with_valid_input():
    embedding = SentenceTransformerEmbedding()
    test_texts = ['Hello world', 'Testing sentence embeddings']
    embeddings = embedding.embed_list(test_texts)
    assert isinstance(embeddings, np.ndarray)
    assert len(embeddings) == 2
    for e in embeddings:
        assert len(e) == embedding.get_output_dim()


def test_embed_list_with_empty_input():
    embedding = SentenceTransformerEmbedding()
    with pytest.raises(ValueError):
        embedding.embed_list([])


def test_get_output_dim():
    embedding = SentenceTransformerEmbedding()
    output_dim = embedding.get_output_dim()
    assert isinstance(output_dim, int)
    assert output_dim > 0
