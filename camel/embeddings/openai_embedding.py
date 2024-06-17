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
import os
from typing import Any, List, Optional

from openai import OpenAI

from camel.embeddings.base import BaseEmbedding
from camel.types import EmbeddingModelType
from camel.utils import model_api_key_required


class OpenAIEmbedding(BaseEmbedding[str]):
    r"""Provides text embedding functionalities using OpenAI's models.

    Args:
        model (OpenAiEmbeddingModel, optional): The model type to be used for
            generating embeddings. (default: :obj:`ModelType.ADA_2`)
        api_key (Optional[str]): The API key for authenticating with the
            OpenAI service. (default: :obj:`None`)

    Raises:
        RuntimeError: If an unsupported model type is specified.
    """

    def __init__(
        self,
        model_type: EmbeddingModelType = EmbeddingModelType.ADA_2,
        api_key: Optional[str] = None,
    ) -> None:
        if not model_type.is_openai:
            raise ValueError("Invalid OpenAI embedding model type.")
        self.model_type = model_type
        self.output_dim = model_type.output_dim
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(timeout=60, max_retries=3, api_key=self._api_key)

    @model_api_key_required
    def embed_list(
        self,
        objs: List[str],
        **kwargs: Any,
    ) -> List[List[float]]:
        r"""Generates embeddings for the given texts.

        Args:
            objs (List[str]): The texts for which to generate the embeddings.
            **kwargs (Any): Extra kwargs passed to the embedding API.

        Returns:
            List[List[float]]: A list that represents the generated embedding
                as a list of floating-point numbers.
        """
        # TODO: count tokens
        response = self.client.embeddings.create(
            input=objs,
            model=self.model_type.value,
            **kwargs,
        )
        return [data.embedding for data in response.data]

    def get_output_dim(self) -> int:
        r"""Returns the output dimension of the embeddings.

        Returns:
            int: The dimensionality of the embedding for the current model.
        """
        return self.output_dim
