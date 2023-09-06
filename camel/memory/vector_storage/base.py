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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from camel.typing import VectorDistance


@dataclass
class VectorRecord():
    """
    Encapsulates information about a vector's unique identifier and its
    payload, which is primarily used as a data transfer object when interacting
    with vector storage operations.

    Attributes:
        id (Optional[str]): A unique identifier for the vector. If not
            provided, an ID will be generated during storage.
        vector (List[float]): The numerical representation of the vector.
        payload (Optional[Dict[str, Any]]): Any additional metadata or
            information related to the vector.
    """
    id: Optional[Union[int, str]] = None
    vector: Optional[List[float]] = None
    payload: Optional[Dict[str, Any]] = None


class BaseVectorStorage(ABC):
    """
    An abstract base class representing a vector storage system.
    Implementations of this class will define how vectors are stored,
    retrieved, and managed in various vector databases or storage systems.

    The class provides abstract methods for common operations like creating
    collections, adding vectors, deleting vectors, and searching for similar
    vectors.

    Note:
        Implementations of this class are expected to provide concrete
        implementations for all the abstract methods. The methods defined are
        common operations one would perform on a vector storage system.
    """

    @abstractmethod
    def create_collection(
        self,
        collection: str,
        size: int,
        distance: VectorDistance = VectorDistance.DOT,
        **kwargs,
    ):
        """
        Creates a new collection in the database.

        Args:
            collection (str): Name of the collection to be created.
            size (int): Dimensionality of vectors to be stored in this
                collection.
            distance (VectorDistance, optional): The distance metric to be used
                for vector similarity. (default: :obj:`VectorDistance.DOT`)
            **kwargs: Additional keyword arguments.
        """
        ...

    @abstractmethod
    def check_collection(self, collection: str) -> Dict[str, Any]:
        """
        Retrieves details of an existing collection.

        Args:
            collection (str): Name of the collection to be checked.

        Returns:
            Dict[str, Any]: A dictionary containing details about the
                collection.
        """
        ...

    @abstractmethod
    def add_vectors(
        self,
        collection: str,
        vectors: List[VectorRecord],
    ) -> List[VectorRecord]:
        """
        Adds a list of vectors to the specified collection.

        Args:
            collection (str): Name of the collection.
            vectors (List[VectorRecord]): List of vectors to be added. If a
                vector does not have an 'id', a new unique ID will be generated
                for it.

        Returns:
            List[VectorRecord]: The list of vectors that were successfully
                added. Vectors in this list will have an 'id' attribute, even
                if it was not provided in the original input.
        """
        ...

    @abstractmethod
    def delete_collection(
        self,
        collection: str,
        **kwargs,
    ) -> None:
        """
        Deletes an existing collection from the database.

        Args:
            collection (str): Name of the collection to be deleted.
            **kwargs: Additional keyword arguments.
        """
        ...

    @abstractmethod
    def delete_vectors(
        self,
        collection: str,
        vectors: List[VectorRecord],
    ) -> List[VectorRecord]:
        """
        Deletes a list of vectors from the specified collection.

        Args:
            collection (str): Name of the collection.
            vectors (List[VectorRecord]): List of vectors to be deleted. If a
                vector does not have an 'id', the method will attempt to find
                the closest matching vector in the collection and delete it.

        Returns:
            List[VectorRecord]: The list of vectors that were successfully
                deleted. Vectors in this list will always have an 'id'
                attribute, representing either the original ID provided or the
                ID of the closest matching vector that was found and deleted.
        """
        ...

    @abstractmethod
    def search(
        self,
        collection: str,
        query_vector: VectorRecord,
        limit: int = 3,
    ) -> List[VectorRecord]:
        """
        Searches for similar vectors in the specified collection based on a
        query vector.

        Args:
            collection (str): Name of the collection.
            query_vector (VectorRecord): The vector to be used as the search
                query.
            limit (int, optional): The maximum number of similar vectors to
                retrieve. (default: :obj:`3`)

        Returns:
            List[VectorRecord]: A list of vectors retrieved from the collection
                based on similarity to :obj:`query_vector`.
        """
        ...
