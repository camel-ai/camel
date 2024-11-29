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
from camel.embeddings import OpenAIEmbedding


def test_openai_embedding():
    embedding_model = OpenAIEmbedding()
    text = "test 1."
    vector = embedding_model.embed(text)
    assert len(vector) == embedding_model.get_output_dim()

    embedding_model = OpenAIEmbedding(dimensions=256)
    text = "test 2"
    vector = embedding_model.embed(text)
    assert len(vector) == embedding_model.get_output_dim() == 256
