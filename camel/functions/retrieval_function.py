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

from pathlib import Path
from typing import Any, Optional, Tuple, Union
from urllib.parse import urlparse

from camel.embeddings import BaseEmbedding, OpenAIEmbedding
from camel.functions.unstructured_io_fuctions import UnstructuredModules
from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    QdrantStorage,
    VectorDBQuery,
    VectorRecord,
)
from camel.types import VectorDistance


class RetrievalFunction:
    r"""Implements retrieval by combining vector storage with an embedding model.

    This class facilitates the retrieval of relevant information using a query-based approach, backed by vector embeddings. It is useful for information retrieval.

    Attributes:
        embedding_model (BaseEmbedding): Embedding model used to generate vector embeddings.
        vector_storage: (BaseVectorStorage): Vector store used to retrieve information.
        top_k (int): Number of top-ranked results returned in queries.
        vector_dim (int): Dimensionality of the vector embeddings used.
    """

    def __init__(self, 
                 embedding_model: Optional[BaseEmbedding] = None, 
                 vector_storage: Optional[BaseVectorStorage] = None,
                 top_k: Optional[int] = 1) -> None:
        r"""Initializes the retrieval class with an optional embedding model and vector storage, and sets the number of top results for retrieval.

        Args:
            embedding_model (Optional[BaseEmbedding]): The embedding model instance. Defaults to OpenAIEmbedding if not provided.
            vector_storage (Optional[BaseVectorStorage]): The vector storage instance. Defaults to QdrantStorage if not provided.
            top_k Optional[int]: The number of top results to return during retrieval. Must be a positive integer. Defaults to 1.

        Raises:
            ValueError: If 'top_k' is less than or equal to 0.
        """
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")

        self.embedding_model = embedding_model or OpenAIEmbedding()
        self.vector_dim = self.embedding_model.get_output_dim()
        self.vector_storage = vector_storage or QdrantStorage(vector_dim=self.vector_dim)
        self.top_k = top_k

    def _set_vector_storage(
        self,
        storage_type: str,
        collection_name: Optional[str] = None,
        collection_accessable: Optional[bool] = None,
        vector_storage_local_path: Optional[str] = None,
        url_and_api_key: Optional[Tuple[str, str]] = None,
        vector_storage: Optional[BaseVectorStorage] = None) -> BaseVectorStorage:
        r"""Sets up and returns a vector storage instance (either local or remote) with specified parameters.

        Args:
            storage_type (str): Type of storage ('local' or 'remote').
            collection_name (Optional[str]): Name of the collection in the vector storage.
            collection_accessable (Optional[bool]): Flag indicating if the collection already exists.
            vector_storage_local_path (Optional[str]): Filesystem path for local vector storage (used when storage_type is 'local').
            url_and_api_key (Optional[Tuple[str, str]]): URL and API key for remote storage access (used when storage_type is 'remote').
            vector_storage (Optional[BaseVectorStorage]): An existing vector storage instance.

        Returns:
            BaseVectorStorage: Configured vector storage instance.

        Raises:
            ValueError: If the necessary parameters for the specified storage type are not provided or if incompatible parameters are provided.
        """

        if storage_type == 'local':
            if vector_storage_local_path is None:
                raise ValueError("For local storage, 'vector_storage_local_path' must be provided.")
            if url_and_api_key is not None:
                raise ValueError("For local storage, 'url_and_api_key' must not be provided.")

            return vector_storage or QdrantStorage(
                vector_dim=self.vector_dim,
                collection=collection_name,
                create_collection=not collection_accessable,
                path=vector_storage_local_path)

        elif storage_type == 'remote':
            if url_and_api_key is None:
                raise ValueError("For remote storage, 'url_and_api_key' must be provided.")
            if vector_storage_local_path is not None:
                raise ValueError("For remote storage, 'vector_storage_local_path' must not be provided.")

            return vector_storage or QdrantStorage(
                vector_dim=self.vector_dim,
                collection=collection_name,
                url_and_api_key=url_and_api_key,
                create_collection=not collection_accessable,
                distance=VectorDistance.COSINE)

        else:
            raise ValueError("Invalid storage type specified. Please choose 'local' or 'remote'.")


    def _check_collection_status(self,
                                collection_name: str,
                                storage_type: str,
                                vector_storage_local_path: Optional[str] = None,
                                url_and_api_key: Optional[Tuple[str, str]] = None,
                                vector_storage: Optional[BaseVectorStorage] = None) -> bool:
        r"""Checks and returns the status of the specified collection in the vector storage.

        Args:
            collection_name (str): Name of the collection to check.
            storage_type (str): Type of storage ('local' or 'remote').
            vector_storage_local_path (Optional[str]): Filesystem path for local vector storage (used when storage_type is 'local').
            url_and_api_key (Optional[Tuple[str, str]]): URL and API key for remote storage access (used when storage_type is 'remote').
            vector_storage (Optional[BaseVectorStorage]): Vector storage instance.

        Returns:
            bool: True if the collection exists and is accessible, False otherwise.

        Raises:
            ValueError: If the necessary parameters for the specified storage type are not provided or if incompatible parameters are provided.
        """
        try:
            if storage_type == 'local':
                if vector_storage_local_path is None:
                    raise ValueError("For local storage, 'vector_storage_local_path' must be provided.")
                if url_and_api_key is not None:
                    raise ValueError("For local storage, 'url_and_api_key' must not be provided.")

                storage = vector_storage or QdrantStorage(
                    vector_dim=self.vector_dim,
                    collection=collection_name,
                    path=vector_storage_local_path
                )

            elif storage_type == 'remote':
                if url_and_api_key is None:
                    raise ValueError("For remote storage, 'url_and_api_key' must be provided.")
                if vector_storage_local_path is not None:
                    raise ValueError("For remote storage, 'vector_storage_local_path' must not be provided.")

                storage = vector_storage or QdrantStorage(
                    vector_dim=self.vector_dim,
                    collection=collection_name,
                    url_and_api_key=url_and_api_key
                )

            else:
                raise ValueError("Invalid storage type specified. Please choose 'local' or 'remote'.")

            storage.status
            return True

        except:
            return False

    def _embed_and_store_chunks(self,
                                 content_input_path: str,
                                 vector_storage: BaseVectorStorage,
                                 **kwargs: Any) -> None:
        r""" Processes content from a file or URL, divides it into chunks, and stores their embeddings in the specified vector storage.

        Args:
            content_input_path (str): File path or URL of the content to be processed.
            vector_storage (BaseVectorStorage): Vector storage to store the embeddings.
            **kwargs (Any): Additional keyword arguments.
        """
        unstructured_modules = UnstructuredModules()
        elements = unstructured_modules.parse_file_or_url(content_input_path)
        chunks = unstructured_modules.chunk_elements(chunk_type="chunk_by_title", elements=elements,**kwargs)

        for chunk in chunks:
            vector = self.embedding_model.embed(obj=str(chunk))
            payload_dict = {"text": str(chunk)}
            vector_storage.add(records=[VectorRecord(vector=vector, payload=payload_dict)])


    def _query_and_compile_results(self,
                                    query: str,
                                    vector_storage: BaseVectorStorage,
                                    **kwargs: Any) -> str:
        r"""Executes a query in vector storage and compiles the retrieved results into a string.

        Args:
            query (str): Query string for information retrieval.
            vector_storage (BaseVectorStorage): Vector storage to query.
            **kwargs (Any): Additional keyword arguments.

        Returns:
            str: Concatenated string of the query results.
        """
        query_vector = self.embedding_model.embed(obj=query)
        db_query = VectorDBQuery(query_vector=query_vector, top_k=self.top_k)
        query_results = vector_storage.query(query=db_query,**kwargs)
        return "".join(str(i.record.payload) for i in query_results)


    def run_retrieval(self,
                    query: str,
                    content_input_paths: Union[str, list[str]],
                    storage_type: str,
                    vector_storage_local_path: Optional[str] = None,
                    url_and_api_key: Optional[Tuple[str, str]] = None
                    ) -> str:
        r"""Executes the retrieval process using specified storage type.

        Args:
            query (str): Query string for information retrieval.
            content_input_paths (Union[str, list[str]]): Paths to content files or URLs.
            storage_type (str): Type of storage ('local' or 'remote').
            vector_storage_local_path (Optional[str]): Local path for vector storage (used when storage_type is 'local').
            url_and_api_key (Optional[Tuple[str, str]]): URL and API key for remote storage access (used when storage_type is 'remote').

        Returns:
            str: Aggregated information retrieved in response to the query.

        Raises:
            ValueError: If the necessary parameters for the specified storage type are not provided or if incompatible parameters are provided.
            RuntimeError: If any errors occur during the retrieval process.
        """
        if storage_type == 'local':
            if not vector_storage_local_path:
                raise ValueError("For local storage, 'vector_storage_local_path' must be provided.")
            if url_and_api_key is not None:
                raise ValueError("For local storage, 'url_and_api_key' must not be provided.")
        elif storage_type == 'remote':
            if not url_and_api_key:
                raise ValueError("For remote storage, 'url_and_api_key' must be provided.")
            if vector_storage_local_path is not None:
                raise ValueError("For remote storage, 'vector_storage_local_path' must not be provided.")
        else:
            raise ValueError("Invalid storage type specified. Please choose 'local' or 'remote'.")

        content_input_paths = [content_input_paths] if isinstance(content_input_paths, str) else content_input_paths

        retrieved_infos = ""

        for content_input_path in content_input_paths:
            # Check path type
            parsed_url = urlparse(content_input_path)
            is_url = all([parsed_url.scheme, parsed_url.netloc])
            # Convert given path into collection name
            collection_name = (content_input_path.replace("https://", "").replace("/", "_").strip("_")
                            if is_url else Path(content_input_path).stem.replace(' ', '_'))

            collection_accessable = self._check_collection_status(
                storage_type=storage_type,
                vector_storage_local_path=vector_storage_local_path if storage_type == 'local' else None,
                url_and_api_key=url_and_api_key if storage_type == 'remote' else None,
                collection_name=collection_name)

            try:
                vector_storage_instance = self._set_vector_storage(
                    storage_type=storage_type,
                    collection_name=collection_name,
                    collection_accessable=collection_accessable,
                    vector_storage_local_path=vector_storage_local_path if storage_type == 'local' else None,
                    url_and_api_key=url_and_api_key if storage_type == 'remote' else None)

                if not collection_accessable:
                    self._embed_and_store_chunks(content_input_path, vector_storage_instance)

                retrieved_info = self._query_and_compile_results(query, vector_storage_instance)
                retrieved_infos += "\n" + retrieved_info

            except Exception as e:
                raise RuntimeError(f"Error in retrieval processing: {str(e)}") from e

        return retrieved_infos
