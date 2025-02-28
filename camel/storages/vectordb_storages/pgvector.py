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

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.utils import dependencies_required

logger = logging.getLogger(__name__)


class PgVectorDistance(str, Enum):
    """Supported distance metrics in pgvector."""
    L2 = "l2"  
    INNER_PRODUCT = "ip"  
    COSINE = "cosine" 
    L1 = "l1"  


@dependencies_required('psycopg2')
class PgVectorStorage(BaseVectorStorage):
    """An implementation of the BaseVectorStorage for interacting with
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
            PgVectorDistance.L2: "<->",
            PgVectorDistance.INNER_PRODUCT: "<#>",
            PgVectorDistance.COSINE: "<=>",
            PgVectorDistance.L1: "<+>",
        }

        self._conn = None
        self._create_connection()
        self._check_and_create_table()

    def _generate_table_name(self) -> str:
        """Generates a table name using the current timestamp."""
        return f"vectors_{datetime.now().isoformat()}"

    def _create_connection(self) -> None:
        """Creates a connection to the PostgreSQL database."""
        import psycopg2
        try:
            self._conn = psycopg2.connect(**self.connection_params)
            # Enable pgvector extension
            with self._conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            self._conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to PostgreSQL: {e}")

    def _check_and_create_table(self) -> None:
        """Checks if the specified table exists and creates it if it doesn't."""
        try:
            with self._conn.cursor() as cur:
                # Check if table exists
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                    """,
                    (self.table_name,),
                )
                exists = cur.fetchone()[0]

                if not exists:
                    # Create table
                    cur.execute(
                        f"""
                        CREATE TABLE {self.table_name} (
                            id VARCHAR PRIMARY KEY,
                            embedding vector({self.vector_dim}),
                            metadata JSONB
                        );
                        """
                    )
                    self._conn.commit()
                else:
                    # Verify vector dimension
                    cur.execute(
                        f"""
                        SELECT vector_dims(embedding) 
                        FROM {self.table_name} 
                        LIMIT 1;
                        """
                    )
                    result = cur.fetchone()
                    if result and result[0] != self.vector_dim:
                        raise ValueError(
                            f"Vector dimension of existing table "
                            f"'{self.table_name}' ({result[0]}) "
                            f"differs from given dim ({self.vector_dim})."
                        )
        except Exception as e:
            raise RuntimeError(f"Failed to create/check table: {e}")

    def add(
        self,
        records: List[VectorRecord],
        **kwargs: Any,
    ) -> None:
        """Saves vector records to PostgreSQL."""
        from psycopg2.extras import Json
        try:
            with self._conn.cursor() as cur:
                for record in records:
                    cur.execute(
                        f"""
                        INSERT INTO {self.table_name} (id, embedding, metadata)
                        VALUES (%s, %s, %s);
                        """,
                        (record.id, record.vector, Json(record.payload))
                    )
                self._conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to add records: {e}")

    def delete(
        self,
        ids: List[str],
        **kwargs: Any,
    ) -> None:
        """Deletes vectors by their IDs from PostgreSQL."""
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    f"""
                    DELETE FROM {self.table_name}
                    WHERE id = ANY(%s);
                    """,
                    (ids,)
                )
                self._conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to delete records: {e}")

    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        """Searches for similar vectors in PostgreSQL."""
        try:
            with self._conn.cursor() as cur:
                operator = self._distance_operators[self.distance]
                cur.execute(
                    f"""
                    SELECT id, embedding, metadata, (embedding {operator} %s) as distance
                    FROM {self.table_name}
                    ORDER BY embedding {operator} %s
                    LIMIT %s;
                    """,
                    (query.query_vector, query.query_vector, query.top_k)
                )
                results = []
                for id_, vector, metadata, distance in cur.fetchall():
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
        """Removes all vectors from the table."""
        try:
            with self._conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {self.table_name};")
                self._conn.commit()
        except Exception as e:
            raise RuntimeError(f"Failed to clear table: {e}")

    def load(self) -> None:
        """No-op for PostgreSQL as data is persisted by default."""
        pass

    def status(self) -> VectorDBStatus:
        """Returns the status of the vector database."""
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

    def client(self):
        """Returns the underlying PostgreSQL connection."""
        return self._conn

    def __del__(self):
        """Closes the PostgreSQL connection when the object is destroyed."""
        if self._conn:
            self._conn.close()