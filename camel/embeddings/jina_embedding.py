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

import base64
import io
import os
from typing import Any, Optional, Union

import requests
from PIL import Image

from camel.embeddings import BaseEmbedding
from camel.types.enums import EmbeddingModelType
from camel.utils import api_keys_required


class JinaEmbedding(BaseEmbedding[Union[str, Image.Image]]):
    r"""Provides text and image embedding functionalities using Jina AI's API.

    Args:
        model_type (EmbeddingModelType, optional): The model to use for
            embeddings. (default: :obj:`JINA_EMBEDDINGS_V3`)
        api_key (Optional[str], optional): The API key for authenticating with
            Jina AI. (default: :obj:`None`)
        dimensions (Optional[int], optional): The dimension of the output
            embeddings. (default: :obj:`None`)
        task (Optional[str], optional): The type of task for text embeddings.
            Options: retrieval.query, retrieval.passage, text-matching,
            classification, separation. (default: :obj:`None`)
        late_chunking (bool, optional): If true, concatenates all sentences in
            input and treats as a single input. (default: :obj:`False`)
        normalized (bool, optional): If true, embeddings are normalized to unit
            L2 norm. (default: :obj:`False`)
    """

    @api_keys_required([("api_key", 'JINA_API_KEY')])
    def __init__(
        self,
        model_type: EmbeddingModelType = EmbeddingModelType.JINA_EMBEDDINGS_V3,
        api_key: Optional[str] = None,
        dimensions: Optional[int] = None,
        embedding_type: Optional[str] = None,
        task: Optional[str] = None,
        late_chunking: bool = False,
        normalized: bool = False,
    ) -> None:
        if not model_type.is_jina:
            raise ValueError(
                f"Model type {model_type} is not a Jina model. "
                "Please use a valid Jina model type."
            )
        self.model_type = model_type
        if dimensions is None:
            self.output_dim = model_type.output_dim
        else:
            self.output_dim = dimensions
        self._api_key = api_key or os.environ.get("JINA_API_KEY")

        self.embedding_type = embedding_type
        self.task = task
        self.late_chunking = late_chunking
        self.normalized = normalized
        self.url = 'https://api.jina.ai/v1/embeddings'
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self._api_key}',
        }

    def embed_list(
        self,
        objs: list[Union[str, Image.Image]],
        **kwargs: Any,
    ) -> list[list[float]]:
        r"""Generates embeddings for the given texts or images.

        Args:
            objs (list[Union[str, Image.Image]]): The texts or images for which
                to generate the embeddings.
            **kwargs (Any): Extra kwargs passed to the embedding API. Not used
                in this implementation.

        Returns:
            list[list[float]]: A list that represents the generated embedding
                as a list of floating-point numbers.

        Raises:
            ValueError: If the input type is not supported.
            RuntimeError: If the API request fails.
        """
        input_data = []
        for obj in objs:
            if isinstance(obj, str):
                if self.model_type == EmbeddingModelType.JINA_CLIP_V2:
                    input_data.append({"text": obj})
                else:
                    input_data.append(obj)  # type: ignore[arg-type]
            elif isinstance(obj, Image.Image):
                if self.model_type != EmbeddingModelType.JINA_CLIP_V2:
                    raise ValueError(
                        f"Model {self.model_type} does not support "
                        "image input. Use JINA_CLIP_V2 for image embeddings."
                    )
                # Convert PIL Image to base64 string
                buffered = io.BytesIO()
                obj.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                input_data.append({"image": img_str})
            else:
                raise ValueError(
                    f"Input type {type(obj)} is not supported. "
                    "Must be either str or PIL.Image"
                )

        data = {
            "model": self.model_type.value,
            "input": input_data,
            "embedding_type": "float",
        }

        if self.embedding_type is not None:
            data["embedding_type"] = self.embedding_type
        if self.task is not None:
            data["task"] = self.task
        if self.late_chunking:
            data["late_chunking"] = self.late_chunking  # type: ignore[assignment]
        if self.normalized:
            data["normalized"] = self.normalized  # type: ignore[assignment]
        try:
            response = requests.post(
                self.url, headers=self.headers, json=data, timeout=180
            )
            response.raise_for_status()
            result = response.json()
            return [data["embedding"] for data in result["data"]]
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to get embeddings from Jina AI: {e}")

    def get_output_dim(self) -> int:
        r"""Returns the output dimension of the embeddings.

        Returns:
            int: The dimensionality of the embedding for the current model.
        """
        return self.output_dim
