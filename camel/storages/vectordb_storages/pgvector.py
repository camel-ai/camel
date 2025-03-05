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
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.utils import dependencies_required


class PgVectorDistance(str, Enum):
    r"""Supported distance metrics in pgvector 0.8.0.

    Reference:
        https://github.com/pgvector/pgvector/
    """

    L2 = "L2"  # Euclidean distance
    INNER_PRODUCT = "INNER_PRODUCT"  # Inner product
    COSINE = "COSINE"  # Cosine similarity
    L1 = "L1"  # Manhattan distance


class PgVectorStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with
    PostgreSQL with pgvector extension, a vector similarity search solution.

    The detailed information about pgvector is available at:
    `pgvector <https://github.com/pgvector/pgvector/>`_

    Args:
        vector_dim (int): The dimension of storing vectors.
        connection_params (Dict[str, Any]): PostgreSQL connection parameters
            (host, port, database, user, password).
        collection_name (Optional[str], optional): Name for the collection in
            PostgreSQL. If not provided, set it to the current time with iso
            format. (default: :obj:`None`)
        distance (PgVectorDistance, optional): The distance metric for vector
            comparison (default: :obj:`PgVectorDistance.COSINE`)
        **kwargs (Any): Additional keyword arguments for initializing
            PostgreSQL connection.

    Raises:
        ImportError: If `psycopg` package is not installed.
    """

    @dependencies_required('psycopg')
    def __init__(
        self,
        vector_dim: int,
        connection_params: Dict[str, Any],
        collection_name: Optional[str] = None,
        distance: PgVectorDistance = PgVectorDistance.COSINE,
    ) -> None:
        """Initialize PgVectorStorage."""
        self.vector_dim = vector_dim
        self.collection_name = (
            collection_name
            if collection_name is not None
            else self._generate_collection_name()
        )
        self.distance = distance
        self._distance_operators = {
            PgVectorDistance.COSINE: "<=>",
            PgVectorDistance.L2: "<->",
            PgVectorDistance.INNER_PRODUCT: "<#>",
            PgVectorDistance.L1: "<+>",
        }
        import psycopg

        self._conn = psycopg.connect(**connection_params)
        self._check_and_create_collection()

    def _generate_collection_name(self) -> str:
        r"""Generates a collection name based on current timestamp.

        Returns:
            str: Generated collection name.
        """
        return f"vectors_{datetime.now().isoformat()}"

    def _get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        r"""Get collection information."""
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT a.atttypmod
                    FROM pg_attribute a
                    JOIN pg_class c ON a.attrelid = c.oid
                    JOIN pg_type t ON a.atttypid = t.oid
                    WHERE c.relname = %s
                    AND a.attname = 'vector'
                    AND t.typname = 'vector';
                    """,
                    (collection_name,),
                )
                result = cur.fetchone()

                if result is None or result[0] is None:
                    raise RuntimeError(
                        f"No vector column in collection {collection_name}"
                    )

                vector_dim = int(result[0])

                return {"name": collection_name, "vector_dim": vector_dim}
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Failed to get collection info: {e}")

    def _check_and_create_collection(self) -> None:
        r"""Check if collection exists and create it if not."""
        try:
            exists = False
            vector_dim = None

            # First check if table exists
            with self._conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute(
                    """
                    SELECT EXISTS (
                    SELECT FROM pg_tables
                    WHERE schemaname = 'public'
                    AND tablename = %s
                    );
                    """,
                    (self.collection_name,),
                )
                result = cur.fetchone()
                exists = bool(result[0]) if result is not None else False

            # If table exists, check vector dimension
            if exists:
                with self._conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT a.atttypmod
                        FROM pg_attribute a
                        JOIN pg_class c ON a.attrelid = c.oid
                        JOIN pg_type t ON a.atttypid = t.oid
                        WHERE c.relname = %s
                        AND a.attname = 'vector'
                        AND t.typname = 'vector';
                        """,
                        (self.collection_name,),
                    )
                    result = cur.fetchone()
                    if result is None or result[0] is None:
                        raise RuntimeError(
                            f"No vector column in collection "
                            f"{self.collection_name}"
                        )
                    vector_dim = int(result[0])

                    if vector_dim != self.vector_dim:
                        raise RuntimeError(
                            f"Vector dimension mismatch: "
                            f"expected {self.vector_dim}, got {vector_dim}"
                        )
            # If table doesn't exist, create it
            else:
                with self._conn.cursor() as cur:
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {self.collection_name} (
                            id TEXT PRIMARY KEY,
                            vector vector({self.vector_dim}),
                            metadata JSONB
                        );
                        """
                    )
                    self._conn.commit()

        except Exception as e:
            self._conn.rollback()
            raise RuntimeError(f"Failed to create collection: {e}")

    def add(self, records: List[VectorRecord], **kwargs: Any) -> None:
        r"""Add records to the collection."""
        try:
            with self._conn.cursor() as cur:
                cur.executemany(
                    f"""
                    INSERT INTO {self.collection_name} (id, vector, metadata)
                    VALUES (%s, %s::vector, %s::jsonb)
                    ON CONFLICT (id) DO UPDATE 
                    SET vector = EXCLUDED.vector,
                        metadata = EXCLUDED.metadata
                    """,
                    [(r.id, r.vector, json.dumps(r.payload)) for r in records],
                )
                self._conn.commit()
        except Exception as e:
            self._conn.rollback()
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
                    DELETE FROM {self.collection_name}
                    WHERE id = ANY(%s);
                    """,
                    (ids,),
                )
                self._conn.commit()
        except Exception as e:
            self._conn.rollback()
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

            Note:
                The similarity values are normalized to [0, 1] range where
                1 means most similar:
                - For COSINE: Returns cosine similarity in [0, 1]
                - For L2: Returns 1/(1 + distance) in (0, 1]
                - For L1: Returns 1/(1 + distance) in (0, 1]
                - For INNER_PRODUCT: Returns -distance in [0, 1] for normalized
                    vectors
        """
        try:
            with self._conn.cursor() as cur:
                operator = self._distance_operators[self.distance]
                cur.execute(
                    f"""
                    SELECT id, vector, metadata, 
                    (vector {operator} %s::vector) as distance
                    FROM {self.collection_name}
                    ORDER BY distance
                    LIMIT %s;
                    """,
                    (
                        query.query_vector,
                        query.top_k,
                    ),
                )

                results = []
                for id_, vector_str, metadata, distance in cur.fetchall():
                    vector = [float(x) for x in vector_str[1:-1].split(',')]
                    record = VectorRecord(
                        id=id_,
                        vector=vector,
                        payload=metadata,
                    )
                    if self.distance == PgVectorDistance.COSINE:
                        similarity = 1 - distance
                    elif self.distance == PgVectorDistance.INNER_PRODUCT:
                        similarity = (-distance + 1) / 2
                    else:
                        similarity = 1 / (1 + distance)

                    results.append(
                        VectorDBQueryResult(
                            record=record, similarity=similarity
                        )
                    )
                return results
        except Exception as e:
            raise RuntimeError(f"Failed to query records: {e}")

    def status(self) -> VectorDBStatus:
        r"""Returns status of the vector database."""
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT COUNT(*) FROM {self.collection_name};
                    """
                )
                result = cur.fetchone()
                if result is None or result[0] is None:
                    count = 0
                else:
                    count = int(result[0])
                return VectorDBStatus(
                    vector_dim=self.vector_dim, vector_count=count
                )
        except Exception as e:
            raise RuntimeError(f"Failed to get status: {e}")

    def clear(self) -> None:
        r"""Removes all vectors from the collection.

        Raises:
            RuntimeError: If failed to clear collection.
        """
        try:
            with self._conn.cursor() as cur:
                cur.execute(f"TRUNCATE TABLE {self.collection_name};")
                self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            raise RuntimeError(f"Failed to clear collection: {e}")

    def load(self) -> None:
        r"""Load the collection hosted on cloud service.

        Note:
            This is a no-op for PostgreSQL as data is persisted by default.
        """
        pass

    @property
    def client(self) -> Any:
        r"""Returns the underlying PostgreSQL connection.

        Returns:
            Any: The PostgreSQL connection object.
        """
        return self._conn

    def __enter__(self):
        r"""Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        r"""Context manager exit."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def close(self):
        r"""Explicitly close the connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __del__(self):
        r"""Closes the PostgreSQL connection when the object is destroyed."""
        self.close()
