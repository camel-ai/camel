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
import datetime
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union
from urllib.parse import urlparse

from camel.embeddings import BaseEmbedding, OpenAIEmbedding
from camel.retrievers.vector_retriever import VectorRetriever
from camel.storages import (
    BaseVectorStorage,
    MilvusStorage,
    QdrantStorage,
    VectorDBQuery,
)
from camel.types import StorageType

DEFAULT_TOP_K_RESULTS = 1
DEFAULT_SIMILARITY_THRESHOLD = 0.75


class AutoRetriever:
    r"""Facilitates the automatic retrieval of information using a
    query-based approach with pre-defined elements.

    Attributes:
        url_and_api_key (Optional[Tuple[str, str]]): URL and API key for
            accessing the vector storage remotely.
        vector_storage_local_path (Optional[str]): Local path for vector
            storage, if applicable.
        storage_type (Optional[StorageType]): The type of vector storage to
            use. Defaults to `StorageType.QDRANT`.
        embedding_model (Optional[BaseEmbedding]): Model used for embedding
            queries and documents. Defaults to `OpenAIEmbedding()`.
    """

    def __init__(
        self,
        url_and_api_key: Optional[Tuple[str, str]] = None,
        vector_storage_local_path: Optional[str] = None,
        storage_type: Optional[StorageType] = None,
        embedding_model: Optional[BaseEmbedding] = None,
    ):
        self.storage_type = storage_type or StorageType.QDRANT
        self.embedding_model = embedding_model or OpenAIEmbedding()
        self.vector_storage_local_path = vector_storage_local_path
        self.url_and_api_key = url_and_api_key

    def _initialize_vector_storage(
        self,
        collection_name: Optional[str] = None,
    ) -> BaseVectorStorage:
        r"""Sets up and returns a vector storage instance with specified
        parameters.

        Args:
            collection_name (Optional[str]): Name of the collection in the
                vector storage.

        Returns:
            BaseVectorStorage: Configured vector storage instance.
        """
        if self.storage_type == StorageType.MILVUS:
            if self.url_and_api_key is None:
                raise ValueError(
                    "URL and API key required for Milvus storage are not"
                    "provided."
                )
            return MilvusStorage(
                vector_dim=self.embedding_model.get_output_dim(),
                collection_name=collection_name,
                url_and_api_key=self.url_and_api_key,
            )

        if self.storage_type == StorageType.QDRANT:
            return QdrantStorage(
                vector_dim=self.embedding_model.get_output_dim(),
                collection_name=collection_name,
                path=self.vector_storage_local_path,
                url_and_api_key=self.url_and_api_key,
            )

        raise ValueError(
            f"Unsupported vector storage type: {self.storage_type}"
        )

    def _collection_name_generator(self, content_input_path: str) -> str:
        r"""Generates a valid collection name from a given file path or URL.

        Args:
            content_input_path: str. The input URL or file path from which to
                generate the collection name.

        Returns:
            str: A sanitized, valid collection name suitable for use.
        """
        # Check path type
        parsed_url = urlparse(content_input_path)
        self.is_url = all([parsed_url.scheme, parsed_url.netloc])

        # Convert given path into a collection name, ensuring it only
        # contains numbers, letters, and underscores
        if self.is_url:
            # For URLs, remove https://, replace /, and any characters not
            # allowed by Milvus with _
            collection_name = re.sub(
                r'[^0-9a-zA-Z]+',
                '_',
                content_input_path.replace("https://", ""),
            )
        else:
            # For file paths, get the stem and replace spaces with _, also
            # ensuring only allowed characters are present
            collection_name = re.sub(
                r'[^0-9a-zA-Z]+', '_', Path(content_input_path).stem
            )

        # Ensure the collection name does not start or end with underscore
        collection_name = collection_name.strip("_")
        # Limit the maximum length of the collection name to 30 characters
        collection_name = collection_name[:30]
        return collection_name

    def _get_file_modified_date_from_file(
        self, content_input_path: str
    ) -> str:
        r"""Retrieves the last modified date and time of a given file. This
        function takes a file path as input and returns the last modified date
        and time of that file.

        Args:
            content_input_path (str): The file path of the content whose
                modified date is to be retrieved.

        Returns:
            str: The last modified time from file.
        """
        mod_time = os.path.getmtime(content_input_path)
        readable_mod_time = datetime.datetime.fromtimestamp(
            mod_time
        ).isoformat(timespec='seconds')
        return readable_mod_time

    def _get_file_modified_date_from_storage(
        self, vector_storage_instance: BaseVectorStorage
    ) -> str:
        r"""Retrieves the last modified date and time of a given file. This
        function takes vector storage instance as input and returns the last
        modified date from the metadata.

        Args:
            vector_storage_instance (BaseVectorStorage): The vector storage
                where modified date is to be retrieved from metadata.

        Returns:
            str: The last modified date from vector storage.
        """

        # Insert any query to get modified date from vector db
        # NOTE: Can be optimized when CAMEL vector storage support
        # direct chunk payload extraction
        query_vector_any = self.embedding_model.embed(obj="any_query")
        query_any = VectorDBQuery(query_vector_any, top_k=1)
        result_any = vector_storage_instance.query(query_any)

        # Extract the file's last modified date from the metadata
        # in the query result
        if result_any[0].record.payload is not None:
            file_modified_date_from_meta = result_any[0].record.payload[
                "metadata"
            ]['last_modified']
        else:
            raise ValueError(
                "The vector storage exits but the payload is None,"
                "please check the collection"
            )

        return file_modified_date_from_meta

    def run_vector_retriever(
        self,
        query: str,
        content_input_paths: Union[str, List[str]],
        top_k: int = DEFAULT_TOP_K_RESULTS,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        return_detailed_info: bool = False,
    ) -> str:
        r"""Executes the automatic vector retriever process using vector
        storage.

        Args:
            query (str): Query string for information retriever.
            content_input_paths (Union[str, List[str]]): Paths to local
                files or remote URLs.
            top_k (int, optional): The number of top results to return during
                retrieve. Must be a positive integer. Defaults to
                `DEFAULT_TOP_K_RESULTS`.
            similarity_threshold (float, optional): The similarity threshold
                for filtering results. Defaults to
                `DEFAULT_SIMILARITY_THRESHOLD`.
            return_detailed_info (bool, optional): Whether to return detailed
                information including similarity score, content path and
                metadata. Defaults to `False`.

        Returns:
            string: By default, returns only the text information. If
                `return_detailed_info` is `True`, return detailed information
                including similarity score, content path and metadata.

        Raises:
            ValueError: If there's an vector storage existing with content
                name in the vector path but the payload is None. If
                `content_input_paths` is empty.
            RuntimeError: If any errors occur during the retrieve process.
        """
        if not content_input_paths:
            raise ValueError("content_input_paths cannot be empty.")

        content_input_paths = (
            [content_input_paths]
            if isinstance(content_input_paths, str)
            else content_input_paths
        )

        vr = VectorRetriever()

        all_retrieved_info = []
        for content_input_path in content_input_paths:
            # Generate a valid collection name
            collection_name = self._collection_name_generator(
                content_input_path
            )
            try:
                vector_storage_instance = self._initialize_vector_storage(
                    collection_name
                )

                # Check the modified time of the input file path, only works
                # for local path since no standard way for remote url
                file_is_modified = False  # initialize with a default value
                if (
                    vector_storage_instance.status().vector_count != 0
                    and not self.is_url
                ):
                    # Get original modified date from file
                    modified_date_from_file = (
                        self._get_file_modified_date_from_file(
                            content_input_path
                        )
                    )
                    # Get modified date from vector storage
                    modified_date_from_storage = (
                        self._get_file_modified_date_from_storage(
                            vector_storage_instance
                        )
                    )
                    # Determine if the file has been modified since the last
                    # check
                    file_is_modified = (
                        modified_date_from_file != modified_date_from_storage
                    )

                if (
                    vector_storage_instance.status().vector_count == 0
                    or file_is_modified
                ):
                    # Clear the vector storage
                    vector_storage_instance.clear()
                    # Process and store the content to the vector storage
                    vr = VectorRetriever(
                        storage=vector_storage_instance,
                        similarity_threshold=similarity_threshold,
                    )
                    vr.process(content_input_path)
                else:
                    vr = VectorRetriever(
                        storage=vector_storage_instance,
                        similarity_threshold=similarity_threshold,
                    )
                # Retrieve info by given query from the vector storage
                retrieved_info = vr.query(query, top_k)
                all_retrieved_info.extend(retrieved_info)
            except Exception as e:
                raise RuntimeError(
                    f"Error in auto vector retriever processing: {e!s}"
                ) from e

        # Split records into those with and without a 'similarity_score'
        # Records with 'similarity_score' lower than 'similarity_threshold'
        # will not have a 'similarity_score' in the output content
        with_score = [
            info for info in all_retrieved_info if 'similarity score' in info
        ]
        without_score = [
            info
            for info in all_retrieved_info
            if 'similarity score' not in info
        ]
        # Sort only the list with scores
        with_score_sorted = sorted(
            with_score, key=lambda x: x['similarity score'], reverse=True
        )
        # Merge back the sorted scored items with the non-scored items
        all_retrieved_info_sorted = with_score_sorted + without_score
        # Select the 'top_k' results
        all_retrieved_info = all_retrieved_info_sorted[:top_k]

        retrieved_infos = "\n".join(str(info) for info in all_retrieved_info)
        retrieved_infos_text = "\n".join(
            info['text'] for info in all_retrieved_info if 'text' in info
        )

        detailed_info = (
            f"Original Query:\n{{ {query} }}\n"
            f"Retrieved Context:\n{retrieved_infos}"
        )

        text_info = (
            f"Original Query:\n{{ {query} }}\n"
            f"Retrieved Context:\n{retrieved_infos_text}"
        )

        if return_detailed_info:
            return detailed_info
        else:
            return text_info
