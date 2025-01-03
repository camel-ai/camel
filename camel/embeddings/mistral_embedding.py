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
from __future__ import annotations

import os
from typing import Any

from camel.embeddings.base import BaseEmbedding
from camel.types import EmbeddingModelType
from camel.utils import api_keys_required


class MistralEmbedding(BaseEmbedding[str]):
    r"""Provides text embedding functionalities using Mistral's models.

    Args:
        model_type (EmbeddingModelType, optional): The model type to be
            used for text embeddings.
            (default: :obj:`MISTRAL_EMBED`)
        api_key (str, optional): The API key for authenticating with the
            Mistral service. (default: :obj:`None`)
        dimensions (int, optional): The text embedding output dimensions.
            (default: :obj:`None`)

    Raises:
        RuntimeError: If an unsupported model type is specified.
    """

    @api_keys_required(
        [
            ("api_key", 'MISTRAL_API_KEY'),
        ]
    )
    def __init__(
        self,
        model_type: EmbeddingModelType = (EmbeddingModelType.MISTRAL_EMBED),
        api_key: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        from mistralai import Mistral

        if not model_type.is_mistral:
            raise ValueError("Invalid Mistral embedding model type.")
        self.model_type = model_type
        if dimensions is None:
            self.output_dim = model_type.output_dim
        else:
            assert isinstance(dimensions, int)
            self.output_dim = dimensions
        self._api_key = api_key or os.environ.get("MISTRAL_API_KEY")
        self._client = Mistral(api_key=self._api_key)

    def embed_list(
        self,
        objs: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        r"""Generates embeddings for the given texts.

        Args:
            objs (list[str]): The texts for which to generate the embeddings.
            **kwargs (Any): Extra kwargs passed to the embedding API.

        Returns:
            list[list[float]]: A list that represents the generated embedding
                as a list of floating-point numbers.
        """
        # TODO: count tokens
        response = self._client.embeddings.create(
            inputs=objs,
            model=self.model_type.value,
            **kwargs,
        )
        return [data.embedding for data in response.data]  # type: ignore[misc,union-attr]

    def get_output_dim(self) -> int:
        r"""Returns the output dimension of the embeddings.

        Returns:
            int: The dimensionality of the embedding for the current model.
        """
        return self.output_dim
