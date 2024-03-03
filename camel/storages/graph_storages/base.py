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
from typing import Any, Dict, Optional, List


class BaseGraphStorage(ABC):
    r"""An abstract base class for graph storage systems. Provides a
    consistent interface for saving, loading, and clearing data records without
    any loss of information.

    An abstract base class designed to serve as a foundation for various
    key-value storage systems. The class primarily interacts through Python
    dictionaries.

    This class is meant to be inherited by multiple types of key-value storage
    implementations, including, but not limited to, JSON file storage, NoSQL
    databases like MongoDB and Redis, as well as in-memory Python dictionaries.
    """
    @property
    @abstractmethod
    def client(self) -> Any:
        r"""Provides access to the underlying graph storage client."""
        pass

    @property
    @abstractmethod
    def get_schema(self) -> str:
        """Get the schema of the Graph database"""
        pass

    @abstractmethod
    def refresh_schema(self) -> None:
        """Refreshes the graph schema information."""
        pass

    @abstractmethod
    def add(
        self, graph_documents: List[Any], include_source: bool = False
    ) -> None:
        """Take GraphDocument as input as uses it to construct a graph."""
        pass


    @abstractmethod
    def delete(self, subj: str, rel: str, obj: str) -> None:
        """Delete triplet."""
        pass

    @abstractmethod   
    def query(self, query: str, param_map: Optional[Dict[str, Any]] = {}) -> Any:
        """Query the graph store with statement and parameters."""
        pass


