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
from typing import Any, Union

from openai import AzureOpenAI

from camel.embeddings.base import BaseEmbedding
from camel.types import EmbeddingModelType
from camel.utils import api_keys_required  # Add this import


class AzureEmbedding(BaseEmbedding[str]):
    r"""Provides text embedding functionalities using Azure's OpenAI models.

    Args:
        model_type (EmbeddingModelType, optional): The model type to be
            used for text embeddings.
            (default: :obj:`TEXT_EMBEDDING_3_SMALL`)
        url (Optional[str], optional): The url to the Azure OpenAI service.
            (default: :obj:`None`)
        api_key (str, optional): The API key for authenticating with the
            Azure OpenAI service. (default: :obj:`None`)
        api_version (str, optional): The API version for Azure OpenAI service.
            (default: :obj:`None`)
        dimensions (Optional[int], optional): The text embedding output
            dimensions. (default: :obj:`None`)

    Raises:
        RuntimeError: If an unsupported model type is specified.
        ValueError: If required API configuration is missing.
    """

    @api_keys_required(
        [
            ("api_key", 'AZURE_OPENAI_API_KEY'),
            ("url", 'AZURE_OPENAI_BASE_URL'),
        ]
    )
    def __init__(
        self,
        model_type: EmbeddingModelType = (
            EmbeddingModelType.TEXT_EMBEDDING_3_SMALL
        ),
        url: Union[str, None] = None,
        api_key: Union[str, None] = None,
        api_version: Union[str, None] = None,
        dimensions: Union[int, None] = None,
    ) -> None:
        self.model_type = model_type
        self.api_version = api_version or os.environ.get("AZURE_API_VERSION")
        if dimensions is None:
            self.output_dim = model_type.output_dim
        else:
            if not isinstance(dimensions, int):
                raise ValueError("dimensions must be an integer")
            self.output_dim = dimensions

        self._api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        self._url = url or os.environ.get("AZURE_OPENAI_BASE_URL")

        self.client = AzureOpenAI(
            api_key=self._api_key,
            api_version=self.api_version,
            azure_endpoint=str(self._url),
        )

    def embed_list(
        self,
        objs: list[str],
        **kwargs: Any,
    ) -> list[list[float]]:
        r"""Embeds a list of texts using the Azure OpenAI model.

        Args:
            objs (list[str]): The list of texts to embed.
            **kwargs (Any): Additional keyword arguments to pass to the API.

        Returns:
            list[list[float]]: The embeddings for the input texts.
        """
        if self.model_type == EmbeddingModelType.TEXT_EMBEDDING_ADA_2:
            response = self.client.embeddings.create(
                input=objs,
                model=self.model_type.value,
                **kwargs,
            )
            return [data.embedding for data in response.data]

        response = self.client.embeddings.create(
            input=objs,
            model=self.model_type.value,
            dimensions=self.output_dim,
            **kwargs,
        )
        return [data.embedding for data in response.data]

    def get_output_dim(self) -> int:
        r"""Returns the output dimension of the embeddings.

        Returns:
            int: The dimensionality of the embedding for the current model.
        """
        return self.output_dim
