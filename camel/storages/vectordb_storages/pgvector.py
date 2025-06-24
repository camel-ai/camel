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
from typing import Any, Dict, List, Optional

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.types import VectorDistance
from camel.utils import dependencies_required

logger = logging.getLogger(__name__)


class PgVectorStorage(BaseVectorStorage):
    r"""
    PgVectorStorage is an implementation of BaseVectorStorage for PostgreSQL
    with pgvector extension.

    This class provides methods to add, delete, query, and manage vector
    records in a PostgreSQL database using the pgvector extension.
    It supports different distance metrics for similarity search.

    Args:
        vector_dim (int): The dimension of the vectors to be stored.
        conn_info (Dict[str, Any]): Connection information for
            psycopg2.connect.
        table_name (str, optional): Name of the table to store vectors.
            Defaults to 'vectors'.
        distance (VectorDistance, optional): Distance metric for vector
            comparison. Defaults to COSINE.
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
        """
        Initialize PgVectorStorage.

        Args:
            vector_dim (int): The dimension of the vectors.
            conn_info (Dict[str, Any]): Connection info for psycopg2.connect.
            table_name (str, optional): Table name. Defaults to 'vectors'.
            distance (VectorDistance, optional): Distance metric.
                Defaults to COSINE.
        """
        import psycopg
        from pgvector.psycopg import register_vector

        self.vector_dim = vector_dim
        self.conn_info = conn_info
        self.table_name = table_name or 'vectors'
        self.distance = distance
        self._conn = psycopg.connect(**conn_info)
        register_vector(self._conn)
        self._ensure_table()

    def _ensure_table(self):
        """
        Ensure the vector table exists in the database.
        Creates the table if it does not exist.
        """
        with self._conn.cursor() as cur:
            cur.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id VARCHAR PRIMARY KEY,
                    vector vector({self.vector_dim}),
                    payload JSONB
                )
            ''')
            self._conn.commit()

    def add(self, records: List[VectorRecord], **kwargs: Any) -> None:
        """
        Add or update vector records in the database.

        Args:
            records (List[VectorRecord]): List of vector records to
                add or update.
        """
        with self._conn.cursor() as cur:
            for rec in records:
                cur.execute(
                    f"""
                    INSERT INTO {self.table_name} (id, vector, payload)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET 
                    vector=EXCLUDED.vector, 
                    payload=EXCLUDED.payload
                    """,
                    (
                        rec.id,
                        rec.vector,
                        json.dumps(rec.payload)
                        if rec.payload is not None
                        else None,
                    ),
                )
            self._conn.commit()

    def delete(self, ids: List[str], **kwargs: Any) -> None:
        """
        Delete vector records from the database by their IDs.

        Args:
            ids (List[str]): List of record IDs to delete.
        """
        if not ids:
            return
        with self._conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self.table_name} WHERE id = ANY(%s)", (ids,)
            )
            self._conn.commit()

    def query(
        self, query: VectorDBQuery, **kwargs: Any
    ) -> List[VectorDBQueryResult]:
        """
        Query the database for the most similar vectors to the given
        query vector.

        Args:
            query (VectorDBQuery): Query object containing the query
                vector and top_k.

        Returns:
            List[VectorDBQueryResult]: List of query results sorted by
                similarity.
        """
        with self._conn.cursor() as cur:
            metric = {
                VectorDistance.COSINE: '<->',
                VectorDistance.EUCLIDEAN: '<->',
                VectorDistance.DOT: '<#>',
            }[self.distance]
            cur.execute(
                f"""
                SELECT id, vector, payload, (vector {metric} %s::vector) 
                AS similarity
                FROM {self.table_name}
                ORDER BY similarity ASC
                LIMIT %s
                """,
                (query.query_vector, query.top_k),
            )
            results = []
            for row in cur.fetchall():
                id, vector, payload, similarity = row
                results.append(
                    VectorDBQueryResult.create(
                        similarity=similarity,
                        vector=list(vector),
                        id=id,
                        payload=payload,
                    )
                )
            return results

    def status(self, **kwargs: Any) -> VectorDBStatus:
        """
        Get the status of the vector database, including vector
        dimension and count.

        Returns:
            VectorDBStatus: Status object with vector dimension and count.
        """
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            count = cur.fetchone()[0]
            return VectorDBStatus(
                vector_dim=self.vector_dim, vector_count=count
            )

    def clear(self) -> None:
        """
        Remove all vectors from the storage by truncating the table.
        """
        with self._conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {self.table_name}")
            self._conn.commit()

    def load(self) -> None:
        """
        Load the collection hosted on cloud service (no-op for pgvector).
        """
        # For PostgreSQL local/managed, nothing to do
        pass

    @property
    def client(self) -> Any:
        """
        Provides access to the underlying vector database client.

        Returns:
            Any: The underlying psycopg connection object.
        """
        return self._conn
