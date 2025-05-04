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
from typing import Any, Optional

from camel.embeddings.base import BaseEmbedding
from camel.types import EmbeddingModelType, GeminiEmbeddingTaskType
from camel.utils import api_keys_required


class GeminiEmbedding(BaseEmbedding[str]):
    r"""Provides text embedding functionalities using Google's Gemini models.

    Args:
        model_type (EmbeddingModelType, optional): The model type to be
            used for text embeddings.
            (default: :obj:`GEMINI_EMBEDDING_EXP`)
        api_key (str, optional): The API key for authenticating with the
            Gemini service. (default: :obj:`None`)
        dimensions (int, optional): The text embedding output dimensions.
            (default: :obj:`None`)
        task_type (GeminiEmbeddingTaskType, optional): The task type for which
            to optimize the embeddings. (default: :obj:`None`)

    Raises:
        RuntimeError: If an unsupported model type is specified.
    """

    @api_keys_required(
        [
            ("api_key", 'GEMINI_API_KEY'),
        ]
    )
    def __init__(
        self,
        model_type: EmbeddingModelType = (
            EmbeddingModelType.GEMINI_EMBEDDING_EXP
        ),
        api_key: Optional[str] = None,
        dimensions: Optional[int] = None,
        task_type: Optional[GeminiEmbeddingTaskType] = None,
    ) -> None:
        from google import genai

        if not model_type.is_gemini:
            raise ValueError("Invalid Gemini embedding model type.")

        self.model_type = model_type
        if dimensions is None:
            self.output_dim = model_type.output_dim
        else:
            assert isinstance(dimensions, int)
            self.output_dim = dimensions

        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._task_type = task_type

        # Initialize Gemini client
        self._client = genai.Client(api_key=self._api_key)

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
        from google.genai import types

        # Create embedding config if task_type is specified
        embed_config = None
        if self._task_type:
            embed_config = types.EmbedContentConfig(
                task_type=self._task_type.value
            )

        # Process each text separately since Gemini API
        # expects single content item
        responses = self._client.models.embed_content(
            model=self.model_type.value,
            contents=objs,  # type: ignore[arg-type]
            config=embed_config,
            **kwargs,
        )

        return [response.values for response in responses.embeddings]  # type: ignore[misc,union-attr]

    def get_output_dim(self) -> int:
        r"""Returns the output dimension of the embeddings.

        Returns:
            int: The dimensionality of the embedding for the current model.
        """
        return self.output_dim
