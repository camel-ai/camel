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

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from camel.storages.vectordb_storages.base import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)


class PgVectorDistance(str, Enum):
    r"""Supported distance metrics in pgvector 0.8.0.

    Attributes:
        L2 (str): Euclidean distance (L2 norm)
        INNER_PRODUCT (str): Inner product distance
        COSINE (str): Cosine distance
        L1 (str): Manhattan distance (L1 norm)
    """
    L2 = "l2"
    INNER_PRODUCT = "ip"
    COSINE = "cosine"
    L1 = "l1"


class PgVectorStorage(BaseVectorStorage):
    r"""An implementation of the BaseVectorStorage for interacting with
    PostgreSQL with pgvector extension.

    Args:
        vector_dim (int): The dimension of storing vectors.
        connection_params (Dict[str, Any]): PostgreSQL connection parameters
            (host, port, database, user, password).
        table_name (Optional[str], optional): Name for the table in PostgreSQL.
            If not provided, set it to the current time with iso format.
            (default: None)
        distance (PgVectorDistance, optional): The distance metric for vector
            comparison (default: PgVectorDistance.COSINE)
    """

    @dependencies_required('psycopg')
    def __init__(
        self,
        vector_dim: int,
        connection_params: Dict[str, Any],
        table_name: Optional[str] = None,
        distance: PgVectorDistance = PgVectorDistance.COSINE,
        **kwargs: Any,
    ) -> None:
        self.vector_dim = vector_dim
        self.connection_params = connection_params
        self.table_name = table_name or self._generate_table_name()
        self.distance = distance

        # Distance operator mapping
        self._distance_operators = {
            PgVectorDistance.L2: "<->",  # Euclidean distance
            PgVectorDistance.INNER_PRODUCT: "<#>",  # (negative) inner product
            PgVectorDistance.COSINE: "<=>",  # cosine distance
            PgVectorDistance.L1: "<+>",  # Manhattan distance
        }

        import psycopg
        self._conn = psycopg.connect(**connection_params)
        self._check_and_create_table()

    def _generate_table_name(self) -> str:
        r"""Generates a table name based on current timestamp.

        Returns:
            str: Generated table name.
        """
        return f"vectors_{datetime.now().isoformat()}"

    def _check_and_create_table(self) -> None:
        r"""Checks if the specified table exists and creates it if it doesn't.

        Raises:
            RuntimeError: If there is an error during table creation.
        """
        try:
            with self._conn.cursor() as cur:
                # Create vector extension if not exists
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                # Create table if not exists
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id TEXT PRIMARY KEY,
                        vector vector({self.vector_dim}),
                        metadata JSONB
                    );
                """)
                self._conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to create table: {e}")

    def add(
        self,
        records: List[VectorRecord],
        **kwargs: Any,
    ) -> None:
        r"""Saves a list of vector records to PostgreSQL using bulk insert with
        upsert.

        Args:
            records (List[VectorRecord]): List of vector records to be saved.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there is an error during the saving process.
        """
        try:
            with self._conn.cursor() as cur:
                for record in records:
                    cur.execute(
                        f"""
                        INSERT INTO {self.table_name} (id, vector, metadata)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (id)
                        DO UPDATE SET vector = EXCLUDED.vector,
                                    metadata = EXCLUDED.metadata;
                        """, (
                            record.id,
                            record.vector,
                            record.payload,
                        ))
                self._conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to add records: {e}")

    def delete(
        self,
        ids: List[str],
        **kwargs: Any,
    ) -> None:
        r"""Deletes vectors by their IDs from PostgreSQL.

        Args:
            ids (List[str]): List of unique identifiers for the vectors to be
                deleted.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there is an error during the deletion process.
        """
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    DELETE FROM {self.table_name}
                    WHERE id = ANY(%s);
                    """, (ids,))
                self._conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to delete records: {e}")

    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in PostgreSQL.

        Args:
            query (VectorDBQuery): The query object containing the search
                vector and the number of top similar vectors to retrieve.
            **kwargs (Any): Additional keyword arguments.

        Returns:
            List[VectorDBQueryResult]: A list of vectors retrieved from
                PostgreSQL based on similarity to the query vector.

        Raises:
            RuntimeError: If there is an error during the query process.
        """
        try:
            with self._conn.cursor() as cur:
                operator = self._distance_operators[self.distance]
                cur.execute(
                    f"""
                    SELECT id, vector, metadata, (vector {operator} %s) as distance
                    FROM {self.table_name}
                    ORDER BY vector {operator} %s
                    LIMIT %s;
                    """, (
                        query.query_vector,
                        query.query_vector,
                        query.top_k,
                    ))

                results = []
                for id_, vector_str, metadata, distance in cur.fetchall():
                    # Convert vector string back to list
                    vector = [float(x) for x in vector_str[1:-1].split(',')]
                    record = VectorRecord(
                        id=id_,
                        vector=vector,
                        payload=metadata,
                    )
                    # For inner product, multiply by -1 since <#> returns negative
                    if self.distance == PgVectorDistance.INNER_PRODUCT:
                        distance *= -1
                    # For cosine similarity, convert distance to similarity
                    elif self.distance == PgVectorDistance.COSINE:
                        distance = 1 - distance
                    results.append(VectorDBQueryResult(record=record,
                                                     similarity=distance))
                return results
        except Exception as e:
            raise RuntimeError(f"Failed to query records: {e}")

    def clear(self) -> None:
        r"""Removes all vectors from the table."""
        try:
            with self._conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {self.table_name};")
                self._conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to clear table: {e}")

    def load(self) -> None:
        r"""No-op for PostgreSQL as data is persisted by default."""
        pass

    def status(self) -> VectorDBStatus:
        r"""Returns the status of the vector database.

        Returns:
            VectorDBStatus: The vector database status.

        Raises:
            RuntimeError: If there is an error getting the status.
        """
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT COUNT(*) FROM {self.table_name};
                    """
                )
                count = cur.fetchone()[0]
                return VectorDBStatus(
                    vector_count=count,
                    vector_dim=self.vector_dim,
                )
        except Exception as e:
            raise RuntimeError(f"Failed to get status: {e}")

    @property
    def client(self):
        r"""Returns the underlying PostgreSQL connection.

        Returns:
            Any: The PostgreSQL connection object.
        """
        return self._conn

    def __del__(self):
        r"""Closes the PostgreSQL connection when the object is destroyed."""
        if self._conn:
            self._conn.close()