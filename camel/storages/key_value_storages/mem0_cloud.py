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
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from camel.memories.records import MemoryRecord
from camel.messages import BaseMessage
from camel.storages.key_value_storages import BaseKeyValueStorage
from camel.types import OpenAIBackendRole, RoleType

logger = logging.getLogger(__name__)


class Mem0Storage(BaseKeyValueStorage):
    r"""A concrete implementation of the :obj:`BaseKeyValueStorage` using Mem0
    as the backend. This storage system uses Mem0's text capabilities to store,
    search, and manage text with context.

    Args:
        agent_id (str): Default agent ID to associate memories with.
        api_key (str, optional): The API key for authentication. If not
            provided, will try to get from environment variable MEM0_API_KEY
            (default: :obj:`None`).
        user_id (str, optional): Default user ID to associate memories with
            (default: :obj:`None`).
        metadata (Dict[str, Any], optional): Default metadata to include with
            all memories (default: :obj:`None`).

    References:
        https://docs.mem0.ai
    """

    def __init__(
        self,
        agent_id: str,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            from mem0 import MemoryClient
        except ImportError as exc:
            logger.error(
                "Please install `mem0` first. You can install it by "
                "running `pip install mem0ai`."
            )
            raise exc

        self.api_key = api_key or os.getenv("MEM0_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key must be provided either through constructor "
                "or MEM0_API_KEY environment variable."
            )

        self.client = MemoryClient(api_key=self.api_key)
        self.agent_id = agent_id
        self.user_id = user_id
        self.metadata = metadata or {}

    def _prepare_options(
        self,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        r"""Helper method to prepare options for Mem0 API calls.

        Args:
            agent_id (Optional[str], optional): Agent ID to use (default:
                :obj:`None`).
            user_id (Optional[str], optional): User ID to use (default:
                :obj:`None`).
            metadata (Optional[Dict[str, Any]], optional): Additional metadata
                to include (default: :obj:`None`).
            **kwargs (Any): Additional keyword arguments.

        Returns:
            Dict[str, Any]: Prepared options dictionary for API calls.
        """
        options = {
            "agent_id": agent_id or self.agent_id,
            "user_id": user_id or self.user_id,
            "metadata": {**self.metadata, **(metadata or {})},
            "output_format": "v1.1",
            **kwargs,
        }
        return {k: v for k, v in options.items() if v is not None}

    def _prepare_filters(
        self,
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        r"""Helper method to prepare filters for Mem0 API calls.

        Args:
            agent_id (Optional[str], optional): Agent ID to filter by
                (default: :obj:`None`).
            user_id (Optional[str], optional): User ID to filter by (default:
                :obj:`None`).
            filters (Optional[Dict[str, Any]], optional): Additional filters
                (default: :obj:`None`).

        Returns:
            Dict[str, Any]: Prepared filters dictionary for API calls.
        """
        base_filters: Dict[str, Any] = {"AND": []}
        if filters:
            base_filters["AND"].append(filters)
        if agent_id or self.agent_id:
            base_filters["AND"].append({"agent_id": agent_id or self.agent_id})
        if user_id or self.user_id:
            base_filters["AND"].append({"user_id": user_id or self.user_id})
        return base_filters if base_filters["AND"] else {}

    def _prepare_messages(
        self,
        records: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        r"""Prepare messages from records for Mem0 API calls.

        Args:
            records (List[Dict[str, Any]]): List of record dictionaries.

        Returns:
            List[Dict[str, Any]]: List of prepared message dictionaries.
        """
        messages = []
        for record in records:
            content = record["message"]["content"]
            role = record["role_at_backend"].value
            messages.append({"role": role, "content": content})
        return messages

    def save(self, records: List[Dict[str, Any]]) -> None:
        r"""Saves a batch of records to the Mem0 storage system.

        Args:
            records (List[Dict[str, Any]]): A list of dictionaries, where each
                dictionary represents a unique record to be stored.
        """
        try:
            messages = self._prepare_messages(records)

            options = self._prepare_options(
                agent_id=self.agent_id,
                user_id=self.user_id,
                metadata=self.metadata,
            )
            self.client.add(messages, **options)
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            logger.error(f"Error: {e}")

    def load(self) -> List[Dict[str, Any]]:
        r"""Loads all stored records from the Mem0 storage system.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                represents a stored record.
        """
        try:
            filters = self._prepare_filters(
                agent_id=self.agent_id,
                user_id=self.user_id,
            )
            results = self.client.get_all(version="v2", **filters)

            # Transform results into MemoryRecord objects
            transformed_results = []
            for result in results:
                memory_record = MemoryRecord(
                    uuid=UUID(result["id"]),
                    message=BaseMessage(
                        role_name="user",
                        role_type=RoleType.USER,
                        meta_dict={},
                        content=result["memory"],
                    ),
                    role_at_backend=OpenAIBackendRole.USER,
                    extra_info=result.get("metadata", {}),
                    timestamp=datetime.fromisoformat(
                        result["created_at"]
                    ).timestamp(),
                    agent_id=result.get("agent_id", ""),
                )
                transformed_results.append(memory_record.to_dict())

            return transformed_results
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []

    def clear(
        self,
    ) -> None:
        r"""Removes all records from the Mem0 storage system."""
        try:
            filters = self._prepare_filters(
                agent_id=self.agent_id,
                user_id=self.user_id,
            )
            self.client.delete_users(**filters)
        except Exception as e:
            logger.error(f"Error deleting memories: {e}")
            logger.error(f"Error: {e}")
