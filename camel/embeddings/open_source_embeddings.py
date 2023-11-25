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
from typing import Any, List

from sentence_transformers import SentenceTransformer

from camel.embeddings import BaseEmbedding


class E5LargeV2Embedding(BaseEmbedding[str]):
    r"""This class provides functionalities to generate embeddings
    using the E5-Large-V2 model from Sentence Transformers.
    """

    def __init__(self):
        r"""Initializes the E5LargeV2Embedding class with the
        specified transformer model.
        """
        self.model = SentenceTransformer('intfloat/e5-large-v2')

    def embed_list(
        self,
        objs: List[str],
        **kwargs: Any,
    ) -> List[List[float]]:
        r"""Generates embeddings for the given texts using the E5-Large-V2 model.

        Args:
            objs (List[str]): The texts for which to generate the embeddings.

        Returns:
            List[List[float]]: A list of embedding vectors.
        """
        if not objs:
            raise ValueError("Input text list is empty")
        return self.model.encode(objs, normalize_embeddings=True, **kwargs)

    def get_output_dim(self) -> int:
        r"""Returns the output dimension of the E5-Large-V2 embeddings.

        Returns:
            int: The dimensionality of the embedding for the E5-Large-V2 model.
        """
        return self.model.get_sentence_embedding_dimension()
