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

import numpy as np

from camel.embeddings import OpenAIEmbedding
from camel.retrievers import AutoRetriever, BM25Retriever
from camel.types import EmbeddingModelType, StorageType


class HybridRetriever:
    def __init__(
        self,
        content_input_path: str,
        auto_retriever: Optional[AutoRetriever] = None,
        bm25_process_chunk_type: Optional[str] = "chunk_by_title",
    ) -> None:
        r"""Initializes a HybridRetriever that combines the functionalities of
        AutoRetriever and BM25Retriever.

        Args:
            content_input_path (str): The path to the input content for the
                BM25Retriever to process.
            auto_retriever (Optional[AutoRetriever], optional): An instance of
                AutoRetriever. If None, a new instance is created.
            bm25_process_chunk_type (Optional[str], optional): The type of
                chunking to be used by BM25Retriever, defaults to
                "chunk_by_title".

        Raises:
            ValueError: If the content_input_path is empty.
        """
        if not content_input_path:
            raise ValueError("content_input_path cannot be empty.")

        self.content_input_path = content_input_path
        if auto_retriever is None:
            embedding_instance = OpenAIEmbedding(
                model_type=EmbeddingModelType.TEXT_EMBEDDING_3_LARGE
            )

            auto_retriever = AutoRetriever(
                vector_storage_local_path="vector_storage/",
                storage_type=StorageType.QDRANT,
                embedding_model=embedding_instance,
            )

        self.auto_retriever = auto_retriever

        self.bm25_retriever = BM25Retriever()
        self.bm25_retriever.process(
            content_input_path=content_input_path,
            chunk_type=bm25_process_chunk_type,
        )

    def _sort_rrf_scores(
        self,
        vector_retriever_results: dict[str, Sequence[Collection[str]]],
        bm25_retriever_results: List[Dict[str, Any]],
        top_k: int,
        vector_weight: float,
        bm25_weight: float,
        rank_smoothing_factor: float,
    ) -> List[Dict[str, Union[str, float]]]:
        r"""Sorts and combines results from vector and BM25 retrievers using
        Reciprocal Rank Fusion (RRF).

        Args:
            vector_retriever_results: A dictionary containing the results from
                the vector retriever, where the key 'Retrieved Context' maps
                to a sequence of collections with 'text' entries.
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
        text_to_id = {}
        id_to_info = {}
        current_id = 1

        # Iterate over vector_retriever_results
        for rank, result in enumerate(
            vector_retriever_results['Retrieved Context'], start=1
        ):
            text = result['text']
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
        vector_retriever_max_characters: int = 500,
        bm25_retriever_top_k: int = 50,
        return_detailed_info: bool = False,
    ) -> dict[str, Sequence[Collection[str]]]:
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
            vector_retriever_max_characters (int): Max characters from vector
                retriever results.
            bm25_retriever_top_k (int): Top results from BM25 retriever.
            return_detailed_info (bool): Return detailed info if True.

        Returns:
            dict[str, Sequence[Collection[str]]]: By default, returns
                only the text information. If `return_detailed_info` is
                `True`, return detailed information including rrf scores.
        """
        if top_k > max(vector_retriever_top_k, bm25_retriever_top_k):
            raise ValueError(
                "top_k needs to be less than or equal to the "
                "maximum value among vector_retriever_top_k and "
                "bm25_retriever_top_k."
            )
        if vector_weight or bm25_weight < 0:
            raise ValueError(
                "Neither `vector_weight` nor `bm25_weight` can be negative."
            )

        vector_retriever_results = self.auto_retriever.run_vector_retriever(
            query=query,
            contents=self.content_input_path,
            top_k=vector_retriever_top_k,
            similarity_threshold=vector_retriever_similarity_threshold,
            max_characters=vector_retriever_max_characters,
            return_detailed_info=True,
        )
        bm25_retriever_results = self.bm25_retriever.query(
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

        detailed_info = {
            "Original Query": query,
            "Retrieved Context": all_retrieved_info,
        }

        text_retrieved_info = [item['text'] for item in all_retrieved_info]

        text_info = {
            "Original Query": query,
            "Retrieved Context": text_retrieved_info,
        }
        if return_detailed_info:
            return detailed_info
        else:
            return text_info
