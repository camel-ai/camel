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
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from camel.storages.key_value_storages.json import CamelJSONEncoder
from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.utils import dependencies_required

logger = logging.getLogger(__name__)


class MilvusPointAdapter:
    """An adapter class for converting VectorRecord objects into a format suitable
    for Milvus storage.

    This class handles the conversion of VectorRecord objects into a dictionary
    format that can be stored in Milvus, including handling of message content
    and payload serialization.

    Args:
        record (VectorRecord): The vector record to be converted into a Milvus
            compatible format.
    """

    def __init__(self, record: VectorRecord):
        """Initialize the adapter with a VectorRecord.

        Args:
            record (VectorRecord): The vector record to be converted.
        """
        self.id = record.id
        self.payload = (
            json.dumps(record.payload, cls=CamelJSONEncoder)
            if record.payload
            else ''
        )
        self.dense_vector = record.vector

        self.text = ""
        if record.payload:
            try:
                message = record.payload.get("message")
                if (
                    message is not None
                    and isinstance(message, dict)
                    and "content" in message
                ):
                    self.text = message["content"]
            except Exception as e:
                logger.warning(
                    f"Failed to extract content from message: {e!s}"
                )

            if not self.text and "content" in record.payload:
                self.text = record.payload["content"]

            if not self.text:
                logger.warning(
                    "No text content found in either message or direct content"
                )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the adapter's data into a dictionary format suitable for
        Milvus storage.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - id: The unique identifier
                - payload: The serialized payload
                - dense_vector: The dense vector representation
                - text: The text content extracted from the payload
        """
        return {
            "id": self.id,
            "payload": self.payload,
            "dense": self.dense_vector,
            "text": self.text,
        }


class MilvusStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with
    Milvus, a cloud-native vector search engine.

    The detailed information about Milvus is available at:
    `Milvus <https://milvus.io/docs/overview.md/>`_

    Args:
        vector_dim (int): The dimenstion of storing vectors.
        url_and_api_key (Tuple[str, str]): Tuple containing
           the URL and API key for connecting to a remote Milvus instance.
           URL maps to Milvus uri concept, typically "endpoint:port".
           API key maps to Milvus token concept, for self-hosted it's
           "username:pwd", for Zilliz Cloud (fully-managed Milvus) it's API
           Key.
        collection_name (Optional[str], optional): Name for the collection in
            the Milvus. If not provided, set it to the current time with iso
            format. (default: :obj:`None`)
        hybrid_search_config (Optional[Dict[str, Any]]): Configuration for hybrid search.
            Supported keys:
            - 'enable': Whether to enable hybrid search (default: False)
            - 'vector_weight': Weight for vector similarity (default: 0.5)
            - 'text_weight': Weight for text similarity (default: 0.5)
        **kwargs (Any): Additional keyword arguments for initializing
            the Milvus.

    Raises:
        ImportError: If `pymilvus` package is not installed.
    """

    @dependencies_required('pymilvus')
    def __init__(
        self,
        vector_dim: int,
        url_and_api_key: Optional[Tuple[str, str]] = None,
        collection_name: Optional[str] = None,
        hybrid_search_config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        from pymilvus import MilvusClient

        self._client: MilvusClient

        if not url_and_api_key:
            url_and_api_key = ("./milvus.db", "")
            logger.warning("Using local Milvus Lite database: ./milvus.db")

        self._create_client(url_and_api_key, **kwargs)

        # Set default hybrid search configuration
        default_config = {
            'enable': False,
            'vector_weight': 0.5,
            'text_weight': 0.5,
        }

        # Merge provided config with defaults
        self.hybrid_search_config = default_config.copy()
        if hybrid_search_config:
            self.hybrid_search_config.update(hybrid_search_config)

        self.vector_dim = vector_dim
        self.collection_name = (
            collection_name or self._generate_collection_name()
        )
        self._check_and_create_collection()

    def _create_client(
        self,
        url_and_api_key: Tuple[str, str] = None,
        **kwargs: Any,
    ) -> None:
        r"""Initializes the Milvus client with the provided connection details.

        Args:
            url_and_api_key (Tuple[str, str]): The URL and API key for the
                Milvus server.
            **kwargs: Additional keyword arguments passed to the Milvus client.
        """
        from pymilvus import MilvusClient

        # Ensure url_and_api_key is not None
        assert url_and_api_key is not None, "url_and_api_key cannot be None"

        self._client = MilvusClient(
            uri=url_and_api_key[0],
            token=url_and_api_key[1],
            **kwargs,
        )

    def _check_and_create_collection(self) -> None:
        r"""Checks if the specified collection exists in Milvus and creates it
        if it doesn't, ensuring it matches the specified vector dimensionality.
        """
        if self._collection_exists(self.collection_name):
            in_dim = self._get_collection_info(self.collection_name)[
                "vector_dim"
            ]
            if in_dim != self.vector_dim:
                # The name of collection has to be confirmed by the user
                raise ValueError(
                    "Vector dimension of the existing collection "
                    f'"{self.collection_name}" ({in_dim}) is different from '
                    f"the given embedding dim ({self.vector_dim})."
                )
        else:
            self._create_collection(
                collection_name=self.collection_name,
            )

    def _create_collection(
        self,
        collection_name: str,
        **kwargs: Any,
    ) -> None:
        r"""Creates a new collection in the database.

        Args:
            collection_name (str): Name of the collection to be created.
            **kwargs (Any): Additional keyword arguments pass to create
                collection.
        """

        from pymilvus import DataType, Function, FunctionType

        if self._client.has_collection(collection_name=collection_name):
            self._client.drop_collection(collection_name=collection_name)

        schema = self._client.create_schema(
            auto_id=False,
            enable_dynamic_field=True,
            description='collection schema',
        )

        schema.add_field(
            field_name="id",
            datatype=DataType.VARCHAR,
            descrition='A unique identifier for the vector',
            is_primary=True,
            max_length=65535,
        )

        schema.add_field(
            field_name="dense",
            datatype=DataType.FLOAT_VECTOR,
            description='The numerical representation of the vector',
            dim=self.vector_dim,
        )

        schema.add_field(
            field_name="payload",
            datatype=DataType.JSON,
            description='Any additional metadata or information related to '
            'the vector',
        )

        schema.add_field(
            field_name="text",
            datatype=DataType.VARCHAR,
            description='The text representation of the vector',
            enable_analyzer=True,
            max_length=65535,
        )

        if self.hybrid_search_config['enable']:
            schema.add_field(
                field_name="sparse",
                datatype=DataType.SPARSE_FLOAT_VECTOR,
                description='The sparse representation of the vector',
            )

            bm25_function = Function(
                name="text_bm25_emb",
                input_field_names=["text"],
                output_field_names=["sparse"],
                function_type=FunctionType.BM25,
            )

            schema.add_function(bm25_function)

        index_params = self._client.prepare_index_params()

        index_params.add_index(
            field_name="dense",
            index_name="dense_index",
            metric_type="IP",
            index_type="FLAT",
            params={"nlist": 128},
        )

        if self.hybrid_search_config['enable']:
            index_params.add_index(
                field_name="sparse",
                index_name="sparse_index",
                # Index type for sparse vectors
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="BM25",
                params={"inverted_index_algo": "DAAT_MAXSCORE"},
                # The ratio of small vector values to be dropped
                # during indexing
            )

        self._client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params,
            **kwargs,
        )

        self.load()

    def _delete_collection(
        self,
        collection_name: str,
    ) -> None:
        r"""Deletes an existing collection from the database.

        Args:
            collection (str): Name of the collection to be deleted.
        """
        self._client.drop_collection(collection_name=collection_name)

    def _collection_exists(self, collection_name: str) -> bool:
        r"""Checks whether a collection with the specified name exists in the
        database.

        Args:
            collection_name (str): The name of the collection to check.

        Returns:
            bool: True if the collection exists, False otherwise.
        """
        return self._client.has_collection(collection_name)

    def _generate_collection_name(self) -> str:
        r"""Generates a unique name for a new collection based on the current
        timestamp. Milvus collection names can only contain alphanumeric
        characters and underscores.

        Returns:
            str: A unique, valid collection name.
        """
        timestamp = datetime.now().isoformat()
        transformed_name = re.sub(r'[^a-zA-Z0-9_]', '_', timestamp)
        valid_name = "Time" + transformed_name
        return valid_name

    def _get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        r"""Retrieves details of an existing collection.

        Args:
            collection_name (str): Name of the collection to be checked.

        Returns:
            Dict[str, Any]: A dictionary containing details about the
                collection.
        """
        vector_count = self._client.get_collection_stats(collection_name)[
            'row_count'
        ]
        collection_info = self._client.describe_collection(collection_name)
        collection_id = collection_info['collection_id']

        dim_value = next(
            (
                field['params']['dim']
                for field in collection_info['fields']
                if field['description']
                == 'The numerical representation of the vector'
            ),
            None,
        )

        return {
            "id": collection_id,  # the id of the collection
            "vector_count": vector_count,  # the number of the vector
            "vector_dim": dim_value,  # the dimension of the vector
        }

    def add(
        self,
        records: List[VectorRecord],
        **kwargs,
    ) -> None:
        r"""Adds a list of vectors to the specified collection.

        Args:
            records (List[VectorRecord]): List of vectors to be added.
            **kwargs (Any): Additional keyword arguments pass to insert.

        Raises:
            RuntimeError: If there was an error in the addition process.
            TypeError: If there was an error serializing the payload to JSON.
        """
        try:
            milvus_points = [
                MilvusPointAdapter(record).to_dict() for record in records
            ]

            self._client.insert(
                collection_name=self.collection_name,
                data=milvus_points,
                **kwargs,
            )
        except TypeError as e:
            error_msg = f"Failed to serialize record payload to JSON: {e!s}"
            raise TypeError(error_msg) from e
        except Exception as e:
            error_msg = f"Error adding records to Milvus: {e!s}"
            raise RuntimeError(error_msg) from e

    def delete(
        self,
        ids: List[str],
        **kwargs: Any,
    ) -> None:
        r"""Deletes a list of vectors identified by their IDs from the
        storage. If unsure of ids you can first query the collection to grab
        the corresponding data.

        Args:
            ids (List[str]): List of unique identifiers for the vectors to be
                deleted.
            **kwargs (Any): Additional keyword arguments passed to delete.

        Raises:
            RuntimeError: If there is an error during the deletion process.
        """

        self._client.delete(
            collection_name=self.collection_name, pks=ids, **kwargs
        )

    def status(self) -> VectorDBStatus:
        r"""Retrieves the current status of the Milvus collection. This method
        provides information about the collection, including its vector
        dimensionality and the total number of vectors stored.

        Returns:
            VectorDBStatus: An object containing information about the
                collection's status.
        """
        status = self._get_collection_info(self.collection_name)
        return VectorDBStatus(
            vector_dim=status["vector_dim"],
            vector_count=status["vector_count"],
        )

    def _json_object_hook(self, d) -> Any:
        if "__enum__" in d:
            name, member = d["__enum__"].split(".")
            return getattr(CamelJSONEncoder.CAMEL_ENUMS[name], member)
        else:
            return d

    def _process_enum_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process dictionary to convert any "__enum__" entries to their
        proper enum values.

        Args:
            data (Dict[str, Any]): Dictionary potentially containing
                "__enum__" entries

        Returns:
            Dict[str, Any]: Processed dictionary with enum values
        """
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                if "__enum__" in value:
                    # Convert "__enum__" format to actual enum values
                    name, member = value["__enum__"].split(".")
                    result[key] = getattr(
                        CamelJSONEncoder.CAMEL_ENUMS[name], member
                    )
                else:
                    # Process nested dictionaries
                    result[key] = self._process_enum_values(value)
            elif isinstance(value, list):
                # Process lists of dictionaries
                result[key] = [
                    self._process_enum_values(item)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                # Keep other values as is
                result[key] = value
        return result

    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        """Searches for similar vectors in the storage based on the provided
        query, supporting both vector and text search when query_text is
        provided.

        Args:
            query (VectorDBQuery): The query object containing the search
                vector and the number of top similar vectors to retrieve.
                If query_text is provided as an attribute, hybrid search will
                be used.
            **kwargs (Any): Additional keyword arguments passed to search.

        Returns:
            List[VectorDBQueryResult]: A list of vectors retrieved from the
                storage based on similarity to the query vector and/or text.
        """

        from pymilvus import AnnSearchRequest, WeightedRanker

        # Use hybrid search if enabled and query_text is provided
        if (
            self.hybrid_search_config['enable']
            and hasattr(query, 'query_text')
            and query.query_text
        ):
            # Create search parameters for vector search
            vector_search_param = {
                "data": [query.query_vector],
                "anns_field": "dense",
                "param": {"metric_type": "IP", "params": {"nprobe": 10}},
                "limit": query.top_k,
            }
            vector_request = AnnSearchRequest(**vector_search_param)

            # Create search parameters for text search
            text_search_param = {
                "data": [query.query_text],
                "anns_field": "sparse",
                "param": {
                    "metric_type": "BM25",
                },
                "limit": query.top_k,
            }
            text_request = AnnSearchRequest(**text_search_param)

            # Get weights from instance configuration
            vector_weight = self.hybrid_search_config['vector_weight']
            text_weight = self.hybrid_search_config['text_weight']

            # Combine both search requests with the weights from configuration
            requests = [vector_request, text_request]
            ranker = WeightedRanker(vector_weight, text_weight)

            # Execute hybrid search
            search_result = self._client.hybrid_search(
                collection_name=self.collection_name,
                reqs=requests,
                ranker=ranker,
                limit=query.top_k,
                output_fields=['dense', 'payload'],
                **kwargs,
            )

        else:
            search_result = self._client.search(
                collection_name=self.collection_name,
                data=[query.query_vector],
                limit=query.top_k,
                output_fields=['dense', 'payload'],
                **kwargs,
            )

        query_results = []
        for point in search_result:
            entry = point[0]
            record_id = str(entry['id'])
            distance = entry['distance']
            payload = entry['entity'].get('payload', '')
            vector = entry['entity'].get('dense')

            try:
                if isinstance(payload, str) and payload:
                    payload_dict = json.loads(
                        payload, object_hook=self._json_object_hook
                    )
                elif isinstance(payload, dict):
                    payload_dict = payload
                else:
                    payload_dict = {"payload": str(payload) if payload else ""}

                # Process enum values that might be in dictionary format
                payload_dict = self._process_enum_values(payload_dict)

                # Process role fields for backward compatibility
                self._process_role_fields(payload_dict)

            except Exception as e:
                payload_dict = {"error": str(e), "raw": str(payload)}

            query_results.append(
                VectorDBQueryResult.create(
                    similarity=distance,
                    id=record_id,
                    payload=payload_dict,
                    vector=vector,
                )
            )

        return query_results

    def _process_role_fields(
        self, payload_dict: Dict[str, Any], key_prefix: str = ""
    ) -> None:
        """Recursively process all fields in the payload dictionary to handle
        potential enum fields.

        This function looks for fields that might be Enum values and converts
        them to lowercase to match the expected format during validation.

        Args:
            payload_dict: The dictionary to process
            key_prefix: Current key prefix for nested dictionaries
                (used in recursion)
        """
        # Common enum-related field names that might need lowercase conversion
        enum_field_names = [
            # Role related
            "role",
            "role_at_backend",
            "role_type",
            "type",
            "message_type",
            "sender",
            "receiver",
            "agent_type",
            # Model related
            "model_type",
            "model_platform",
            "embedding_model",
            "audio_model",
            "voice_type",
            "task_type",
            "vector_distance",
            "storage_type",
            "termination_mode",
            "openai_backend_role",
            "openai_image_type",
            "openai_vision_detail_type",
            "open_api_name",
            "jina_return_format",
            "huggingface_repo_type",
        ]

        if not isinstance(payload_dict, dict):
            return

        for key, value in list(payload_dict.items()):
            full_key = f"{key_prefix}.{key}" if key_prefix else key

            # Check if this is an enum-related field and value is a string
            if isinstance(value, str) and (
                key in enum_field_names
                or any(
                    enum_name in key.lower()
                    for enum_name in [
                        'role',
                        'type',
                        'model',
                        'format',
                        'mode',
                        'distance',
                    ]
                )
            ):
                # Convert to lowercase for consistent validation
                payload_dict[key] = value.lower()

            # Recursively process nested dictionaries
            elif isinstance(value, dict):
                self._process_role_fields(value, full_key)

            # Process dictionaries in lists
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._process_role_fields(item, f"{full_key}[{i}]")
                    elif isinstance(item, str) and (
                        key in enum_field_names
                        or any(
                            enum_name in key.lower()
                            for enum_name in [
                                'role',
                                'type',
                                'model',
                                'format',
                                'mode',
                                'distance',
                            ]
                        )
                    ):
                        # Convert string values in lists if they match
                        # enum field patterns
                        value[i] = item.lower()

    def clear(self) -> None:
        r"""Removes all vectors from the Milvus collection. This method
        deletes the existing collection and then recreates it with the same
        schema to effectively remove all stored vectors.
        """
        self._delete_collection(self.collection_name)
        self._create_collection(collection_name=self.collection_name)

    def load(self) -> None:
        r"""Load the collection hosted on cloud service."""
        self._client.load_collection(self.collection_name)

    @property
    def client(self) -> Any:
        r"""Provides direct access to the Milvus client. This property allows
        for direct interactions with the Milvus client for operations that are
        not covered by the `MilvusStorage` class.

        Returns:
            Any: The Milvus client instance.
        """
        return self._client
