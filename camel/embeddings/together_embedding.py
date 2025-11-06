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
import os
from typing import Any, Optional

from openai import OpenAI

from camel.embeddings.base import BaseEmbedding
from camel.logger import get_logger
from camel.utils import api_keys_required

logger = get_logger(__name__)


class TogetherEmbedding(BaseEmbedding[str]):
    r"""Provides text embedding functionalities using Together AI's models.

    Args:
        model_type (str, optional): The model name to be used for text
            embeddings.
            (default: :obj:`togethercomputer/m2-bert-80M-8k-retrieval`)
        api_key (str, optional): The API key for authenticating with the
            Together service. (default: :obj:`None`)
        dimensions (int, optional): The text embedding output dimensions.
            (default: :obj:`None`)

    Raises:
        ValueError: If the model name format is invalid or if an empty input
            list is provided.
        RuntimeError: If the API request fails.
    """

    @api_keys_required([("api_key", 'TOGETHER_API_KEY')])
    def __init__(
        self,
        model_type: str = "togethercomputer/m2-bert-80M-8k-retrieval",
        api_key: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> None:
        if not isinstance(model_type, str) or not model_type.strip():
            raise ValueError("Model name must be a non-empty string")

        if dimensions is not None and dimensions <= 0:
            raise ValueError("Dimensions must be a positive integer")

        self.model_type = model_type
        self._api_key = api_key or os.environ.get("TOGETHER_API_KEY")
        self.output_dim = dimensions

        # Initialize OpenAI client with Together AI configuration
        self.client = OpenAI(
            timeout=180,
            max_retries=3,
            api_key=self._api_key,
            base_url="https://api.together.xyz/v1",
        )

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

        Raises:
            ValueError: If the input list is empty.
            RuntimeError: If the API request fails.
        """
        if not objs:
            raise ValueError("Input list cannot be empty")

        try:
            response = self.client.embeddings.create(
                input=objs,
                model=self.model_type,
                **kwargs,
            )

            # Set output dimension if not already set
            if self.output_dim is None and response.data:
                self.output_dim = len(response.data[0].embedding)
                logger.debug(
                    f"Set output dimension to {self.output_dim} for model "
                    f"{self.model_type}"
                )

            return [data.embedding for data in response.data]

        except Exception as e:
            raise RuntimeError(
                f"Failed to get embeddings from Together AI: {e}"
            )

    def get_output_dim(self) -> int:
        r"""Returns the output dimension of the embeddings.

        Returns:
            int: The dimensionality of the embedding for the current model.

        Raises:
            ValueError: If the embedding dimension cannot be determined.
        """
        if self.output_dim is None:
            logger.debug(
                "Output dimension not set, "
                "making test embedding to determine it"
            )
            # Make a test embedding to determine the dimension
            self.embed_list(["test"])

        if self.output_dim is None:
            raise ValueError(
                "Failed to determine embedding dimension for model: "
                f"{self.model_type}"
            )

        return self.output_dim
