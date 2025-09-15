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
from typing import Any, Collection, Dict, List, Optional, Sequence, Union

from camel.embeddings import BaseEmbedding
from camel.retrievers import BaseRetriever, BM25Retriever, VectorRetriever
from camel.storages import BaseVectorStorage


class HybridRetriever(BaseRetriever):
    def __init__(
        self,
        embedding_model: Optional[BaseEmbedding] = None,
        vector_storage: Optional[BaseVectorStorage] = None,
    ) -> None:
        r"""Initializes the HybridRetriever with optional embedding model and
        vector storage.

        Args:
            embedding_model (Optional[BaseEmbedding]): An optional embedding
                model used by the VectorRetriever. Defaults to None.
            vector_storage (Optional[BaseVectorStorage]): An optional vector
                storage used by the VectorRetriever. Defaults to None.
        """
        self.vr = VectorRetriever(embedding_model, vector_storage)
        self.bm25 = BM25Retriever()

    def process(self, content_input_path: str) -> None:
        r"""Processes the content input path for both vector and BM25
        retrievers.

        Args:
            content_input_path (str): File path or URL of the content to be
                processed.

        Raises:
            ValueError: If the content_input_path is empty.
        """
        if not content_input_path:
            raise ValueError("content_input_path cannot be empty.")

        self.content_input_path = content_input_path
        self.vr.process(content=self.content_input_path)
        self.bm25.process(content_input_path=self.content_input_path)

    def _sort_rrf_scores(
        self,
        vector_retriever_results: List[Dict[str, Any]],
        bm25_retriever_results: List[Dict[str, Any]],
        top_k: int,
        vector_weight: float,
        bm25_weight: float,
        rank_smoothing_factor: float,
    ) -> List[Dict[str, Union[str, float]]]:
        r"""Sorts and combines results from vector and BM25 retrievers using
        Reciprocal Rank Fusion (RRF).

        Args:
            vector_retriever_results: A list of dictionaries containing the
                results from the vector retriever, where each dictionary
                contains a 'text' entry.
            bm25_retriever_results: A list of dictionaries containing the
                results from the BM25 retriever, where each dictionary
                contains a 'text' entry.
            top_k: The number of top results to return after sorting by RRF
                score.
            vector_weight: The weight to assign to the vector retriever
                results in the RRF calculation.
            bm25_weight: The weight to assign to the BM25 retriever results in
                the RRF calculation.
            rank_smoothing_factor: A hyperparameter for the RRF calculation
                that helps smooth the rank positions.

        Returns:
            List[Dict[str, Union[str, float]]]: A list of dictionaries
            representing the sorted results. Each dictionary contains the
            'text'from the retrieved items and their corresponding 'rrf_score'.

        Raises:
            ValueError: If any of the input weights are negative.

        References:
            https://medium.com/@devalshah1619/mathematical-intuition-behind-reciprocal-rank-fusion-rrf-explained-in-2-mins-002df0cc5e2a
            https://colab.research.google.com/drive/1iwVJrN96fiyycxN1pBqWlEr_4EPiGdGy#scrollTo=0qh83qGV2dY8
        """
        import numpy as np

        text_to_id = {}
        id_to_info = {}
        current_id = 1

        # Iterate over vector_retriever_results
        for rank, result in enumerate(vector_retriever_results, start=1):
            text = result.get('text', None)  # type: ignore[attr-defined]
            if text is None:
                raise KeyError("Each result must contain a 'text' key")

            if text not in text_to_id:
                text_to_id[text] = current_id
                id_to_info[current_id] = {'text': text, 'vector_rank': rank}
                current_id += 1
            else:
                id_to_info[text_to_id[text]]['vector_rank'] = rank

        # Iterate over bm25_retriever_results
        for rank, result in enumerate(bm25_retriever_results, start=1):
            text = result['text']
            if text not in text_to_id:
                text_to_id[text] = current_id
                id_to_info[current_id] = {'text': text, 'bm25_rank': rank}
                current_id += 1
            else:
                id_to_info[text_to_id[text]].setdefault('bm25_rank', rank)

        vector_ranks = np.array(
            [
                info.get('vector_rank', float('inf'))
                for info in id_to_info.values()
            ]
        )
        bm25_ranks = np.array(
            [
                info.get('bm25_rank', float('inf'))
                for info in id_to_info.values()
            ]
        )

        # Calculate RRF scores
        vector_rrf_scores = vector_weight / (
            rank_smoothing_factor + vector_ranks
        )
        bm25_rrf_scores = bm25_weight / (rank_smoothing_factor + bm25_ranks)
        rrf_scores = vector_rrf_scores + bm25_rrf_scores

        for idx, (_, info) in enumerate(id_to_info.items()):
            info['rrf_score'] = rrf_scores[idx]
        sorted_results = sorted(
            id_to_info.values(), key=lambda x: x['rrf_score'], reverse=True
        )
        return sorted_results[:top_k]

    def query(
        self,
        query: str,
        top_k: int = 20,
        vector_weight: float = 0.8,
        bm25_weight: float = 0.2,
        rank_smoothing_factor: int = 60,
        vector_retriever_top_k: int = 50,
        vector_retriever_similarity_threshold: float = 0.5,
        bm25_retriever_top_k: int = 50,
        return_detailed_info: bool = False,
    ) -> Union[
        dict[str, Sequence[Collection[str]]],
        dict[str, Sequence[Union[str, float]]],
    ]:
        r"""Executes a hybrid retrieval query using both vector and BM25
        retrievers.

        Args:
            query (str): The search query.
            top_k (int): Number of top results to return (default 20).
            vector_weight (float): Weight for vector retriever results in RRF.
            bm25_weight (float): Weight for BM25 retriever results in RRF.
            rank_smoothing_factor (int): RRF hyperparameter for rank smoothing.
            vector_retriever_top_k (int): Top results from vector retriever.
            vector_retriever_similarity_threshold (float): Similarity
                threshold for vector retriever.
            bm25_retriever_top_k (int): Top results from BM25 retriever.
            return_detailed_info (bool): Return detailed info if True.

        Returns:
            Union[
                dict[str, Sequence[Collection[str]]],
                dict[str, Sequence[Union[str, float]]]
            ]: By default, returns only the text information. If
                `return_detailed_info` is `True`, return detailed information
                including rrf scores.
        """
        if top_k > max(vector_retriever_top_k, bm25_retriever_top_k):
            raise ValueError(
                "top_k needs to be less than or equal to the "
                "maximum value among vector_retriever_top_k and "
                "bm25_retriever_top_k."
            )
        if vector_weight < 0 or bm25_weight < 0:
            raise ValueError(
                "Neither `vector_weight` nor `bm25_weight` can be negative."
            )

        vr_raw_results: List[Dict[str, Any]] = self.vr.query(
            query=query,
            top_k=vector_retriever_top_k,
            similarity_threshold=vector_retriever_similarity_threshold,
        )
        # if the number of results is less than top_k, return all results
        with_score = [
            info for info in vr_raw_results if 'similarity score' in info
        ]
        vector_retriever_results = sorted(
            with_score, key=lambda x: x['similarity score'], reverse=True
        )

        bm25_retriever_results = self.bm25.query(
            query=query,
            top_k=bm25_retriever_top_k,
        )

        all_retrieved_info = self._sort_rrf_scores(
            vector_retriever_results,
            bm25_retriever_results,
            top_k,
            vector_weight,
            bm25_weight,
            rank_smoothing_factor,
        )

        retrieved_info = {
            "Original Query": query,
            "Retrieved Context": (
                all_retrieved_info
                if return_detailed_info
                else [item['text'] for item in all_retrieved_info]  # type: ignore[misc]
            ),
        }
        return retrieved_info
