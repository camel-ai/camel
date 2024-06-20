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

from camel.embeddings.base import BaseEmbedding


class SentenceTransformerEncoder(BaseEmbedding[str]):
    r"""This class provides functionalities to generate embeddings
    using a specified model from `Sentence Transformers`.

    References:
        https://www.sbert.net/
    """

    def __init__(self, model_name: str = 'intfloat/e5-large-v2'):
        r"""Initializes the: obj: `SentenceTransformerEmbedding` class
        with the specified transformer model.

        Args:
            model_name (str, optional): The name of the model to use.
                                        Defaults to `intfloat/e5-large-v2`.
        """
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def embed_list(
        self,
        objs: List[str],
        **kwargs: Any,
    ) -> List[List[float]]:
        r"""Generates embeddings for the given texts using the model.

        Args:
            objs (List[str]): The texts for which to generate the
            embeddings.

        Returns:
            List[List[float]]: A list that represents the generated embedding
                as a list of floating-point numbers.
        """
        if not objs:
            raise ValueError("Input text list is empty")
        return self.model.encode(
            objs, normalize_embeddings=True, **kwargs
        ).tolist()

    def get_output_dim(self) -> int:
        r"""Returns the output dimension of the embeddings.

        Returns:
            int: The dimensionality of the embeddings.
        """
        return self.model.get_sentence_embedding_dimension()
