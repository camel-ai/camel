# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class VectorDistance(Enum):
    DOT = 1
    COSINE = 2
    EUCLIDEAN = 3


@dataclass
class VectorRecord:
    r"""Encapsulates information about a vector's unique identifier and its
    payload, which is primarily used as a data transfer object when saving
    to vector storage.

    Attributes:
        vector (List[float]): The numerical representation of the vector.
        id (str, optional): A unique identifier for the vector. If not
            provided, an random uuid will be assigned.
        payload (Optional[Dict[str, Any]], optional): Any additional metadata
            or information related to the vector. (default: :obj:`None`)
    """
    vector: List[float]
    id: str = field(default_factory=lambda: str(uuid4()))
    payload: Optional[Dict[str, Any]] = None


@dataclass
class VectorDBQuery:
    r"""Represents a query to a vector database.

    Attributes:
        query_vector (List[float]): The numerical representation of the query
            vector.
        top_k (int, optional): The number of top similar vectors to retrieve
            from the database. (default: `1`)
    """
    query_vector: List[float]
    top_k: int = 1


@dataclass
class VectorDBQueryResult:
    r"""Encapsulates the result of a query against a vector database.

    Attributes:
        record (VectorRecord): The target vector record.
        similarity (float): The similarity score between the query vector and
            the record.
    """
    record: VectorRecord
    similarity: float

    @classmethod
    def construct(
        cls,
        similarity: float,
        vector: List[float],
        id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> "VectorDBQueryResult":
        r"""A class method to construct a `VectorDBQueryResult` instance."""
        return cls(
            record=VectorRecord(vector, id, payload),
            similarity=similarity,
        )


class BaseVectorStorage(ABC):
    r"""An abstract base class for vector storage systems."""

    @abstractmethod
    def validate_vector_dimensions(
        self,
        records: List[VectorRecord],
    ) -> None:
        r"""Validates that all vectors in the given list have the same
        dimensionality as the collection.

        Args:
            records (List[VectorRecord]): A list of vector records to validate.

        Raises:
            ValueError: If any vector has a different dimensionality than
            the collection.
        """
        pass

    @abstractmethod
    def add(
        self,
        records: List[VectorRecord],
        **kwargs: Any,
    ) -> None:
        r"""Saves a list of vector records to the storage.

        Args:
            records (List[VectorRecord]): List of vector records to be saved.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there is an error during the saving process.
        """
        pass

    @abstractmethod
    def delete(
        self,
        ids: List[str],
        **kwargs: Any,
    ) -> None:
        r"""Deletes a list of vectors identified by their IDs from the storage.

        Args:
            ids (List[str]): List of unique identifiers for the vectors to be
                deleted.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there is an error during the deletion process.
        """
        pass

    @abstractmethod
    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in the storage based on the provided query.

        Args:
            query (VectorDBQuery): The query object containing the search
                vector and the number of top similar vectors to retrieve.
            **kwargs (Any): Additional keyword arguments.

        Returns:
            List[VectorDBQueryResult]: A list of vectors retrieved from the
                storage based on similarity to the query vector.
        """
        pass

    def simple_query(
        self,
        vector: List[float],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        r"""A simple interface for vector query

        Args:
            vector (List[float]): The search vector.
            top_k (int): The number of top similer vectors.

        Returns:
            List[List[Dict[str, Any]]]: A list of vector payloads retrieved
                from the storage based on similarity to the query vector.
        """
        results = self.query(VectorDBQuery(vector, top_k))
        return [
            result.record.payload for result in results
            if result.record.payload is not None
        ]

    @abstractmethod
    def clear(self) -> None:
        r"""Remove all vectors from the storage."""
        pass

    @property
    @abstractmethod
    def client(self) -> Any:
        r"""Provides access to the underlying client used for interacting with
        the vector storage system.
        """
        pass
