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
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.utils import dependencies_required

if TYPE_CHECKING:
    from pytidb import Table, TiDBClient

logger = logging.getLogger(__name__)


class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class TiDBStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with TiDB.

    The detailed information about TiDB is available at:
    `TiDB Vector Search <https://ai.pingcap.com/>`_

    Args:
        vector_dim (int): The dimension of storing vectors.
        url_and_api_key (Optional[Union[Tuple[str, str], str]]): A tuple
            containing the database url and API key for connecting to a TiDB
            cluster. The URL should be in the format:
           "mysql+pymysql://<username>:<password>@<host>:<port>/<db_name>".
           TiDB will not use the API Key, but retains the definition for
           interface compatible.
        collection_name (Optional[str]): Name of the collection.
            The collection name will be used as the table name in TiDB. If not
            provided, set it to the current time with iso format.
        **kwargs (Any): Additional keyword arguments for initializing
            TiDB connection.

    Raises:
        ImportError: If `pytidb` package is not installed.
    """

    @dependencies_required('pytidb')
    def __init__(
        self,
        vector_dim: int,
        collection_name: Optional[str] = None,
        url_and_api_key: Optional[Union[Tuple[str, str], str]] = None,
        **kwargs: Any,
    ) -> None:
        from pytidb import TiDBClient

        self._client: TiDBClient
        database_url = None
        if isinstance(url_and_api_key, str):
            database_url = url_and_api_key
        elif isinstance(url_and_api_key, tuple):
            database_url = url_and_api_key[0]
        self._create_client(database_url, **kwargs)
        self.vector_dim = vector_dim
        self.collection_name = collection_name or self._generate_table_name()
        self._table = self._open_and_create_table()
        self._table_model = self._table.table_model
        self._check_table()

    def _create_client(
        self,
        database_url: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        r"""Initializes the TiDB client with the provided connection details.

        Args:
            database_url (Optional[str]): The database connection string for
                the TiDB server.
            **kwargs: Additional keyword arguments passed to the TiDB client.
        """
        from pytidb import TiDBClient

        self._client = TiDBClient.connect(
            database_url,
            **kwargs,
        )

    def _get_table_model(self, collection_name: str) -> Any:
        from pytidb.schema import Field, TableModel, VectorField
        from sqlalchemy import JSON

        class VectorDBRecord(TableModel):
            id: Optional[str] = Field(None, primary_key=True)
            vector: list[float] = VectorField(self.vector_dim)
            payload: Optional[dict[str, Any]] = Field(None, sa_type=JSON)

        # Notice: Avoid repeated definition warnings by dynamically generating
        # class names.
        return type(
            f"VectorDBRecord_{collection_name}",
            (VectorDBRecord,),
            {"__tablename__": collection_name},
            table=True,
        )

    def _open_and_create_table(self) -> "Table[Any]":
        r"""Opens an existing table or creates a new table in TiDB."""
        table = self._client.open_table(self.collection_name)
        if table is None:
            table = self._client.create_table(
                schema=self._get_table_model(self.collection_name)
            )
        return table

    def _check_table(self):
        r"""Ensuring the specified table matches the specified vector
        dimensionality.
        """
        in_dim = self._get_table_info()["vector_dim"]
        if in_dim != self.vector_dim:
            raise ValueError(
                "Vector dimension of the existing table "
                f'"{self.collection_name}" ({in_dim}) is different from '
                f"the given embedding dim ({self.vector_dim})."
            )

    def _generate_table_name(self) -> str:
        r"""Generates a unique name for a new table based on the current
        timestamp. TiDB table names can only contain alphanumeric
        characters and underscores.

        Returns:
            str: A unique, valid table name.
        """
        timestamp = datetime.now().isoformat()
        transformed_name = re.sub(r'[^a-zA-Z0-9_]', '_', timestamp)
        valid_name = "vectors_" + transformed_name
        return valid_name

    def _get_table_info(self) -> Dict[str, Any]:
        r"""Retrieves details of an existing table.

        Returns:
            Dict[str, Any]: A dictionary containing details about the
                table.
        """
        vector_count = self._table.rows()
        # Get vector dimension from table schema
        columns = self._table.columns()
        dim_value = None
        for col in columns:
            match = re.search(r'vector\((\d+)\)', col.column_type)
            if match:
                dim_value = int(match.group(1))
                break

        # If no vector column found, log a warning
        if dim_value is None:
            logger.warning(
                f"No vector column found in table {self.collection_name}. "
                "This may indicate an incompatible table schema."
            )

        return {
            "vector_count": vector_count,
            "vector_dim": dim_value,
        }

    def _validate_and_convert_vectors(
        self, records: List[VectorRecord]
    ) -> List[Any]:
        r"""Validates and converts VectorRecord instances to VectorDBRecord
        instances.

        Args:
            records (List[VectorRecord]): List of vector records to validate
                and convert.

        Returns:
            List[VectorDBRecord]: A list of VectorDBRecord instances.
        """
        db_records = []
        for record in records:
            payload = record.payload
            if isinstance(payload, str):
                payload = json.loads(payload)
            elif isinstance(payload, dict):
                payload = json.loads(json.dumps(payload, cls=EnumEncoder))
            else:
                payload = None

            db_records.append(
                self._table_model(
                    id=record.id,
                    vector=record.vector,
                    payload=payload,
                )
            )
        return db_records

    def add(
        self,
        records: List[VectorRecord],
        **kwargs,
    ) -> None:
        r"""Adds a list of vectors to the specified table.

        Args:
            records (List[VectorRecord]): List of vectors to be added.
            **kwargs (Any): Additional keyword arguments pass to insert.

        Raises:
            RuntimeError: If there was an error in the addition process.
        """

        db_records = self._validate_and_convert_vectors(records)
        if len(db_records) == 0:
            return
        self._table.bulk_insert(db_records)

        logger.debug(
            f"Successfully added vectors to TiDB table: {self.collection_name}"
        )

    def delete(
        self,
        ids: List[str],
        **kwargs: Any,
    ) -> None:
        r"""Deletes a list of vectors identified by their IDs from the
        storage.

        Args:
            ids (List[str]): List of unique identifiers for the vectors to be
                deleted.
            **kwargs (Any): Additional keyword arguments passed to delete.

        Raises:
            RuntimeError: If there is an error during the deletion process.
        """
        self._table.delete({"id": {"$in": ids}})
        logger.debug(
            f"Successfully deleted vectors from TiDB table "
            f"<{self.collection_name}>"
        )

    def status(self) -> VectorDBStatus:
        r"""Retrieves the current status of the TiDB table.

        Returns:
            VectorDBStatus: An object containing information about the
                table's status.
        """
        status = self._get_table_info()
        return VectorDBStatus(
            vector_dim=status["vector_dim"],
            vector_count=status["vector_count"],
        )

    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in the storage based on the provided
        query.

        Args:
            query (VectorDBQuery): The query object containing the search
                vector and the number of top similar vectors to retrieve.
            **kwargs (Any): Additional keyword arguments passed to search.

        Returns:
            List[VectorDBQueryResult]: A list of vectors retrieved from the
                storage based on similarity to the query vector.
        """
        rows = (
            self._table.search(query.query_vector).limit(query.top_k).to_list()
        )

        query_results = []
        for row in rows:
            query_results.append(
                VectorDBQueryResult.create(
                    similarity=float(row['similarity_score']),
                    id=str(row['id']),
                    payload=row['payload'],
                    vector=row['vector'],
                )
            )
        return query_results

    def clear(self) -> None:
        r"""Removes all vectors from the TiDB table. This method
        deletes the existing table and then recreates it with the same
        schema to effectively remove all stored vectors.
        """
        self._table.truncate()

    def load(self) -> None:
        r"""Load the collection hosted on cloud service."""
        pass

    @property
    def client(self) -> "TiDBClient":
        r"""Provides direct access to the TiDB client.

        Returns:
            Any: The TiDB client instance.
        """
        return self._client
