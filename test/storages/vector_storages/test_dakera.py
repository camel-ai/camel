# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from unittest.mock import MagicMock, patch

import pytest

from camel.storages import (
    DakeraStorage,
    VectorDBQuery,
    VectorRecord,
)
from camel.types import VectorDistance

# ``dakera`` is an optional runtime dependency loaded lazily by
# ``DakeraStorage`` (it is not in the ``storage``/``all`` extras because
# ``dakera``'s ``requests>=2.33`` pin conflicts with ``arxiv (<3)`` in the
# universal lock). Skip this module when it is not installed.
pytest.importorskip("dakera")


def _namespace_info(vector_count=0, dimensions=4):
    info = MagicMock()
    info.vector_count = vector_count
    info.dimensions = dimensions
    return info


@pytest.fixture
def mock_dakera_client():
    r"""Patches ``DakeraClient`` so no live server is required and yields a
    :obj:`DakeraStorage` wired to the mock client.
    """
    with patch('dakera.DakeraClient') as mock_client_cls:
        client = MagicMock()
        # Namespace already exists with a matching dimension.
        client.get_namespace.return_value = _namespace_info(
            vector_count=0, dimensions=4
        )
        mock_client_cls.return_value = client

        storage = DakeraStorage(
            vector_dim=4,
            collection_name="test_collection",
            url="http://localhost:3000",
            api_key="dk-test",
        )
        yield storage, client


def test_client_initialization(mock_dakera_client):
    with patch('dakera.DakeraClient') as mock_client_cls:
        from dakera import NotFoundError

        client = MagicMock()
        # Namespace missing -> should be created with the given dimension.
        client.get_namespace.side_effect = NotFoundError("missing")
        mock_client_cls.return_value = client

        DakeraStorage(
            vector_dim=8,
            collection_name="fresh",
            url="http://localhost:3000",
            api_key="dk-test",
            index_type="hnsw",
        )
        mock_client_cls.assert_called_once_with(
            "http://localhost:3000", api_key="dk-test"
        )
        client.create_namespace.assert_called_once_with(
            "fresh", dimensions=8, index_type="hnsw"
        )


def test_dimension_mismatch_raises(mock_dakera_client):
    with patch('dakera.DakeraClient') as mock_client_cls:
        client = MagicMock()
        client.get_namespace.return_value = _namespace_info(dimensions=16)
        mock_client_cls.return_value = client

        with pytest.raises(ValueError):
            DakeraStorage(vector_dim=4, collection_name="mismatch")


def test_add_vectors(mock_dakera_client):
    from dakera import Vector

    storage, client = mock_dakera_client
    records = [
        VectorRecord(vector=[0.2, 0.2, 0.2, 0.2], payload={"label": "A"}),
        VectorRecord(vector=[-0.2, -0.2, -0.2, -0.2], payload={"label": "B"}),
    ]
    storage.add(records=records)

    client.upsert.assert_called_once()
    _, kwargs = client.upsert.call_args
    args, _ = client.upsert.call_args
    assert args[0] == "test_collection"
    sent = kwargs["vectors"]
    assert len(sent) == 2
    assert all(isinstance(v, Vector) for v in sent)
    assert sent[0].id == records[0].id
    assert sent[0].values == [0.2, 0.2, 0.2, 0.2]
    assert sent[0].metadata == {"label": "A"}


def test_add_wraps_errors(mock_dakera_client):
    from dakera import DakeraError

    storage, client = mock_dakera_client
    client.upsert.side_effect = DakeraError("boom")
    with pytest.raises(RuntimeError):
        storage.add(records=[VectorRecord(vector=[0.1, 0.1, 0.1, 0.1])])


def test_query_maps_results(mock_dakera_client):
    storage, client = mock_dakera_client

    result = MagicMock()
    result.id = "vec-1"
    result.score = 0.97
    result.metadata = {"label": "A"}
    result.values = [0.2, 0.2, 0.2, 0.2]
    search_result = MagicMock()
    search_result.results = [result]
    client.query.return_value = search_result

    query = VectorDBQuery(query_vector=[0.2, 0.2, 0.2, 0.2], top_k=1)
    results = storage.query(query)

    assert len(results) == 1
    assert results[0].record.id == "vec-1"
    assert results[0].similarity == 0.97
    assert results[0].record.payload == {"label": "A"}
    assert results[0].record.vector == [0.2, 0.2, 0.2, 0.2]

    _, kwargs = client.query.call_args
    assert kwargs["vector"] == [0.2, 0.2, 0.2, 0.2]
    assert kwargs["top_k"] == 1
    assert kwargs["distance_metric"].value == "cosine"


def test_query_distance_metric_mapping(mock_dakera_client):
    storage, client = mock_dakera_client
    storage.distance = VectorDistance.EUCLIDEAN
    search_result = MagicMock()
    search_result.results = []
    client.query.return_value = search_result

    storage.query(VectorDBQuery(query_vector=[0.0, 0.0, 0.0, 0.0], top_k=3))
    _, kwargs = client.query.call_args
    assert kwargs["distance_metric"].value == "euclidean"


def test_delete_vectors(mock_dakera_client):
    storage, client = mock_dakera_client
    storage.delete(ids=["vec-1", "vec-2"])
    client.delete.assert_called_once_with(
        "test_collection", ids=["vec-1", "vec-2"]
    )


def test_status(mock_dakera_client):
    storage, client = mock_dakera_client
    client.get_namespace.return_value = _namespace_info(
        vector_count=5, dimensions=4
    )
    status = storage.status()
    assert status.vector_count == 5
    assert status.vector_dim == 4


def test_clear(mock_dakera_client):
    storage, client = mock_dakera_client
    storage.clear()
    client.delete.assert_called_once_with("test_collection", delete_all=True)


def test_load_is_noop(mock_dakera_client):
    storage, _ = mock_dakera_client
    # Remote namespaces are always available; load() must not raise.
    assert storage.load() is None


def test_client_property(mock_dakera_client):
    storage, client = mock_dakera_client
    assert storage.client is client
