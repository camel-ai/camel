# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from abc import abstractmethod
from typing import Any, Dict, List

from camel.retrievers.base import BaseRetriever

DEFAULT_TOP_K_RESULTS = 1


class BaseRerankRetriever(BaseRetriever):
    r"""Abstract base class for re-ranking retrievers.

    A re-ranking retriever takes a query together with a list of already
    retrieved results (for example, the output of a :class:`VectorRetriever`,
    a :class:`BM25Retriever`, or a :class:`HybridRetriever`) and re-orders
    those results by their semantic relevance to the query, typically using a
    cross-encoder or a dedicated re-ranking API.

    Unlike first-stage retrievers, re-rankers do not ingest content, so the
    :meth:`process` method is not required and is left unimplemented.
    """

    @abstractmethod
    def query(
        self,
        query: str,
        retrieved_result: List[Dict[str, Any]],
        top_k: int = DEFAULT_TOP_K_RESULTS,
    ) -> List[Dict[str, Any]]:
        r"""Re-ranks the given retrieved results against the query.

        Args:
            query (str): The query string used for re-ranking.
            retrieved_result (List[Dict[str, Any]]): The content to be
                re-ranked, typically the output of a first-stage retriever.
                Each item should contain a ``'text'`` entry.
            top_k (int, optional): The number of top results to return after
                re-ranking. Must be a positive integer. (default:
                :obj:`DEFAULT_TOP_K_RESULTS`)

        Returns:
            List[Dict[str, Any]]: The re-ranked results, each containing the
                original data plus an updated ``'similarity score'``.
        """
        raise NotImplementedError
