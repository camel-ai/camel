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
import re
from typing import Dict, List, Optional

from surrealdb import Surreal
from surrealdb.data.types.record_id import RecordID

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


class SurrealStorage(BaseVectorStorage):
    @dependencies_required('surrealdb')
    def __init__(
        self,
        *,
        url: str = "ws://localhost:8000/rpc",
        table: str = "vector_store",
        vector_dim: int = 786,
        distance: VectorDistance = VectorDistance.COSINE,
        namespace: str = "default",
        database: str = "demo",
        user: str = "root",
        password: str = "root",
    ) -> None:
        r"""
        Initialize SurrealStorage with connection settings and ensure
        the target table exists.

        Args:
            url (str): WebSocket URL for connecting to SurrealDB.
            table (str): Name of the table used for vector storage.
            vector_dim (int): Dimensionality of the stored vectors.
            distance (VectorDistance): Distance metric for similarity searches.
            namespace (str): SurrealDB namespace to use.
            database (str): SurrealDB database name.
            user (str): Username for authentication.
            password (str): Password for authentication.
        """
        self.url = url
        self.table = table
        self.ns = namespace
        self.db = database
        self.user = user
        self.password = password
        self.vector_dim = vector_dim
        self.distance = distance
        self._check_and_create_table()
        self._surreal_client = Surreal(self.url)

    def _table_exists(self) -> bool:
        r"""
        Check whether the target table exists in the database.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        with Surreal(self.url) as db:
            db.signin({"username": self.user, "password": self.password})
            db.use(self.ns, self.db)
            res = db.query_raw("INFO FOR DB;")
            tables = res['result'][0]['result'].get('tables', {})
            return self.table in tables

    def _get_table_info(self) -> dict[str, int | None]:
        r"""
        Retrieve dimension and record count from the table metadata.

        Returns:
            dict: A dictionary with 'dim' and 'count' keys.
        """
        if not self._table_exists():
            return {"dim": self.vector_dim, "count": 0}
        with Surreal(self.url) as db:
            db.signin({"username": self.user, "password": self.password})
            db.use(self.ns, self.db)
            res = db.query_raw(f"INFO FOR TABLE {self.table};")

            indexes = res['result'][0]['result'].get("indexes", {})

            dim = self.vector_dim
            idx_def = indexes.get("hnsw_idx")
            if idx_def and isinstance(idx_def, str):
                m = re.search(r"DIMENSION\s+(\d+)", idx_def)
                if m:
                    dim = int(m.group(1))
            cnt = db.query_raw(f"SELECT COUNT() FROM {self.table};")
            try:
                count = len(cnt['result'][0]['result'])
            except (KeyError, IndexError, TypeError):
                logger.warning(
                    "Unexpected result format when counting records: %s", cnt
                )
                count = 0

            return {"dim": dim, "count": count}

    def _create_table(self):
        r"""
        Define and create the vector storage table with HNSW index.
        """
        with Surreal(self.url) as db:
            db.signin({"username": self.user, "password": self.password})
            db.use(self.ns, self.db)
            db.query_raw(
                f"""
                DEFINE TABLE $table SCHEMALESS;
                DEFINE FIELD payload    ON {self.table} TYPE object;
                DEFINE FIELD embedding  ON {self.table} TYPE array;
                DEFINE INDEX hnsw_idx   ON {self.table}
                            FIELDS embedding HNSW DIMENSION {self.vector_dim};
                """
            )
        logger.info(f"Table '{self.table}' created successfully.")

    def _drop_table(self):
        r"""
        Drop the vector storage table if it exists.
        """
        with Surreal(self.url) as db:
            db.signin({"username": self.user, "password": self.password})
            db.use(self.ns, self.db)
            db.query_raw(f"REMOVE TABLE IF EXISTS {self.table};")
        logger.info(f"Table '{self.table}' deleted successfully.")

    def _check_and_create_table(self):
        r"""
        Check if the table exists and matches the expected vector dimension.
        If not, create a new table.
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
        r"""
        Validate and convert VectorRecord instances into
        SurrealDB-compatible dictionaries.

        Args:
            records (List[VectorRecord]): List of vector records to insert.

        Returns:
            List[Dict]: Transformed list of dicts ready for insertion.
        """
        validate_data = []
        for record in records:
            record_dict = {
                "payload": record.payload if record.payload else "",
                "embedding": record.vector,
            }
            validate_data.append(record_dict)

        return validate_data

    def query(self, q: VectorDBQuery, **kwargs) -> List[VectorDBQueryResult]:
        r"""
        Perform a top-k similarity search using the configured distance metric.

        Args:
            q (VectorDBQuery): Query containing the query vector
                and top_k value.

        Returns:
            List[VectorDBQueryResult]: Ranked list of matching records
                with similarity scores.
        """
        metric = {
            VectorDistance.COSINE: "cosine",
            VectorDistance.EUCLIDEAN: "euclidean",
            VectorDistance.DOT: "dot",
        }[self.distance]

        metric_func = {
            VectorDistance.COSINE: "vector::similarity::cosine",
            VectorDistance.EUCLIDEAN: "vector::distance::euclidean",
            VectorDistance.DOT: "vector::dot",
        }.get(self.distance)

        if not metric_func:
            raise ValueError(f"Unsupported distance metric: {self.distance}")

        with Surreal(self.url) as db:
            db.signin({"username": self.user, "password": self.password})
            db.use(self.ns, self.db)

            query = f"""
                SELECT payload,
                    {metric_func}(embedding, {q.query_vector}) AS score
                FROM {self.table}
                WHERE embedding <|{q.top_k},{metric}|> {q.query_vector}
                ORDER BY score;
            """

            response = db.query_raw(query)
            results = response["result"][0]

            return [
                VectorDBQueryResult(
                    record=VectorRecord(vector=[], payload=row["payload"]),
                    similarity=1.0 - row["score"]
                    if self.distance == VectorDistance.COSINE
                    else -row["score"],
                )
                for row in results["result"]
            ]

    def add(self, records: List[VectorRecord], **kwargs) -> None:
        r"""
        Insert validated vector records into the SurrealDB table.

        Args:
            records (List[VectorRecord]): List of vector records to add.
        """
        logger.info(
            "Adding %d records to table '%s'.", len(records), self.table
        )
        try:
            with Surreal(self.url) as db:
                db.signin({"username": self.user, "password": self.password})
                db.use(self.ns, self.db)

                validated_records = self._validate_and_convert_records(records)
                for record in validated_records:
                    db.create(self.table, record)

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
        r"""
        Delete specific records by ID or clear the entire table.

        Args:
            ids (Optional[List[str]]): List of record IDs to delete.
            if_all (bool): Whether to delete all records in the table.
        """
        try:
            with Surreal(self.url) as db:
                db.signin({"username": self.user, "password": self.password})
                db.use(self.ns, self.db)

                if if_all:
                    db.delete(self.table, **kwargs)
                    logger.info(
                        f"Deleted all records from table '{self.table}'"
                    )
                    return

                if not ids:
                    raise ValueError(
                        "Either `ids` must be provided or `if_all=True`"
                    )

                for id_str in ids:
                    rec = RecordID(self.table, id_str)
                    db.delete(rec, **kwargs)
                    logger.info(f"Deleted record {rec}")

        except Exception as e:
            logger.exception("Error deleting records from SurrealDB")
            raise RuntimeError(f"Failed to delete records {ids!r}") from e

    def status(self) -> VectorDBStatus:
        r"""
        Retrieve the status of the vector table including dimension and count.

        Returns:
            VectorDBStatus: Object containing vector table metadata.
        """
        status = self._get_table_info()
        return VectorDBStatus(
            vector_dim=status["dim"],
            vector_count=status["count"],
        )

    def clear(self) -> None:
        r"""
        Reset the vector table by dropping and recreating it.
        """
        self._drop_table()
        self._create_table()

    def load(self) -> None:
        r"""Load the collection hosted on cloud service."""
        # SurrealDB doesn't require explicit loading
        pass

    @property
    def client(self) -> "Surreal":
        r"""Provides access to the underlying SurrealDB client."""
        return self._surreal_client
