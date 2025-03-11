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
from typing import Any, Dict, List, Optional

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.types.enums import VectorDistance
from camel.utils import dependencies_required


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
        distance (VectorDistance, optional): The distance metric for vector
            comparison (default: :obj:`VectorDistance.COSINE`)
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
        distance: VectorDistance = VectorDistance.COSINE,
    ) -> None:
        r"""Initialize a new PgVectorStorage instance.

        This method initializes the connection to PostgreSQL and ensures the
        required table and extensions are set up correctly.
        """
        self.vector_dim = vector_dim
        self.collection_name = (
            collection_name
            if collection_name is not None
            else self._generate_collection_name()
        )
        self.distance = distance
        self._distance_operators = {
            VectorDistance.COSINE: "<=>",
            VectorDistance.EUCLIDEAN: "<->",
            VectorDistance.DOT: "<#>",
            VectorDistance.MANHATTAN: "<+>",
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
        r"""Get information about a specific collection.

        This method retrieves metadata about a collection, including its
        vector dimension and other properties.

        Args:
            collection_name (str): Name of the collection to get info for.

        Returns:
            Dict[str, Any]: Collection information including:
                - name: Name of the collection
                - vector_dim: Dimension of vectors in the collection

        Raises:
            RuntimeError: If collection does not exist or has no vector column.
        """
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
        r"""Check if collection exists and create it if not.

        Raises:
            RuntimeError: If collection creation fails or vector dimension
                mismatch is detected.
        """
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
        r"""Add vector records to the PostgreSQL collection.

        This method inserts or updates vector records in the collection. If a
        record with the same ID already exists, it will be updated with the
        new vector and metadata.

        Args:
            records (List[VectorRecord]): List of vector records to add.
                Each record should contain an ID, vector, and optional
                metadata.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there is an error during the insertion process.
        """
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
                    if self.distance == VectorDistance.COSINE:
                        similarity = 1 - distance
                    elif self.distance == VectorDistance.DOT:
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

    def create_index(
        self,
        vector_type: str,
        index_type: str = 'ivfflat',
        lists: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        r"""Creates an index for optimizing vector similarity search.

        This method creates a PostgreSQL index for vector similarity search
        using either IVFFlat or HNSW indexing methods. The index type and
        parameters can be configured to optimize for different use cases.

        Args:
            vector_type (str): Type of vector to index. Options are:
                - 'vector': up to 2,000 dimensions
                - 'halfvec': up to 4,000 dimensions
                - 'sparsevec': up to 1,000 non-zero elements
            index_type (str, optional): Type of index to create. Options are:
                - 'ivfflat': IVFFlat index, good for large datasets.
                  Faster to build, uses less memory.
                - 'hnsw': HNSW index, provides better query performance but
                  slower to build and uses more memory.
                (default: :obj:`'ivfflat'`)
            lists (Optional[int], optional): For IVFFlat index, number of
                clusters to create. If None, automatically calculated based
                on table size. (default: :obj:`None`)
            **kwargs: Advanced options for index creation:
                - m (int): HNSW max connections per node
                    (default: :obj:`16`)
                - ef_construction (int): HNSW build accuracy
                    (default: :obj:`64`)
                - ef_search (int): HNSW query accuracy (default: :obj:`40`)
                - maintenance_work_mem (str): Build memory
                    (default: :obj:`'1GB'`)
                - max_parallel_workers (int): Parallel workers
                    (default: :obj:`2`)
        Raises:
            ValueError: If an invalid vector type or index type is provided.
            RuntimeError: If there is an error during index creation.
        """
        # Get default values from kwargs
        m = kwargs.get('m', 16)
        ef_construction = kwargs.get('ef_construction', 64)
        ef_search = kwargs.get('ef_search', 40)
        maintenance_work_mem = kwargs.get('maintenance_work_mem', '1GB')
        workers = kwargs.get('max_parallel_workers', 2)

        # Validate vector type
        valid_vector_types = ['vector', 'halfvec', 'sparsevec']
        if vector_type not in valid_vector_types:
            raise ValueError(
                f"Invalid vector_type: {vector_type}. "
                f"Must be one of {valid_vector_types}"
            )

        # Get operator based on distance metric
        base_ops = {
            VectorDistance.COSINE: 'cosine_ops',
            VectorDistance.EUCLIDEAN: 'l2_ops',
            VectorDistance.DOT: 'ip_ops',
            VectorDistance.MANHATTAN: 'l1_ops',
        }
        ops_suffix = base_ops.get(self.distance)
        if ops_suffix is None:
            raise ValueError(
                f"Unsupported distance metric for indexing: {self.distance}"
            )
        operator = f"{vector_type}_{ops_suffix}"

        try:
            with self._conn.cursor() as cur:
                # Configure build parameters
                cur.execute(
                    f"SET maintenance_work_mem = '{maintenance_work_mem}';"
                )
                cur.execute(
                    f"SET max_parallel_maintenance_workers = {workers};"
                )

                # Drop existing index
                cur.execute(
                    f"DROP INDEX IF EXISTS {self.collection_name}_vector_idx;"
                )

                # Calculate lists for IVFFlat if needed
                if index_type.lower() == 'ivfflat' and lists is None:
                    cur.execute(
                        f"SELECT COUNT(*) FROM {self.collection_name};"
                    )
                    result = cur.fetchone()
                    if result is None:
                        count = 0
                    else:
                        count = result[0]
                    lists = (
                        max(count // 1000, 1)
                        if count <= 1_000_000
                        else max(int(count**0.5), 1)
                    )

                # Create index
                if index_type.lower() == 'ivfflat':
                    cur.execute(f"""
                        CREATE INDEX {self.collection_name}_vector_idx
                        ON {self.collection_name}
                        USING ivfflat (vector {operator})
                        WITH (lists = {lists});
                    """)
                elif index_type.lower() == 'hnsw':
                    cur.execute(f"SET hnsw.ef_search = {ef_search};")
                    cur.execute(f"""
                        CREATE INDEX {self.collection_name}_vector_idx
                        ON {self.collection_name}
                        USING hnsw (vector {operator})
                        WITH (m = {m}, ef_construction = {ef_construction});
                    """)
                else:
                    raise ValueError(
                        f"Unsupported index type: {index_type}. "
                        "Supported types are 'ivfflat' and 'hnsw'."
                    )

                self._conn.commit()

        except Exception as e:
            self._conn.rollback()
            raise RuntimeError(f"Failed to create index: {e}")
