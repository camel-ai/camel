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
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from pyobvector.client import ObVecClient

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.utils import dependencies_required

logger = logging.getLogger(__name__)


class OceanBaseStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with
    OceanBase Vector Database.

    Args:
        vector_dim (int): The dimension of storing vectors.
        table_name (str): Name for the table in OceanBase.
        uri (str): Connection URI for OceanBase (host:port).
            (default: :obj:`"127.0.0.1:2881"`)
        user (str): Username for connecting to OceanBase.
            (default: :obj:`"root@test"`)
        password (str): Password for the user. (default: :obj:`""`)
        db_name (str): Database name in OceanBase.
            (default: :obj:`"test"`)
        distance (Literal["l2", "cosine"], optional): The distance metric for
            vector comparison. Options: "l2", "cosine". (default: :obj:`"l2"`)
        delete_table_on_del (bool, optional): Flag to determine if the
            table should be deleted upon object destruction.
            (default: :obj:`False`)
        **kwargs (Any): Additional keyword arguments for initializing
            `ObVecClient`.

    Raises:
        ImportError: If `pyobvector` package is not installed.
    """

    @dependencies_required('pyobvector')
    def __init__(
        self,
        vector_dim: int,
        table_name: str,
        uri: str = "127.0.0.1:2881",
        user: str = "root@test",
        password: str = "",
        db_name: str = "test",
        distance: Literal["l2", "cosine"] = "l2",
        delete_table_on_del: bool = False,
        **kwargs: Any,
    ) -> None:
        from pyobvector.client import (
            ObVecClient,
        )
        from pyobvector.client.index_param import (
            IndexParams,
        )
        from pyobvector.schema import VECTOR
        from sqlalchemy import JSON, Column, Integer

        self.vector_dim: int = vector_dim
        self.table_name: str = table_name
        self.distance: Literal["l2", "cosine"] = distance
        self.delete_table_on_del: bool = delete_table_on_del

        # Create client
        self._client: ObVecClient = ObVecClient(
            uri=uri, user=user, password=password, db_name=db_name, **kwargs
        )

        # Map distance to distance function in OceanBase
        self._distance_func_map: Dict[str, str] = {
            "cosine": "cosine_distance",
            "l2": "l2_distance",
        }

        # Check or create table with vector index
        if not self._client.check_table_exists(self.table_name):
            # Define table schema
            columns: List[Column] = [
                Column("id", Integer, primary_key=True, autoincrement=True),
                Column("embedding", VECTOR(vector_dim)),
                Column("metadata", JSON),
            ]

            # Create table
            self._client.create_table(
                table_name=self.table_name, columns=columns
            )

            # Create vector index
            index_params: IndexParams = IndexParams()
            index_params.add_index(
                field_name="embedding",
                index_type="hnsw",
                index_name="embedding_idx",
                distance=self.distance,
                m=16,
                ef_construction=256,
            )

            # Get the first index parameter
            first_index_param = next(iter(index_params), None)
            if first_index_param is not None:
                self._client.create_vidx_with_vec_index_param(
                    table_name=self.table_name, vidx_param=first_index_param
                )

            logger.info(f"Created table {self.table_name} with vector index")
        else:
            logger.info(f"Using existing table {self.table_name}")

    def __del__(self):
        r"""Deletes the table if :obj:`delete_table_on_del` is set to
        :obj:`True`.
        """
        if hasattr(self, "delete_table_on_del") and self.delete_table_on_del:
            try:
                self._client.drop_table_if_exist(self.table_name)
                logger.info(f"Deleted table {self.table_name}")
            except Exception as e:
                logger.error(f"Failed to delete table {self.table_name}: {e}")

    def add(
        self,
        records: List[VectorRecord],
        batch_size: int = 100,
        **kwargs: Any,
    ) -> None:
        r"""Saves a list of vector records to the storage.

        Args:
            records (List[VectorRecord]): List of vector records to be saved.
            batch_size (int): Number of records to insert each batch.
                Larger batches are more efficient but use more memory.
                (default: :obj:`100`)
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there is an error during the saving process.
            ValueError: If any vector dimension doesn't match vector_dim.
        """

        if not records:
            return

        try:
            # Convert records to OceanBase format
            data: List[Dict[str, Any]] = []
            for i, record in enumerate(records):
                # Validate vector dimensions
                if len(record.vector) != self.vector_dim:
                    raise ValueError(
                        f"Vector at index {i} has dimension "
                        f"{len(record.vector)}, expected {self.vector_dim}"
                    )

                item: Dict[str, Any] = {
                    "embedding": record.vector,
                    "metadata": record.payload or {},
                }
                # If id is specified, use it
                if record.id:
                    try:
                        # If id is numeric, use it directly
                        item["id"] = int(record.id)
                    except ValueError:
                        # If id is not numeric, store it in payload
                        item["metadata"]["_id"] = record.id

                data.append(item)

                # Batch insert when reaching batch_size
                if len(data) >= batch_size:
                    self._client.insert(self.table_name, data=data)
                    data = []

            # Insert any remaining records
            if data:
                self._client.insert(self.table_name, data=data)

        except ValueError as e:
            # Re-raise ValueError for dimension mismatch
            raise e
        except Exception as e:
            error_msg = f"Failed to add records to OceanBase: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def delete(
        self,
        ids: List[str],
        **kwargs: Any,
    ) -> None:
        r"""Deletes a list of vectors identified by their IDs from the storage.

        Args:
            ids (List[str]): List of unique identifiers for the vectors to
                be deleted.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there is an error during the deletion process.
        """
        if not ids:
            return

        try:
            numeric_ids: List[int] = []
            non_numeric_ids: List[str] = []

            # Separate numeric and non-numeric IDs
            for id_val in ids:
                try:
                    numeric_ids.append(int(id_val))
                except ValueError:
                    non_numeric_ids.append(id_val)

            # Delete records with numeric IDs
            if numeric_ids:
                self._client.delete(self.table_name, ids=numeric_ids)

            # Delete records with non-numeric IDs stored in metadata
            if non_numeric_ids:
                from sqlalchemy import text

                for id_val in non_numeric_ids:
                    self._client.delete(
                        self.table_name,
                        where_clause=[
                            text(f"metadata->>'$.._id' = '{id_val}'")
                        ],
                    )
        except Exception as e:
            error_msg = f"Failed to delete records from OceanBase: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def status(self) -> VectorDBStatus:
        r"""Returns status of the vector database.

        Returns:
            VectorDBStatus: The vector database status.
        """
        try:
            # Get count of records
            result = self._client.perform_raw_text_sql(
                f"SELECT COUNT(*) FROM {self.table_name}"
            )
            count: int = result.fetchone()[0]

            return VectorDBStatus(
                vector_dim=self.vector_dim, vector_count=count
            )
        except Exception as e:
            error_msg = f"Failed to get status from OceanBase: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in the storage based on the
        provided query.

        Args:
            query (VectorDBQuery): The query object containing the search
                vector and the number of top similar vectors to retrieve.
            **kwargs (Any): Additional keyword arguments.

        Returns:
            List[VectorDBQueryResult]: A list of vectors retrieved from the
                storage based on similarity to the query vector.

        Raises:
            RuntimeError: If there is an error during the query process.
            ValueError: If the query vector dimension does not match the
                storage dimension.
        """
        from sqlalchemy import func

        try:
            # Get distance function name
            distance_func_name: str = self._distance_func_map.get(
                self.distance, "l2_distance"
            )

            distance_func = getattr(func, distance_func_name)

            # Validate query vector dimensions
            if len(query.query_vector) != self.vector_dim:
                raise ValueError(
                    f"Query vector dimension {len(query.query_vector)} "
                    f"does not match storage dimension {self.vector_dim}"
                )

            results = self._client.ann_search(
                table_name=self.table_name,
                vec_data=query.query_vector,
                vec_column_name="embedding",
                distance_func=distance_func,
                with_dist=True,
                topk=query.top_k,
                output_column_names=["id", "embedding", "metadata"],
            )

            # Convert results to VectorDBQueryResult format
            query_results: List[VectorDBQueryResult] = []
            for row in results:
                try:
                    result_dict: Dict[str, Any] = dict(row._mapping)

                    # Extract data
                    id_val: str = str(result_dict["id"])

                    # Handle vector - ensure it's a proper list of floats
                    vector: Any = result_dict.get("embedding")
                    if isinstance(vector, str):
                        # If vector is a string, try to parse it
                        try:
                            if vector.startswith('[') and vector.endswith(']'):
                                # Remove brackets and split by commas
                                vector = [
                                    float(x.strip())
                                    for x in vector[1:-1].split(',')
                                ]
                        except (ValueError, TypeError) as e:
                            logger.warning(
                                f"Failed to parse vector string: {e}"
                            )

                    # Ensure we have a proper vector
                    if (
                        not isinstance(vector, list)
                        or len(vector) != self.vector_dim
                    ):
                        logger.warning(
                            f"Invalid vector format, using zeros: {vector}"
                        )
                        vector = [0.0] * self.vector_dim

                    # Ensure metadata is a dictionary
                    metadata: Dict[str, Any] = result_dict.get("metadata", {})
                    if not isinstance(metadata, dict):
                        # Convert to dict if it's not already
                        try:
                            if isinstance(metadata, str):
                                metadata = json.loads(metadata)
                            else:
                                metadata = {"value": metadata}
                        except Exception:
                            metadata = {"value": str(metadata)}

                    distance_value: Optional[float] = None
                    for key in result_dict:
                        if (
                            key.endswith(distance_func_name)
                            or distance_func_name in key
                        ):
                            distance_value = float(result_dict[key])
                            break

                    if distance_value is None:
                        # If we can't find the distance, use a default value
                        logger.warning(
                            "Could not find distance value in query results, "
                            "using default"
                        )
                        distance_value = 0.0

                    similarity: float = self._convert_distance_to_similarity(
                        distance_value
                    )

                    # Check if the id is stored in metadata
                    if isinstance(metadata, dict) and "_id" in metadata:
                        id_val = metadata.pop("_id")

                    # Create query result
                    query_results.append(
                        VectorDBQueryResult.create(
                            similarity=similarity,
                            vector=vector,
                            id=id_val,
                            payload=metadata,
                        )
                    )
                except Exception as e:
                    logger.warning(f"Failed to process result row: {e}")
                    continue

            return query_results
        except Exception as e:
            error_msg = f"Failed to query OceanBase: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def _convert_distance_to_similarity(self, distance: float) -> float:
        r"""Converts distance to similarity score based on distance metric."""
        # Ensure distance is non-negative
        distance = max(0.0, distance)

        if self.distance == "cosine":
            # Cosine distance = 1 - cosine similarity
            # Ensure similarity is between 0 and 1
            return max(0.0, min(1.0, 1.0 - distance))
        elif self.distance == "l2":
            import math

            # Exponential decay function for L2 distance
            return math.exp(-distance)
        else:
            # Default normalization, ensure result is between 0 and 1
            return max(0.0, min(1.0, 1.0 - min(1.0, distance)))

    def clear(self) -> None:
        r"""Remove all vectors from the storage."""
        try:
            self._client.delete(self.table_name)
            logger.info(f"Cleared all records from table {self.table_name}")
        except Exception as e:
            error_msg = f"Failed to clear records from OceanBase: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def load(self) -> None:
        r"""Load the collection hosted on cloud service."""
        # OceanBase doesn't require explicit loading
        pass

    @property
    def client(self) -> "ObVecClient":
        r"""Provides access to underlying OceanBase vector database client."""
        return self._client
