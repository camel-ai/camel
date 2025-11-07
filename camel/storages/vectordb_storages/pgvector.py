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
from typing import Any, Dict, List, Optional

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

logger = get_logger(__name__)


class PgVectorStorage(BaseVectorStorage):
    r"""PgVectorStorage is an implementation of BaseVectorStorage for
    PostgreSQL with pgvector extension.

    This class provides methods to add, delete, query, and manage vector
    records in a PostgreSQL database using the pgvector extension.
    It supports different distance metrics for similarity search.

    Args:
        vector_dim (int): The dimension of the vectors to be stored.
        conn_info (Dict[str, Any]): Connection information for
            psycopg2.connect.
        table_name (str, optional): Name of the table to store vectors.
            (default: :obj:`None`)
        distance (VectorDistance, optional): Distance metric for vector
            comparison. (default: :obj:`VectorDistance.COSINE`)
    """

    @dependencies_required('psycopg', 'pgvector')
    def __init__(
        self,
        vector_dim: int,
        conn_info: Dict[str, Any],
        table_name: Optional[str] = None,
        distance: VectorDistance = VectorDistance.COSINE,
        **kwargs: Any,
    ) -> None:
        r"""Initialize PgVectorStorage.

        Args:
            vector_dim (int): The dimension of the vectors.
            conn_info (Dict[str, Any]): Connection info for psycopg2.connect.
            table_name (str, optional): Table name. (default: :obj:`None`)
            distance (VectorDistance, optional): Distance metric.
                (default: :obj:`VectorDistance.COSINE`)
        """
        import psycopg
        from pgvector.psycopg import register_vector

        if vector_dim <= 0:
            raise ValueError("vector_dim must be positive")

        self.vector_dim = vector_dim
        self.conn_info = conn_info
        self.table_name = table_name or 'vectors'
        self.distance = distance

        try:
            self._conn = psycopg.connect(**conn_info)
            register_vector(self._conn)
            self._ensure_table()
            self._ensure_index()
        except Exception as e:
            logger.error(f"Failed to initialize PgVectorStorage: {e}")
            raise

    def _ensure_table(self) -> None:
        r"""Ensure the vector table exists in the database.
        Creates the table if it does not exist.
        """
        try:
            from psycopg.sql import SQL, Identifier, Literal

            with self._conn.cursor() as cur:
                query = SQL("""
                    CREATE TABLE IF NOT EXISTS {table} (
                        id VARCHAR PRIMARY KEY,
                        vector vector({dim}),
                        payload JSONB
                    )
                """).format(
                    table=Identifier(self.table_name),
                    dim=Literal(self.vector_dim),
                )
                cur.execute(query)
                self._conn.commit()
        except Exception as e:
            logger.error(f"Failed to create table {self.table_name}: {e}")
            raise

    def _ensure_index(self) -> None:
        r"""Ensure vector similarity search index exists for better
        performance.
        """
        try:
            from psycopg.sql import SQL, Identifier

            with self._conn.cursor() as cur:
                index_name = f"{self.table_name}_vector_idx"
                query = SQL("""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table} 
                    USING hnsw (vector vector_cosine_ops)
                """).format(
                    index_name=Identifier(index_name),
                    table=Identifier(self.table_name),
                )
                cur.execute(query)
                self._conn.commit()
        except Exception as e:
            logger.warning(f"Failed to create vector index: {e}")

    def add(self, records: List[VectorRecord], **kwargs: Any) -> None:
        r"""Add or update vector records in the database.

        Args:
            records (List[VectorRecord]): List of vector records to
                add or update.
        """
        if not records:
            return

        try:
            with self._conn.cursor() as cur:
                # Use batch insert for better performance
                batch_data = []
                for rec in records:
                    if len(rec.vector) != self.vector_dim:
                        raise ValueError(
                            f"Vector dimension mismatch: expected "
                            f"{self.vector_dim}, got {len(rec.vector)}"
                        )

                    batch_data.append(
                        (
                            rec.id,
                            rec.vector,
                            json.dumps(rec.payload)
                            if rec.payload is not None
                            else None,
                        )
                    )

                # Use executemany for efficient batch insert
                from psycopg.sql import SQL, Identifier

                query = SQL("""
                    INSERT INTO {table} (id, vector, payload)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET 
                    vector=EXCLUDED.vector, 
                    payload=EXCLUDED.payload
                """).format(table=Identifier(self.table_name))

                cur.executemany(query, batch_data)
                self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            logger.error(f"Failed to add records: {e}")
            raise

    def delete(self, ids: List[str], **kwargs: Any) -> None:
        r"""Delete vector records from the database by their IDs.

        Args:
            ids (List[str]): List of record IDs to delete.
        """
        from psycopg.sql import SQL, Identifier

        if not ids:
            return

        try:
            with self._conn.cursor() as cur:
                query = SQL("DELETE FROM {table} WHERE id = ANY(%s)").format(
                    table=Identifier(self.table_name)
                )
                cur.execute(query, (ids,))
                self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            logger.error(f"Failed to delete records: {e}")
            raise

    def query(
        self, query: VectorDBQuery, **kwargs: Any
    ) -> List[VectorDBQueryResult]:
        r"""Query the database for the most similar vectors to the given
        query vector.

        Args:
            query (VectorDBQuery): Query object containing the query
                vector and top_k.
            **kwargs (Any): Additional keyword arguments for the query.

        Returns:
            List[VectorDBQueryResult]: List of query results sorted by
                similarity.
        """
        if len(query.query_vector) != self.vector_dim:
            raise ValueError(
                f"Query vector dimension mismatch: "
                f"expected {self.vector_dim}, got {len(query.query_vector)}"
            )

        try:
            with self._conn.cursor() as cur:
                # Fix distance metric mapping
                metric_info = {
                    VectorDistance.COSINE: ('<=>', 'ASC'),  # Cosine distance
                    VectorDistance.EUCLIDEAN: (
                        '<->',
                        'ASC',
                    ),  # Euclidean distance
                    VectorDistance.DOT: (
                        '<#>',
                        'DESC',
                    ),  # Negative dot product (higher is better)
                }

                if self.distance not in metric_info:
                    raise ValueError(
                        f"Unsupported distance metric: {self.distance}"
                    )

                metric, order = metric_info[self.distance]

                from psycopg.sql import SQL, Identifier, Literal

                query_sql = SQL("""
                    SELECT id, vector, payload, (vector {} %s::vector) 
                    AS similarity
                    FROM {}
                    ORDER BY similarity {}
                    LIMIT %s
                """).format(
                    Literal(metric),
                    Identifier(self.table_name),
                    Literal(order),
                )

                cur.execute(query_sql, (query.query_vector, query.top_k))
                results = []
                for row in cur.fetchall():
                    id, vector, payload, similarity = row
                    results.append(
                        VectorDBQueryResult.create(
                            similarity=float(similarity),
                            vector=list(vector),
                            id=id,
                            payload=payload,
                        )
                    )
                return results
        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            raise

    def status(self, **kwargs: Any) -> VectorDBStatus:
        r"""Get the status of the vector database, including vector
        dimension and count.

        Args:
            **kwargs (Any): Additional keyword arguments for the query.

        Returns:
            VectorDBStatus: Status object with vector dimension and count.
        """
        try:
            with self._conn.cursor() as cur:
                from psycopg.sql import SQL, Identifier

                query = SQL('SELECT COUNT(*) FROM {}').format(
                    Identifier(self.table_name)
                )
                cur.execute(query)
                result = cur.fetchone()
                count = result[0] if result else 0
                return VectorDBStatus(
                    vector_dim=self.vector_dim, vector_count=count
                )
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            raise

    def clear(self) -> None:
        r"""Remove all vectors from the storage by truncating the table."""
        try:
            with self._conn.cursor() as cur:
                from psycopg.sql import SQL, Identifier

                query = SQL("TRUNCATE TABLE {table}").format(
                    table=Identifier(self.table_name)
                )
                cur.execute(query)
                self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            logger.error(f"Failed to clear table: {e}")
            raise

    def load(self) -> None:
        r"""Load the collection hosted on cloud service (no-op for pgvector).
        This method is provided for interface compatibility.
        """
        # For PostgreSQL local/managed instances, no loading is required
        pass

    def close(self) -> None:
        r"""Close the database connection."""
        if hasattr(self, '_conn') and self._conn:
            try:
                self._conn.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")

    def __del__(self) -> None:
        r"""Ensure connection is closed when object is destroyed."""
        self.close()

    @property
    def client(self) -> Any:
        r"""Provides access to the underlying vector database client.

        Returns:
            Any: The underlying psycopg connection object.
        """
        return self._conn
