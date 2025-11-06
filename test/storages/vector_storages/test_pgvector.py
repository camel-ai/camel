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
from unittest.mock import MagicMock, patch

import pytest

from camel.storages import VectorDBQuery, VectorRecord
from camel.storages.vectordb_storages.pgvector import PgVectorStorage
from camel.types import VectorDistance


@pytest.fixture
def mock_pgvector_conn():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    return mock_conn, mock_cursor


@patch("psycopg.connect")
@patch("pgvector.psycopg.register_vector")
def test_pgvector_init(mock_register, mock_connect, mock_pgvector_conn):
    mock_conn, _ = mock_pgvector_conn
    mock_connect.return_value = mock_conn
    storage = PgVectorStorage(
        vector_dim=4,
        conn_info={"host": "localhost"},
        table_name="test_vectors",
        distance=VectorDistance.COSINE,
    )
    assert storage.vector_dim == 4
    assert storage.table_name == "test_vectors"
    assert storage.distance == VectorDistance.COSINE
    mock_register.assert_called_once()
    mock_connect.assert_called_once()


def test_pgvector_add(mock_pgvector_conn):
    mock_conn, mock_cursor = mock_pgvector_conn
    with (
        patch("psycopg.connect", return_value=mock_conn),
        patch("pgvector.psycopg.register_vector"),
    ):
        storage = PgVectorStorage(4, {"host": "localhost"})
        mock_cursor.executemany.reset_mock()
        records = [
            VectorRecord(
                id="1", vector=[0.1, 0.2, 0.3, 0.4], payload={"a": 1}
            ),
            VectorRecord(
                id="2", vector=[0.5, 0.6, 0.7, 0.8], payload={"b": 2}
            ),
        ]
        storage.add(records)
        assert mock_cursor.executemany.call_count == 1
        mock_conn.commit.assert_called()


def test_pgvector_query(mock_pgvector_conn):
    mock_conn, mock_cursor = mock_pgvector_conn
    mock_cursor.fetchall.return_value = [
        ("1", [0.1, 0.2, 0.3, 0.4], {"a": 1}, 0.01),
    ]
    with (
        patch("psycopg.connect", return_value=mock_conn),
        patch("pgvector.psycopg.register_vector"),
    ):
        storage = PgVectorStorage(4, {"host": "localhost"})
        mock_cursor.execute.reset_mock()
        query = VectorDBQuery(query_vector=[0.1, 0.2, 0.3, 0.4], top_k=1)
        results = storage.query(query)
        assert len(results) == 1
        assert results[0].record.id == "1"
        assert results[0].record.vector == [0.1, 0.2, 0.3, 0.4]
        assert results[0].record.payload == {"a": 1}
        assert results[0].similarity == 0.01


def test_pgvector_delete(mock_pgvector_conn):
    mock_conn, mock_cursor = mock_pgvector_conn
    with (
        patch("psycopg.connect", return_value=mock_conn),
        patch("pgvector.psycopg.register_vector"),
    ):
        storage = PgVectorStorage(4, {"host": "localhost"})
        mock_cursor.execute.reset_mock()
        storage.delete(["1", "2"])
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called()


def test_pgvector_status(mock_pgvector_conn):
    mock_conn, mock_cursor = mock_pgvector_conn
    mock_cursor.fetchone.return_value = [5]
    with (
        patch("psycopg.connect", return_value=mock_conn),
        patch("pgvector.psycopg.register_vector"),
    ):
        storage = PgVectorStorage(4, {"host": "localhost"})
        mock_cursor.execute.reset_mock()
        status = storage.status()
        assert status.vector_dim == 4
        assert status.vector_count == 5


def test_pgvector_clear(mock_pgvector_conn):
    mock_conn, mock_cursor = mock_pgvector_conn
    with (
        patch("psycopg.connect", return_value=mock_conn),
        patch("pgvector.psycopg.register_vector"),
    ):
        storage = PgVectorStorage(4, {"host": "localhost"})
        mock_cursor.execute.reset_mock()
        storage.clear()
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called()


def test_pgvector_empty_add_delete(mock_pgvector_conn):
    mock_conn, mock_cursor = mock_pgvector_conn
    with (
        patch("psycopg.connect", return_value=mock_conn),
        patch("pgvector.psycopg.register_vector"),
    ):
        storage = PgVectorStorage(4, {"host": "localhost"})
        mock_cursor.execute.reset_mock()
        storage.add([])
        storage.delete([])
        # Should not call execute for empty add/delete
        assert not mock_cursor.execute.called
