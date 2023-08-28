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
    id: Optional[Union[int, str]] = None
    vector: Optional[List[float]] = None
    payload: Optional[Dict[str, Any]] = None


class BaseVectorStorage(ABC):
    """
    Abstract base class representing the basic operations
    required for long-term memory storage.

    Inherits the fundamental memory operations from BaseMemory.
    Additional long-term specific operations can be added here.
    """

    @abstractmethod
    def create_collection(
        self,
        collection: str,
        size: int,
        distance: VectorDistance,
        **kwargs,
    ):
        """_summary_

        Args:
            collection (str): _description_
            size (int): _description_
            distance (str, optional): _description_. Defaults to "dot".
        """
        ...

    @abstractmethod
    def check_collection(self, collection: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    def add_vectors(
        self,
        collection: str,
        vectors: List[VectorRecord],
    ) -> List[VectorRecord]:
        """
        Archives a message in long-term storage. Archiving may differ
        from standard storage in terms of compression, backup, redundancy, etc.

        Args:
            msg (BaseMessage): The message to be archived.
        """
        ...

    @abstractmethod
    def delete_collection(
        self,
        collection: str,
        **kwargs,
    ) -> None:
        ...

    @abstractmethod
    def delete_vectors(
        self,
        collection: str,
        vectors: List[VectorRecord],
    ) -> List[VectorRecord]:
        """
        Archives a message in long-term storage. Archiving may differ
        from standard storage in terms of compression, backup, redundancy, etc.

        Args:
            msg (BaseMessage): The message to be archived.
        """
        ...

    @abstractmethod
    def search(
        self,
        collection: str,
        query_vector: VectorRecord,
        limit: int,
    ) -> List[VectorRecord]:
        """
        Retrieves an archived message from long-term storage based on its
            identifier.

        Args:
            id (str): The unique identifier of the archived message.

        Returns:
            BaseMessage: The retrieved archived message.
        """
        ...
