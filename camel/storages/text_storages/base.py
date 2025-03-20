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

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

class BaseTextStorage(ABC):
    r"""An abstract base class for text-based storage systems. This class is
    designed to handle text operations with support for user contexts, memory
    persistence, and advanced querying capabilities.

    The class provides a foundation for implementing memory storage systems that
    can:
    1. Store and retrieve memories with context (user, agent, session)
    2. Support both long-term and short-term memory management
    3. Enable semantic search and filtering of memories
    4. Handle structured data with metadata
    5. Support batch operations for memory management

    This class is meant to be inherited by implementations that provide memory
    storage capabilities, such as Mem0, vector databases with memory features,
    or custom memory management systems.
    """

    @abstractmethod
    def add(
        self,
        content: Union[str, List[Dict[str, str]]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        r"""Add a memory or list of memories to the storage.

        Args:
            content (Union[str, List[Dict[str, str]]]): The content to store.
                Can be either a string or a list of message dictionaries.
            **kwargs (Any): Additional implementation-specific parameters.

        Returns:
            Dict[str, Any]: Response containing the operation result.
        """
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        r"""Search for memories using semantic similarity.

        Args:
            query (str): The search query.
            limit (int): Maximum number of results to return.
            **kwargs (Any): Additional implementation-specific parameters.

        Returns:
            List[Dict[str, Any]]: List of matching memories.
        """
        pass

    @abstractmethod
    def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 100,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        r"""Retrieve all memories matching the specified criteria.

        Args:
            filters (Dict[str, Any], optional): Additional filters to apply.
            page (int): Page number for pagination.
            page_size (int): Number of items per page.
            **kwargs (Any): Additional implementation-specific parameters.

        Returns:
            Dict[str, Any]: Paginated list of memories and metadata.
        """
        pass

    @abstractmethod
    def delete(
        self,
        memory_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        r"""Delete memories matching the specified criteria.

        Args:
            memory_ids (List[str], optional): List of specific memory IDs to delete.
            filters (Dict[str, Any], optional): Additional filters for deletion.
            **kwargs (Any): Additional implementation-specific parameters.

        Returns:
            Dict[str, Any]: Response containing the operation result.
        """
        pass

    @abstractmethod
    def update(
        self,
        memory_id: str,
        content: Union[str, Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        r"""Update a specific memory.

        Args:
            memory_id (str): ID of the memory to update.
            content (Union[str, Dict[str, str]]): New content for the memory.
            metadata (Dict[str, Any], optional): New metadata for the memory.
            **kwargs (Any): Additional implementation-specific parameters.

        Returns:
            Dict[str, Any]: Response containing the operation result.
        """
        pass
