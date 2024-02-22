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
from typing import Any, Optional

from camel.embeddings import BaseEmbedding, OpenAIEmbedding
from camel.functions.unstructured_io_functions import UnstructuredModules
from camel.retrievers import BaseRetriever
from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorRecord,
)

DEFAULT_TOP_K_RESULTS = 1
DEFAULT_SIMILARITY_THRESHOLD = 0.75


class VectorRetriever(BaseRetriever):
    r"""An implementation of the `BaseRetriever` by using vector storage and
    embedding model.

    This class facilitates the retriever of relevant information using a
    query-based approach, backed by vector embeddings.

    Attributes:
        embedding_model (BaseEmbedding): Embedding model used to generate
            vector embeddings.
    """

    def __init__(self,
                 embedding_model: Optional[BaseEmbedding] = None) -> None:
        r"""Initializes the retriever class with an optional embedding model.

        Args:
            embedding_model (Optional[BaseEmbedding]): The embedding model
                instance. Defaults to `OpenAIEmbedding` if not provided.
        """
        self.embedding_model = embedding_model or OpenAIEmbedding()

    def process_and_store(self, content_input_path: str,
                          storage: BaseVectorStorage, **kwargs: Any) -> None:
        r""" Processes content from a file or URL, divides it into chunks by
        using `Unstructured IO`, and stores their embeddings in the specified
        vector storage.

        Args:
            content_input_path (str): File path or URL of the content to be
                processed.
            storage (BaseVectorStorage): Vector storage to store the
                embeddings.
            **kwargs (Any): Additional keyword arguments for elements chunking.
        """
        unstructured_modules = UnstructuredModules()
        elements = unstructured_modules.parse_file_or_url(content_input_path)
        chunks = unstructured_modules.chunk_elements(
            chunk_type="chunk_by_title", elements=elements, **kwargs)
        # Iterate to process and store embeddings, set batch of 50
        for i in range(0, len(chunks), 50):
            batch_chunks = chunks[i:i + 50]
            batch_vectors = self.embedding_model.embed_list(
                objs=[str(chunk) for chunk in batch_chunks])

            records = []
            # Prepare the payload for each vector record, includes the content
            # path, chunk metadata, and chunk text
            for vector, chunk in zip(batch_vectors, batch_chunks):
                content_path_info = {"content path": content_input_path}
                chunk_metadata = {"metadata": chunk.metadata.to_dict()}
                chunk_text = {"text": str(chunk)}
                combined_dict = {
                    **content_path_info,
                    **chunk_metadata,
                    **chunk_text
                }

                records.append(
                    VectorRecord(vector=vector, payload=combined_dict))

            storage.add(records=records)

    def query_and_compile_results(
            self, query: str, storage: BaseVectorStorage,
            top_k: int = DEFAULT_TOP_K_RESULTS,
            similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
            **kwargs: Any) -> list:
        r"""Executes a query in vector storage and compiles the retrieved
        results into a string.

        Args:
            query (str): Query string for information retriever.
            storage (BaseVectorStorage): Vector storage to query.
            top_k (int, optional): The number of top results to return during
                retriever. Must be a positive integer. Defaults to 1.
            similarity_threshold (float, optional): The similarity threshold
                for filtering results. Defaults to 0.75.
            **kwargs (Any): Additional keyword arguments for vector storage
                query.

        Returns:
            list: Concatenated list of the query results.

        Raises:
            ValueError: If 'top_k' is less than or equal to 0, if vector
                storage is empty, if payload of vector storage is None.
        """

        if top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        if storage.status().vector_count == 0:
            raise ValueError("Vector storage is empty, please check"
                             "the collection.")

        query_vector = self.embedding_model.embed(obj=query)
        db_query = VectorDBQuery(query_vector=query_vector, top_k=top_k)
        query_results = storage.query(query=db_query, **kwargs)

        if query_results[0].record.payload is None:
            raise ValueError("Payload of vector storage is None, please check"
                             " the collection.")

        # format the results
        formatted_results = []
        for result in query_results:
            if (result.similarity >= similarity_threshold
                    and result.record.payload is not None):
                result_dict = {
                    'similarity score': str(result.similarity),
                    'content path':
                    result.record.payload.get('content path', ''),
                    'metadata': result.record.payload.get('metadata', {}),
                    'text': result.record.payload.get('text', '')
                }
                formatted_results.append(result_dict)

        if not formatted_results:
            return [{
                'text':
                f"""No suitable information retrieved from \
                {query_results[0].record.payload.get('content path','')} \
                with similarity_threshold = {similarity_threshold}."""
            }]
        return formatted_results
