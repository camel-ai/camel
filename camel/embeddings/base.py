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
from abc import ABC, abstractmethod
from typing import Any, Generic, List, TypeVar

T = TypeVar('T')


class BaseEmbedding(ABC, Generic[T]):
    r"""Abstract base class for text embedding functionalities."""

    @abstractmethod
    def embed_list(
        self,
        objs: List[T],
        **kwargs: Any,
    ) -> List[List[float]]:
        r"""Generates embeddings for the given texts.

        Args:
            objs (List[T]): The objects for which to generate the embeddings.
            **kwargs (Any): Extra kwargs passed to the embedding API.

        Returns:
            List[List[float]]: A list that represents the
            generated embedding as a list of floating-point numbers or a
            numpy matrix with embeddings.
        """
        pass

    def embed(
        self,
        obj: T,
        **kwargs: Any,
    ) -> List[float]:
        r"""Generates an embedding for the given text.

        Args:
            obj (T): The object for which to generate the embedding.
            **kwargs (Any): Extra kwargs passed to the embedding API.

        Returns:
            List[float]: A list of floating-point numbers representing the
                generated embedding.
        """
        return self.embed_list([obj], **kwargs)[0]

    @abstractmethod
    def get_output_dim(self) -> int:
        r"""Returns the output dimension of the embeddings.

        Returns:
            int: The dimensionality of the embedding for the current model.
        """
        pass
