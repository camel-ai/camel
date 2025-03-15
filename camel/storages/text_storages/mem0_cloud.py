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
from typing import Any, Dict, List, Optional, Union

from camel.storages.text_storages import BaseMemoryStorage

logger = logging.getLogger(__name__)


class Mem0Storage(BaseMemoryStorage):
    r"""A concrete implementation of the :obj:`BaseMemoryStorage` using Mem0
    as the backend. This storage system uses Mem0's memory capabilities to store,
    search, and manage memories with context.

    Args:
        api_key (str, optional): The API key for authentication. If not provided,
            will try to get from environment variable MEM0_API_KEY.
        user_id (str, optional): Default user ID to associate memories with.
        agent_id (str, optional): Default agent ID to associate memories with.
        run_id (str, optional): Default run ID for session-based memories.
        metadata (Dict[str, Any], optional): Default metadata to include with
            all memories.

    References:
        https://docs.mem0.ai
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            from mem0ai import MemoryClient
        except ImportError as exc:
            logger.error(
                "Please install `mem0ai` first. You can install it by "
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
        self.user_id = user_id
        self.agent_id = agent_id
        self.run_id = run_id
        self.metadata = metadata or {}

    def _prepare_options(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Helper method to prepare options for Mem0 API calls."""
        options = {
            "user_id": user_id or self.user_id,
            "agent_id": agent_id or self.agent_id,
            "run_id": run_id or self.run_id,
            "metadata": {**self.metadata, **(metadata or {})},
            **kwargs
        }
        return {k: v for k, v in options.items() if v is not None}

    def _prepare_filters(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Helper method to prepare filters for Mem0 API calls."""
        base_filters = {"AND": []}
        if filters:
            base_filters["AND"].append(filters)
        if user_id or self.user_id:
            base_filters["AND"].append({"user_id": user_id or self.user_id})
        if agent_id or self.agent_id:
            base_filters["AND"].append({"agent_id": agent_id or self.agent_id})
        if run_id or self.run_id:
            base_filters["AND"].append({"run_id": run_id or self.run_id})
        return base_filters if base_filters["AND"] else {}

    def add(
        self,
        content: Union[str, List[Dict[str, str]]],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Add a memory or list of memories to Mem0 storage."""
        try:
            if isinstance(content, str):
                messages = [{"role": "user", "content": content}]
            else:
                messages = content

            options = self._prepare_options(
                user_id=user_id,
                agent_id=agent_id,
                run_id=run_id,
                metadata=metadata,
                **kwargs
            )
            return self.client.add(messages, options)
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return {"error": str(e)}

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Search for memories in Mem0 storage using semantic similarity."""
        try:
            options = self._prepare_options(
                user_id=user_id,
                agent_id=agent_id,
                run_id=run_id,
                version="v2",
                filters=self._prepare_filters(
                    user_id=user_id,
                    agent_id=agent_id,
                    run_id=run_id,
                    filters=filters,
                ),
                limit=limit,
                **kwargs
            )
            results = self.client.search(query, options)
            return results.get("memories", [])
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []

    def get_all(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 100,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Retrieve all memories from Mem0 storage matching criteria."""
        try:
            options = self._prepare_options(
                user_id=user_id,
                agent_id=agent_id,
                run_id=run_id,
                version="v2",
                filters=self._prepare_filters(
                    user_id=user_id,
                    agent_id=agent_id,
                    run_id=run_id,
                    filters=filters,
                ),
                page=page,
                page_size=page_size,
                **kwargs
            )
            return self.client.getAll(options)
        except Exception as e:
            logger.error(f"Error getting memories: {e}")
            return {"memories": [], "total": 0, "page": page, "page_size": page_size}

    def delete(
        self,
        memory_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Delete memories from Mem0 storage."""
        try:
            if memory_ids:
                # Delete specific memories by ID
                return self.client.batchDelete([{"memory_id": id} for id in memory_ids])
            else:
                # Delete memories matching filters
                filters = self._prepare_filters(
                    user_id=user_id,
                    agent_id=agent_id,
                    run_id=run_id,
                    filters=filters,
                )
                return self.client.delete_users(filters)
        except Exception as e:
            logger.error(f"Error deleting memories: {e}")
            return {"error": str(e)}

    def update(
        self,
        memory_id: str,
        content: Union[str, Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Update a specific memory in Mem0 storage."""
        try:
            if isinstance(content, str):
                content = {"role": "user", "content": content}
            update_data = {"memory_id": memory_id, "text": content}
            if metadata:
                update_data["metadata"] = metadata
            return self.client.update(memory_id, update_data)
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            return {"error": str(e)}
