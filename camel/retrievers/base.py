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
from typing import Any

from camel.storages import BaseVectorStorage

DEFAULT_TOP_K_RESULTS = 1
DEFAULT_SIMILARITY_THRESHOLD = 0.75


class BaseRetriever(ABC):
    r"""An abstract base class for information retriever.

    A retriever system can return the most relevant informatiomn from source
    with the given string query.
    """

    @abstractmethod
    def process_and_store(
        self,
        content_input_path: str,
        storage: BaseVectorStorage,
        **kwargs: Any,
    ) -> None:
        r"""Process the content from a given path and store it to the storage.

        Args:
            content_input_path (str): File path or URL of the content to be
                processed.
            storage (BaseVectorStorage): Storage to store the information.
            **kwargs (Any): Additional keyword arguments.
        """
        pass

    @abstractmethod
    def query_and_compile_results(
        self,
        query: str,
        storage: BaseVectorStorage,
        top_k: int = DEFAULT_TOP_K_RESULTS,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        **kwargs: Any,
    ) -> Any:
        r"""Executes a query in storage and compiles the retrieved
        results back.

        Args:
            query (str): Query string for information retriever.
            storage (BaseVectorStorage): Storage to store the information.
            top_k (int, optional): The number of top results to return during
                retriever. Must be a positive integer. Defaults to 1.
            similarity_threshold (float, optional): The similarity threshold
                for filtering results. Defaults to 0.75.
            **kwargs (Any): Additional keyword arguments.
        """
        pass
