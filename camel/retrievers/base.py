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
    def process_and_store(self, content_input_path: str,
                          **kwargs: Any) -> None:
        r"""
        Processes content and stores it. Subclasses should implement this
        method according to their specific needs.

        Args:
            content_input_path (str): The path or URL of the content to
                process.
            **kwargs (Any): Flexible keyword arguments for additional
                parameters.
        """
        pass

    @abstractmethod
    def query_and_compile_results(self, query: str,
                                  top_k: int = DEFAULT_TOP_K_RESULTS,
                                  **kwargs: Any) -> List[Dict[str, Any]]:
        r"""Queries and compiles results. Subclasses should implement this
        method according to their specific needs.

        Args:
            query (str): Query string for information retriever.
            top_k (int, optional): The number of top results to return during
                retriever. Must be a positive integer. Defaults to
                `DEFAULT_TOP_K_RESULTS`.
            **kwargs (Any): Flexible keyword arguments for additional
                parameters, like `similarity_threshold`.
        """
        pass
