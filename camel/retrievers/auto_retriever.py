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
from camel.retrievers import VectorRetriever
from camel.storages import (
    BaseVectorStorage,
    MilvusStorage,
    QdrantStorage,
    VectorDBQuery,
)

DEFAULT_TOP_K_RESULTS = 1
DEFAULT_SIMILARITY_THRESHOLD = 0.75


class AutoRetriever():
    r""" Facilitates the automatic retrieval of information using a
    query-based approach with pre-defined elements.

    Attributes:
        url_and_api_key (Optional[Tuple[str, str]]): URL and API key for
            accessing the vector storage remotely.
        vector_storage_local_path (Optional[str]): Local path for vector
            storage, if applicable.
        storage_type (str): Type of vector storage to use. Defaults to
            `Milvus`.
            Available document types:
            "Milvus", "Qdrant".
        embedding_model (BaseEmbedding): Model used for embedding queries and
            documents. Defaults to `OpenAIEmbedding()`.
    """

    def __init__(
        self,
        url_and_api_key: Optional[Tuple[str, str]] = None,
        vector_storage_local_path: Optional[str] = None,
        storage_type: Optional[str] = None,
        embedding_model: Optional[BaseEmbedding] = None,
    ):

        self.storage_type = storage_type or "milvus"
        self.embedding_model = embedding_model or OpenAIEmbedding()
        self.vector_storage_local_path = vector_storage_local_path
        self.url_and_api_key = url_and_api_key

    def _initialize_vector_storage(
        self,
        collection_name: Optional[str] = None,
    ) -> BaseVectorStorage:
        r"""Sets up and returns a vector storage instance with specified parameters.

        Args:
            collection_name (Optional[str]): Name of the collection in the
                vector storage.

        Returns:
            BaseVectorStorage: Configured vector storage instance.
        """
        if self.storage_type.lower() == 'milvus':
            if self.url_and_api_key is None:
                raise ValueError(
                    "URL and API key required for Milvus storage are not"
                    "provided.")
            return MilvusStorage(
                vector_dim=self.embedding_model.get_output_dim(),
                collection_name=collection_name,
                url_and_api_key=self.url_and_api_key)

        if self.storage_type.lower() == 'qdrant':
            return QdrantStorage(
                vector_dim=self.embedding_model.get_output_dim(),
                collection_name=collection_name,
                path=self.vector_storage_local_path,
                url_and_api_key=self.url_and_api_key)

        raise ValueError(
            f"Unsupported vector storage type: {self.storage_type}, supported"
            "type: 'milvus', 'qdrant'")

    def _get_file_modified_date(self, content_input_path: str) -> str:
        r"""Retrieves the last modified date and time of a given file. This
        function takes a file path as input and returns the last modified date
        and time of that file.

        Args:
            content_input_path (str): The file path of the content whose
                modified date is to be retrieved.

        Returns:
            str: The last modified date and time of the file.
        """
        mod_time = os.path.getmtime(content_input_path)
        readable_mod_time = datetime.datetime.fromtimestamp(
            mod_time).isoformat(timespec='seconds')
        return readable_mod_time

    def run_vector_retriever(
            self, query: str, content_input_paths: Union[str, List[str]],
            top_k: int = DEFAULT_TOP_K_RESULTS,
            similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
            return_detailed_info: bool = False) -> str:
        r"""Executes the automatic vector retriever process using vector storage.

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
                metadata. Defaults to False.

        Returns:
            string: By default, returns only the text information. If
                `return_detailed_info` is True, return detailed information
                including similarity score, content path and metadata.

        Raises:
            ValueError: If there's an vector storage existing with content
                name in the vector path but the payload is None.
            RuntimeError: If any errors occur during the retrieve process.
        """
        vr = VectorRetriever()
        content_input_paths = [content_input_paths] if isinstance(
            content_input_paths, str) else content_input_paths

        retrieved_infos = ""
        retrieved_infos_text = ""

        for content_input_path in content_input_paths:
            # Check path type
            parsed_url = urlparse(content_input_path)
            is_url = all([parsed_url.scheme, parsed_url.netloc])

            # Convert given path into a collection name, ensuring it only
            # contains numbers, letters, and underscores
            if is_url:
                # For URLs, replace https://, /, and any characters not
                # allowed by Milvus with _
                collection_name = re.sub(
                    r'[^0-9a-zA-Z]+', '_',
                    content_input_path.replace("https://", ""))
            else:
                # For file paths, get the stem and replace spaces with _, also
                # ensuring only allowed characters are present
                collection_name = re.sub(r'[^0-9a-zA-Z]+', '_',
                                         Path(content_input_path).stem)

            # Ensure the collection name does not start or end with an
            # underscore
            collection_name = collection_name.strip("_")

            try:
                vector_storage_instance = self._initialize_vector_storage(
                    collection_name)

                # Check the modified time of the input file path, only works
                # for local path since no standard way for remote url

                file_is_modified = False  # Initialize with a default value

                if vector_storage_instance.status(
                ).vector_count != 0 and not is_url:
                    # Get original modified date from file
                    file_modified_date = self._get_file_modified_date(
                        content_input_path)

                    # Insert any query to get modified date from vector db
                    # NOTE: Can be optimized when CAMEL vector storage support
                    # direct chunk payload extraction
                    query_vector_any = self.embedding_model.embed(
                        obj="any_query")
                    query_any = VectorDBQuery(query_vector_any, top_k=1)
                    result_any = vector_storage_instance.query(query_any)

                    # Extract the file's last modified date from the metadata
                    # in the query result
                    if result_any[0].record.payload is not None:
                        file_modified_date_from_meta = (
                            result_any[0].record.payload["metadata"]
                            ['last_modified'])
                    else:
                        raise ValueError(
                            "The vector storage exits but the payload is None,"
                            "please check the collection")

                    # Determine if the file has been modified since the last
                    # check
                    file_is_modified = (file_modified_date !=
                                        file_modified_date_from_meta)

                if vector_storage_instance.status(
                ).vector_count == 0 or file_is_modified:
                    # Clear the vector storage
                    vector_storage_instance.clear()
                    # Process and store the content to the vector storage
                    vr.process_and_store(content_input_path,
                                         vector_storage_instance)
                # Retrieve info by given query from the vector storage
                retrieved_info = vr.query_and_compile_results(
                    query, vector_storage_instance, top_k,
                    similarity_threshold)
                for info in retrieved_info:
                    # Reorganize the retrieved info with original query
                    retrieved_infos += "\n" + str(info)
                    retrieved_infos_text += "\n" + str(info['text'])
                output = ("Original Query:" + "\n" + "{" + query + "}" + "\n" +
                          "Retrieved Context:" + retrieved_infos)
                output_text = ("Original Query:" + "\n" + "{" + query + "}" +
                               "\n" + "Retrieved Context:" +
                               retrieved_infos_text)
            except Exception as e:
                raise RuntimeError(
                    f"Error in auto vector retriever processing: {str(e)}"
                ) from e
        if return_detailed_info:
            return output
        else:
            return output_text
