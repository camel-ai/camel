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
from typing import Any, Dict, List, Optional

import numpy as np

from camel.loaders import Chunk
from camel.retrievers import BaseRetriever
from camel.types.enums import ChunkToolType
from camel.utils import dependencies_required

DEFAULT_TOP_K_RESULTS = 1


class BM25Retriever(BaseRetriever):
    r"""An implementation of the `BaseRetriever` using the `BM25` model.

    This class facilitates the retriever of relevant information using a
    query-based approach, it ranks documents based on the occurrence and
    frequency of the query terms.

    Attributes:
        bm25 (BM25Okapi): An instance of the BM25Okapi class used for
            calculating document scores.
        content_input_path (str): The path to the content that has been
            processed and stored.
        unstructured_modules (UnstructuredIO): A module for parsing files and
            URLs and chunking content based on specified parameters.

    References:
        https://github.com/dorianbrown/rank_bm25
    """

    @dependencies_required('rank_bm25')
    def __init__(self) -> None:
        r"""Initializes the BM25Retriever."""
        from rank_bm25 import BM25Okapi

        self.bm25: BM25Okapi = None
        self.content_input_path: str = ""

    def load_chunks(
        self,
        chunks: Optional[List[Chunk]] = None,
    ) -> None:
        r"""Loads chunks into the BM25 model.

        Uses BM25Okapi from the rank_bm25 library to create a BM25 model based
        on tokenized text. If no chunks are provided, `self.chunks` is used.
        Raises a ValueError if both are empty.

        Args:
            chunks (Optional[List[Chunk]]): A list of chunks.
        Raises:
            ValueError: If neither `chunks` nor `self.chunks` is available.
        """
        if chunks is None:
            chunks = self.chunks

        if not chunks:
            raise ValueError("No chunks provided.")

        from rank_bm25 import BM25Okapi

        tokenized_corpus = []
        for chunk in chunks:
            tokenized_corpus.append(chunk.text.split(" "))

        self.bm25 = BM25Okapi(tokenized_corpus)

    def process(
        self,
        content_input_path: str,
        chunk_tool_type: ChunkToolType = ChunkToolType.UNSTRUCTURED_IO,
        chunk_type: str = "chunk_by_title",
        extra_info: Optional[dict] = None,
        **kwargs: Any,
    ) -> None:
        r"""Processes content from a file or URL, divides it into chunks by
        using chunk tool, then stored internally. This method or `load_chunks`
        must be called before executing queries with the retriever.

        Args:
            content_input_path (str): File path or URL of the content to be
                processed.
            chunk_tool_type (ChunkToolType): Type of chunking going to apply.
                Defaults to `ChunkToolType.UNSTRUCTURED_IO`.
            chunk_type (str): Type of chunking going to apply in
                `UnstructuredIO`. Defaults to "chunk_by_title".
            extra_info (Optional[dict]): Additional information to be added to
                the chunks.
            **kwargs (Any): Additional keyword arguments for content parsing.
        """
        self.content_input_path = content_input_path
        if chunk_tool_type == ChunkToolType.UNSTRUCTURED_IO:
            from camel.loaders import UnstructuredIO

            # Load and preprocess documents
            self.unstructured_modules: UnstructuredIO = UnstructuredIO()
            elements = self.unstructured_modules.parse_file_or_url(
                content_input_path, **kwargs
            )
            if elements:
                uio_chunks = self.unstructured_modules.chunk_elements(
                    chunk_type=chunk_type, elements=elements
                )
                self.chunks = Chunk.from_uio_chunks(uio_chunks, extra_info)
        else:
            raise ValueError(f"Unsupported chunk tool type: {chunk_tool_type}")

        self.load_chunks()

    def query(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K_RESULTS,
    ) -> List[Dict[str, Any]]:
        r"""Executes a query and compiles the results.

        Args:
            query (str): Query string for information retriever.
            top_k (int, optional): The number of top results to return during
                retriever. Must be a positive integer. Defaults to
                `DEFAULT_TOP_K_RESULTS`.

        Returns:
            List[Dict[str]]: Concatenated list of the query results.

        Raises:
            ValueError: If `top_k` is less than or equal to 0, if the BM25
                model has not been initialized by calling `process`
                first.
        """

        if top_k <= 0:
            raise ValueError("top_k must be a positive integer.")
        if self.bm25 is None or not self.chunks:
            raise ValueError(
                "BM25 model is not initialized. Call `process` first."
            )

        # Preprocess query similarly to how documents were processed
        processed_query = query.split(" ")
        # Retrieve documents based on BM25 scores
        scores = self.bm25.get_scores(processed_query)

        top_k_indices = np.argpartition(scores, -top_k)[-top_k:]

        formatted_results = []
        for i in top_k_indices:
            result_dict = {
                'similarity score': scores[i],
                'content path': self.content_input_path,
                'metadata': self.chunks[i].metadata,
                'text': self.chunks[i].text,
            }
            formatted_results.append(result_dict)

        # Sort the list of dictionaries by 'similarity score' from high to low
        formatted_results.sort(
            key=lambda x: x['similarity score'], reverse=True
        )

        return formatted_results
