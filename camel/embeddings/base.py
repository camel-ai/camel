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
from typing import List

class BaseEmbeddings(ABC):
    r"""Base class for embedding models in CAMEL system.

    Args:
        texts (List[str]): List of texts to be embedded.

    """
    texts: List[str]

    @abstractmethod
    def embed_documents(self) -> List[List[float]]:
        r"""Abstract method for embedding documents.

        Returns:
            List[List[float]]: The embedded documents as a list of vectors.
        """
        pass

    @abstractmethod
    def embed_query(self) -> List[float]:
        r"""Abstract method for embedding a query text.

        Returns:
            List[float]: The embedded query as a vector.
        """
        pass

    def to_dict(self) -> Dict:
        r"""Converts the inputs to a dictionary.

        Returns:
            dict: The converted dictionary.
        """
        return {
            "texts": self.texts,
        }
