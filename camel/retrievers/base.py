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
from typing import Any, Dict, List

DEFAULT_TOP_K_RESULTS = 1


class BaseRetriever(ABC):
    r"""Abstract base class for implementing various types of information
    retrievers.
    """

    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def process(self, content_input_path: str,
                chunk_type: str = "chunk_by_title", **kwargs: Any) -> None:
        r"""Processes content from a file or URL, divides it into chunks by
        using `Unstructured IO`,then stored internally. This method must be
        called before executing queries with the retriever.

        Args:
            content_input_path (str): File path or URL of the content to be
                processed.
            chunk_type (str): Type of chunking going to apply. Defaults to
                "chunk_by_title".
            **kwargs (Any): Additional keyword arguments for content parsing.
        """
        pass

    @abstractmethod
    def query(self, query: str,
              top_k: int = DEFAULT_TOP_K_RESULTS) -> List[Dict[str, Any]]:
        r"""Query the results. Subclasses should implement this
        method according to their specific needs.

        Args:
            query (str): Query string for information retriever.
            top_k (int, optional): The number of top results to return during
                retriever. Must be a positive integer. Defaults to
                `DEFAULT_TOP_K_RESULTS`.
        """
        pass
