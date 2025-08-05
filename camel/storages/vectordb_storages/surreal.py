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
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.logger import get_logger
from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.types import VectorDistance
from camel.utils import dependencies_required

if TYPE_CHECKING:
    from surrealdb import Surreal  # type: ignore[import-not-found]

logger = get_logger(__name__)


class SurrealStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` using SurrealDB,
    a scalable, distributed database with WebSocket support, for
    efficient vector storage and similarity search.

    SurrealDB official site and documentation can be found at:
    `SurrealDB <https://surrealdb.com>`_

    Args:
        url (str): WebSocket URL for connecting to SurrealDB
            (default: "ws://localhost:8000/rpc").
        table (str): Name of the table used for storing vectors
            (default: "vector_store").
        vector_dim (int): Dimensionality of the stored vectors.
        distance (VectorDistance): Distance metric used for similarity
            comparisons (default: VectorDistance.COSINE).
        namespace (str): SurrealDB namespace to use (default: "default").
        database (str): SurrealDB database name (default: "demo").
        user (str): Username for authentication (default: "root").
        password (str): Password for authentication (default: "root").

    Notes:
        - SurrealDB supports flexible schema and powerful querying capabilities
        via SQL-like syntax over WebSocket.
        - This implementation manages connection setup and ensures the target
        table exists.
        - Suitable for applications requiring distributed vector storage and
        search with real-time updates.
    """

    @dependencies_required('surrealdb')
    def __init__(
        self,
        *,
        url: str = "ws://localhost:8000/rpc",
        table: str = "vector_store",
        vector_dim: int = 786,
        vector_type: str = "F64",
        distance: VectorDistance = VectorDistance.COSINE,
        hnsw_effort: int = 40,
        namespace: str = "default",
        database: str = "demo",
        user: str = "root",
        password: str = "root",
    ) -> None:
        r"""Initialize SurrealStorage with connection settings and ensure
        the target table exists.

        Args:
            url (str): WebSocket URL for connecting to SurrealDB.
                (default: :obj:`"ws://localhost:8000/rpc"`)
            table (str): Name of the table used for vector storage.
                (default: :obj:`"vector_store"`)
            vector_dim (int): Dimensionality of the stored vectors.
                (default: :obj:`786`)
            distance (VectorDistance): Distance metric for similarity
                searches. (default: :obj:`VectorDistance.COSINE`)
            namespace (str): SurrealDB namespace to use.
                (default: :obj:`"default"`)
            database (str): SurrealDB database name.
                (default: :obj:`"demo"`)
            user (str): Username for authentication.
                (default: :obj:`"root"`)
            password (str): Password for authentication.
                (default: :obj:`"root"`)
        """

        from surrealdb import Surreal

        self.url = url
        self.table = table
        self.ns = namespace
        self.db = database
        self.user = user
        self.password = password
        self.vector_dim = vector_dim
        self.vector_type = vector_type
        self.distance = distance
        self._hnsw_effort = hnsw_effort
        self._surreal_client = Surreal(self.url)
        self._surreal_client.signin({"username": user, "password": password})
        self._surreal_client.use(namespace, database)

        self._check_and_create_table()

    def _table_exists(self) -> bool:
        r"""Check whether the target table exists in the database.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        res = self._surreal_client.query("INFO FOR DB;")
        tables = res.get('tables', {})
        logger.debug(f"_table_exists: {res}")
        return self.table in tables

    def _get_table_info(self) -> dict[str, int | None]:
        r"""Retrieve dimension and record count from the table metadata.

        Returns:
            Dict[str, int]: A dictionary with 'dim' and 'count' keys.
        """
        if not self._table_exists():
            return {"dim": self.vector_dim, "count": 0}
        res = self._surreal_client.query(f"INFO FOR TABLE {self.table};")
        logger.debug(f"_get_table_info: {res}")
        indexes = res.get("indexes", {})

        dim = self.vector_dim
        idx_def = indexes.get("hnsw_idx")
        if idx_def and isinstance(idx_def, str):
            m = re.search(r"DIMENSION\s+(\d+)", idx_def)
            if m:
                dim = int(m.group(1))
        cnt = self._surreal_client.query(
            f"SELECT COUNT() FROM ONLY {self.table} GROUP ALL LIMIT 1;"
        )
        count = cnt.get("count", 0)
        return {"dim": dim, "count": count}

    def _create_table(self):
        r"""Define and create the vector storage table with HNSW index.

        Documentation: https://surrealdb.com/docs/surrealdb/reference-guide/
        vector-search#vector-search-cheat-sheet
        """
        if self.distance.value not in ["cosine", "euclidean", "manhattan"]:
            raise ValueError(
                f"Unsupported distance metric: {self.distance.value}"
            )
        surql_query = f"""
        DEFINE TABLE {self.table} SCHEMALESS;
        DEFINE FIELD payload    ON {self.table} FLEXIBLE TYPE object;
        DEFINE FIELD embedding  ON {self.table} TYPE array<float>;
        DEFINE INDEX hnsw_idx   ON {self.table}
                    FIELDS embedding
                    HNSW DIMENSION {self.vector_dim}
                    DIST {self.distance.value}
                    TYPE {self.vector_type}
                    EFC 150 M 12 M0 24;
        """
        logger.debug(f"_create_table query: {surql_query}")
        res = self._surreal_client.query_raw(surql_query)
        logger.debug(f"_create_table response: {res}")
        if "error" in res:
            raise ValueError(f"Failed to create table: {res['error']}")
        logger.info(f"Table '{self.table}' created successfully.")

    def _drop_table(self):
        r"""Drop the vector storage table if it exists."""
        self._surreal_client.query_raw(f"REMOVE TABLE IF EXISTS {self.table};")
        logger.info(f"Table '{self.table}' deleted successfully.")

    def _check_and_create_table(self):
        r"""Check if the table exists and matches the expected vector
        dimension. If not, create a new table.
        """
        if self._table_exists():
            in_dim = self._get_table_info()["dim"]
            if in_dim != self.vector_dim:
                raise ValueError(
                    f"Table {self.table} exists with dimension {in_dim}, "
                    f"expected {self.vector_dim}"
                )
        else:
            self._create_table()

    def _validate_and_convert_records(
        self, records: List[VectorRecord]
    ) -> List[Dict]:
        r"""Validate and convert VectorRecord instances into
        SurrealDB-compatible dictionaries.

        Args:
            records (List[VectorRecord]): List of vector records to insert.

        Returns:
            List[Dict]: Transformed list of dicts ready for insertion.
        """
        validate_data = []
        for record in records:
            if len(record.vector) != self.vector_dim:
                raise ValueError(
                    f"Vector dimension mismatch: expected {self.vector_dim}, "
                    f"got {len(record.vector)}"
                )
            record_dict = {
                "payload": record.payload if record.payload else {},
                "embedding": record.vector,
            }
            validate_data.append(record_dict)

        return validate_data

    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Perform a top-k similarity search using the configured distance
        metric.

        Args:
            query (VectorDBQuery): Query containing the query vector
                and top_k value.

        Returns:
            List[VectorDBQueryResult]: Ranked list of matching records
                with similarity scores.
        """
        surql_query = f"""
            SELECT id, embedding, payload, vector::distance::knn() AS dist
            FROM {self.table}
            WHERE embedding <|{query.top_k},{self._hnsw_effort}|> $vector
            ORDER BY dist;
        """
        logger.debug(
            f"query surql: {surql_query} with $vector = {query.query_vector}"
        )

        response = self._surreal_client.query(
            surql_query, {"vector": query.query_vector}
        )
        logger.debug(f"query response: {response}")

        return [
            VectorDBQueryResult(
                record=VectorRecord(
                    id=row["id"].id,
                    vector=row["embedding"],
                    payload=row["payload"],
                ),
                similarity=1.0 - row["dist"]
                if self.distance == VectorDistance.COSINE
                else -row["score"],
            )
            for row in response
        ]

    def add(self, records: List[VectorRecord], **kwargs) -> None:
        r"""Insert validated vector records into the SurrealDB table.

        Args:
            records (List[VectorRecord]): List of vector records to add.
        """
        logger.info(
            "Adding %d records to table '%s'.", len(records), self.table
        )
        try:
            validated_records = self._validate_and_convert_records(records)
            for record in validated_records:
                self._surreal_client.create(self.table, record)

            logger.info(
                "Successfully added %d records to table '%s'.",
                len(records),
                self.table,
            )
        except Exception as e:
            logger.error(
                "Failed to add records to table '%s': %s",
                self.table,
                str(e),
                exc_info=True,
            )
            raise

    def delete(
        self, ids: Optional[List[str]] = None, if_all: bool = False, **kwargs
    ) -> None:
        r"""Delete specific records by ID or clear the entire table.

        Args:
            ids (Optional[List[str]]): List of record IDs to delete.
            if_all (bool): Whether to delete all records in the table.
        """
        from surrealdb.data.types.record_id import RecordID

        try:
            if if_all:
                self._surreal_client.delete(self.table, **kwargs)
                logger.info(f"Deleted all records from table '{self.table}'")
                return

            if not ids:
                raise ValueError(
                    "Either `ids` must be provided or `if_all=True`"
                )

            for id_str in ids:
                rec = RecordID(self.table, id_str)
                self._surreal_client.delete(rec, **kwargs)
                logger.info(f"Deleted record {rec}")

        except Exception as e:
            logger.exception("Error deleting records from SurrealDB")
            raise RuntimeError(f"Failed to delete records {ids!r}") from e

    def status(self) -> VectorDBStatus:
        r"""Retrieve the status of the vector table including dimension and
        count.

        Returns:
            VectorDBStatus: Object containing vector table metadata.
        """
        status = self._get_table_info()

        dim = status.get("dim")
        count = status.get("count")

        if dim is None or count is None:
            raise ValueError("Vector dimension and count cannot be None")

        return VectorDBStatus(
            vector_dim=dim,
            vector_count=count,
        )

    def clear(self) -> None:
        r"""Reset the vector table by dropping and recreating it."""
        self._drop_table()
        self._create_table()

    def load(self) -> None:
        r"""Load the collection hosted on cloud service."""
        # SurrealDB doesn't require explicit loading
        raise NotImplementedError("SurrealDB does not support loading")

    @property
    def client(self) -> "Surreal":
        r"""Provides access to the underlying SurrealDB client."""
        return self._surreal_client
