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
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.types import VectorDistance
from camel.utils import dependencies_required

if TYPE_CHECKING:
    from dakera import DakeraClient

logger = logging.getLogger(__name__)

# Maps CAMEL's distance metric to Dakera's ``distance_metric`` query parameter.
DISTANCE_TYPE_MAP = {
    VectorDistance.DOT: "dot_product",
    VectorDistance.COSINE: "cosine",
    VectorDistance.EUCLIDEAN: "euclidean",
}


class DakeraStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with
    Dakera, a self-hosted memory server that exposes a REST vector API.

    Dakera runs beside the application (single container plus object storage,
    provisioned via the ``dakera-ai/dakera-deploy`` docker-compose) and stores
    vectors in server-side namespaces. This backend lets a CAMEL
    :obj:`VectorDBBlock` persist agent memory across sessions without standing
    up a separate managed vector database. The detailed information about
    Dakera is available at: `Dakera <https://dakera.ai>`_

    Args:
        vector_dim (int): The dimension of storing vectors.
        collection_name (Optional[str], optional): Name of the Dakera
            namespace used to store vectors. If not provided, it is set to the
            current time in iso format. (default: :obj:`None`)
        url (Optional[str], optional): The base URL of the Dakera server. If
            not provided, falls back to the ``DAKERA_API_URL`` environment
            variable and finally to ``"http://localhost:3000"``.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key (``dk-...``) used to
            authenticate against the Dakera server. If not provided, falls back
            to the ``DAKERA_API_KEY`` environment variable.
            (default: :obj:`None`)
        distance (VectorDistance, optional): The distance metric used when
            querying the namespace. (default: :obj:`VectorDistance.COSINE`)
        index_type (str, optional): The index type to create the namespace
            with (e.g. ``"hnsw"``, ``"flat"``, ``"ivf"``).
            (default: :obj:`"hnsw"`)
        delete_collection_on_del (bool, optional): Flag to determine if the
            namespace should be deleted upon object destruction.
            (default: :obj:`False`)
        **kwargs (Any): Additional keyword arguments for initializing
            :obj:`DakeraClient`.

    Raises:
        ImportError: If `dakera` package is not installed.
    """

    @dependencies_required('dakera')
    def __init__(
        self,
        vector_dim: int,
        collection_name: Optional[str] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        distance: VectorDistance = VectorDistance.COSINE,
        index_type: str = "hnsw",
        delete_collection_on_del: bool = False,
        **kwargs: Any,
    ) -> None:
        from dakera import DakeraClient

        self.vector_dim = vector_dim
        self.distance = distance
        self.index_type = index_type
        self.collection_name = (
            collection_name or self._generate_collection_name()
        )
        self.delete_collection_on_del = delete_collection_on_del

        resolved_url = (
            url or os.environ.get("DAKERA_API_URL") or "http://localhost:3000"
        )
        resolved_api_key = api_key or os.environ.get("DAKERA_API_KEY")

        self._client: "DakeraClient" = DakeraClient(
            resolved_url,
            api_key=resolved_api_key,
            **kwargs,
        )

        self._check_and_create_collection()

    def __del__(self) -> None:
        r"""Deletes the namespace if :obj:`delete_collection_on_del` is set to
        :obj:`True`.
        """
        if getattr(self, "delete_collection_on_del", False):
            try:
                self._delete_collection(self.collection_name)
            except Exception as e:
                logger.error(
                    "Failed to delete namespace "
                    f"'{self.collection_name}' during destruction: {e}"
                )

    def _generate_collection_name(self) -> str:
        r"""Generates a collection name if user doesn't provide one."""
        return datetime.now().isoformat()

    def _collection_exists(self, collection_name: str) -> bool:
        r"""Returns whether the namespace exists on the server."""
        from dakera import NotFoundError

        try:
            self._client.get_namespace(collection_name)
            return True
        except NotFoundError:
            return False

    def _check_and_create_collection(self) -> None:
        r"""Ensures the namespace exists with a matching vector dimension,
        creating it if necessary.
        """
        from dakera import NotFoundError

        try:
            info = self._client.get_namespace(self.collection_name)
        except NotFoundError:
            self._client.create_namespace(
                self.collection_name,
                dimensions=self.vector_dim,
                index_type=self.index_type,
            )
            return

        if info.dimensions is not None and info.dimensions != self.vector_dim:
            raise ValueError(
                f"Namespace '{self.collection_name}' has dimension "
                f"{info.dimensions}, which is different from the given "
                f"vector dimension {self.vector_dim}."
            )

    def _delete_collection(self, collection_name: str) -> None:
        r"""Deletes the namespace from the server."""
        self._client.delete_namespace(collection_name)

    def add(
        self,
        records: List[VectorRecord],
        **kwargs: Any,
    ) -> None:
        r"""Saves a list of vector records to the Dakera namespace.

        Args:
            records (List[VectorRecord]): List of vector records to be saved.
            **kwargs (Any): Additional keyword arguments passed to the Dakera
                client's ``upsert`` call.

        Raises:
            RuntimeError: If there is an error during the saving process.
        """
        from dakera import DakeraError, Vector

        vectors = [
            Vector(
                id=record.id,
                values=record.vector,
                metadata=record.payload or {},
            )
            for record in records
        ]
        try:
            self._client.upsert(
                self.collection_name, vectors=vectors, **kwargs
            )
        except DakeraError as e:
            raise RuntimeError(
                f"Failed to add vectors to Dakera namespace "
                f"'{self.collection_name}': {e}"
            ) from e

    def delete(
        self,
        ids: List[str],
        **kwargs: Any,
    ) -> None:
        r"""Deletes a list of vectors identified by their IDs from the
        namespace.

        Args:
            ids (List[str]): List of unique identifiers for the vectors to be
                deleted.
            **kwargs (Any): Additional keyword arguments passed to the Dakera
                client's ``delete`` call.

        Raises:
            RuntimeError: If there is an error during the deletion process.
        """
        from dakera import DakeraError

        try:
            self._client.delete(self.collection_name, ids=ids, **kwargs)
        except DakeraError as e:
            raise RuntimeError(
                f"Failed to delete vectors from Dakera namespace "
                f"'{self.collection_name}': {e}"
            ) from e

    def status(self) -> VectorDBStatus:
        r"""Returns the status (dimension and vector count) of the namespace.

        Returns:
            VectorDBStatus: The vector database status.
        """
        info = self._client.get_namespace(self.collection_name)
        return VectorDBStatus(
            vector_dim=info.dimensions or self.vector_dim,
            vector_count=info.vector_count,
        )

    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in the namespace based on the provided
        query.

        Args:
            query (VectorDBQuery): The query object containing the search
                vector and the number of top similar vectors to retrieve.
            **kwargs (Any): Additional keyword arguments passed to the Dakera
                client's ``query`` call (e.g. a metadata ``filter``).

        Returns:
            List[VectorDBQueryResult]: A list of vectors retrieved from the
                namespace based on similarity to the query vector.
        """
        from dakera import DistanceMetric

        search_result = self._client.query(
            self.collection_name,
            vector=query.query_vector,
            top_k=query.top_k,
            include_values=True,
            include_metadata=True,
            distance_metric=DistanceMetric(DISTANCE_TYPE_MAP[self.distance]),
            **kwargs,
        )
        return [
            VectorDBQueryResult.create(
                similarity=result.score,
                id=result.id,
                payload=result.metadata,
                vector=result.values or [],
            )
            for result in search_result.results
        ]

    def clear(self) -> None:
        r"""Remove all vectors from the namespace."""
        self._client.delete(self.collection_name, delete_all=True)

    def load(self) -> None:
        r"""Load the collection hosted on cloud service.

        Dakera namespaces are served remotely and are always available, so no
        action is required.
        """
        pass

    @property
    def client(self) -> "DakeraClient":
        r"""Provides access to the underlying Dakera client."""
        return self._client
