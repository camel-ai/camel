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
from typing import Any, Dict, List, Literal, Optional
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx

from camel.memories.records import MemoryRecord
from camel.messages import BaseMessage
from camel.storages.key_value_storages.base import BaseKeyValueStorage
from camel.types import OpenAIBackendRole, RoleType

logger = logging.getLogger(__name__)

MemantoMemoryType = Literal[
    "fact",
    "preference",
    "goal",
    "decision",
    "artifact",
    "learning",
    "event",
    "instruction",
    "relationship",
    "context",
    "observation",
    "commitment",
    "error",
]

_RECALL_PAGE_SIZE = 100

_ROLE_NAME_MAP = {
    OpenAIBackendRole.USER: "user",
    OpenAIBackendRole.ASSISTANT: "assistant",
    OpenAIBackendRole.SYSTEM: "system",
    OpenAIBackendRole.DEVELOPER: "developer",
    OpenAIBackendRole.TOOL: "tool",
    OpenAIBackendRole.FUNCTION: "function",
}


class MemantoRESTClient:
    r"""REST client for the Memanto memory API.

    Args:
        agent_id (str): Memanto agent identifier.
        base_url (str, optional): Memanto server URL. Defaults to
            :obj:`MEMANTO_BASE_URL` or ``http://localhost:8000``.
        timeout (float, optional): HTTP request timeout in seconds.
            (default: :obj:`30.0`)
    """

    def __init__(
        self,
        agent_id: str,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        self.agent_id = agent_id
        self.base_url = (
            base_url or os.getenv("MEMANTO_BASE_URL", "http://localhost:8000")
        ).rstrip("/")
        self._client = httpx.Client(timeout=timeout)
        self._session_token: Optional[str] = None
        self.activate_session()

    def activate_session(self) -> str:
        r"""Activate an agent session and store the session token.

        Returns:
            str: The session token for subsequent memory operations.
        """
        response = self._client.post(
            f"{self.base_url}/api/v2/agents/{self.agent_id}/activate"
        )
        response.raise_for_status()
        data = response.json()
        self._session_token = data["session_token"]
        return self._session_token

    def _headers(self) -> Dict[str, str]:
        if not self._session_token:
            self.activate_session()
        return {
            "X-Session-Token": self._session_token or "",
            "Content-Type": "application/json",
        }

    def _session_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        r"""Send a request and re-activate the session once on 401."""
        response = self._client.request(
            method,
            url,
            headers=self._headers(),
            **kwargs,
        )
        if response.status_code == 401:
            self.activate_session()
            response = self._client.request(
                method,
                url,
                headers=self._headers(),
                **kwargs,
            )
        response.raise_for_status()
        return response

    def remember(
        self,
        content: str,
        memory_type: MemantoMemoryType = "context",
        title: Optional[str] = None,
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
    ) -> str:
        r"""Store a memory for the active agent.

        Args:
            content (str): Memory content.
            memory_type (MemantoMemoryType, optional): Semantic memory type.
                (default: :obj:`"context"`)
            title (Optional[str], optional): Short title for the memory.
            confidence (float, optional): Confidence score. (default: :obj:`1.0`)
            tags (Optional[List[str]], optional): Optional tags.

        Returns:
            str: The stored memory ID.
        """
        payload: Dict[str, Any] = {
            "content": content,
            "type": memory_type,
            "title": title or f"{memory_type.title()}: {content[:50]}",
            "confidence": confidence,
        }
        if tags:
            payload["tags"] = tags

        response = self._session_request(
            "POST",
            f"{self.base_url}/api/v2/agents/{self.agent_id}/remember",
            json=payload,
        )
        return response.json()["memory_id"]

    def recall(
        self,
        query: str,
        limit: int = 10,
        memory_type: Optional[List[MemantoMemoryType]] = None,
    ) -> List[Dict[str, Any]]:
        r"""Retrieve memories by semantic similarity.

        Args:
            query (str): Natural-language search query.
            limit (int, optional): Maximum memories to return.
                (default: :obj:`10`)
            memory_type (Optional[List[MemantoMemoryType]], optional): Optional
                type filter.

        Returns:
            List[Dict[str, Any]]: Matching memory records.
        """
        payload: Dict[str, Any] = {"query": query, "limit": limit}
        if memory_type:
            payload["type"] = memory_type

        response = self._session_request(
            "POST",
            f"{self.base_url}/api/v2/agents/{self.agent_id}/recall",
            json=payload,
        )
        return response.json().get("memories", [])

    def recall_recent(
        self,
        limit: int = _RECALL_PAGE_SIZE,
        memory_type: Optional[List[MemantoMemoryType]] = None,
    ) -> List[Dict[str, Any]]:
        r"""Retrieve the most recent memories (newest first).

        Args:
            limit (int, optional): Maximum memories to return.
                (default: :obj:`100`)
            memory_type (Optional[List[MemantoMemoryType]], optional): Optional
                type filter.

        Returns:
            List[Dict[str, Any]]: Recent memory records.
        """
        payload: Dict[str, Any] = {"limit": limit}
        if memory_type:
            payload["type"] = memory_type

        response = self._session_request(
            "POST",
            f"{self.base_url}/api/v2/agents/{self.agent_id}/recall/recent",
            json=payload,
        )
        return response.json().get("memories", [])

    def answer(self, question: str) -> str:
        r"""Generate an answer grounded in stored memories.

        Args:
            question (str): Question to answer.

        Returns:
            str: Generated answer text.
        """
        response = self._session_request(
            "POST",
            f"{self.base_url}/api/v2/agents/{self.agent_id}/answer",
            json={"question": question},
        )
        return response.json().get("answer", "")

    def delete_memory(self, memory_id: str) -> None:
        r"""Delete a single memory by ID.

        Args:
            memory_id (str): Memory identifier to delete.
        """
        self._session_request(
            "DELETE",
            f"{self.base_url}/api/v2/agents/{self.agent_id}/memories/{memory_id}",
        )

    def clear_all_memories(self) -> None:
        r"""Delete all memories for the active agent."""
        while True:
            memories = self.recall_recent(limit=_RECALL_PAGE_SIZE)
            if not memories:
                break
            for memory in memories:
                memory_id = memory.get("id") or memory.get("memory_id")
                if memory_id:
                    self.delete_memory(memory_id)

    def close(self) -> None:
        r"""Close the underlying HTTP client."""
        self._client.close()


class MemantoStorage(BaseKeyValueStorage):
    r"""A concrete implementation of :obj:`BaseKeyValueStorage` using Memanto
    as the backend for persistent agent memory.

    Args:
        agent_id (str): Memanto agent identifier. If not provided, falls back
            to the :obj:`MEMANTO_AGENT_ID` environment variable.
        base_url (str, optional): Memanto server URL. Defaults to
            :obj:`MEMANTO_BASE_URL` or ``http://localhost:8000``.
        recall_limit (int, optional): Maximum number of recent memories to
            load. (default: :obj:`100`)

    References:
        https://docs.memanto.ai
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        base_url: Optional[str] = None,
        recall_limit: int = 100,
    ) -> None:
        resolved_agent_id = agent_id or os.getenv("MEMANTO_AGENT_ID")
        if not resolved_agent_id:
            raise ValueError(
                "agent_id must be provided or set via MEMANTO_AGENT_ID."
            )

        self.agent_id = resolved_agent_id
        self.recall_limit = recall_limit
        self._client = MemantoRESTClient(
            agent_id=self.agent_id,
            base_url=base_url,
        )

    @staticmethod
    def _memory_id_to_uuid(memory_id: str) -> UUID:
        try:
            return UUID(memory_id)
        except ValueError:
            return uuid5(NAMESPACE_URL, memory_id)

    @staticmethod
    def _parse_timestamp(created_at: Optional[str]) -> float:
        if not created_at:
            return datetime.now().timestamp()
        return datetime.fromisoformat(
            created_at.replace("Z", "+00:00")
        ).timestamp()

    def _record_to_content(self, record: Dict[str, Any]) -> str:
        role = record["role_at_backend"]
        if isinstance(role, OpenAIBackendRole):
            role_name = _ROLE_NAME_MAP.get(role, role.value)
        else:
            role_name = str(role)
        content = record["message"]["content"]
        return f"{role_name}: {content}"

    def _memory_to_record_dict(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        memory_id = memory.get("id") or memory.get("memory_id") or ""
        metadata = {
            "memanto_id": memory_id,
            "memanto_type": memory.get("type", "context"),
        }
        tags = memory.get("tags")
        if tags:
            metadata["tags"] = ",".join(tags)

        memory_record = MemoryRecord(
            uuid=self._memory_id_to_uuid(memory_id),
            message=BaseMessage(
                role_name="memory",
                role_type=RoleType.USER,
                meta_dict=metadata,
                content=memory.get("content", ""),
            ),
            role_at_backend=OpenAIBackendRole.USER,
            extra_info=metadata,
            timestamp=self._parse_timestamp(memory.get("created_at")),
            agent_id=self.agent_id,
        )
        return memory_record.to_dict()

    def save(self, records: List[Dict[str, Any]]) -> None:
        r"""Saves a batch of records to Memanto.

        Args:
            records (List[Dict[str, Any]]): Records to store.
        """
        try:
            for record in records:
                content = self._record_to_content(record)
                self._client.remember(content=content, memory_type="context")
        except Exception as error:
            logger.error(f"Error saving memories to Memanto: {error}")

    def load(self) -> List[Dict[str, Any]]:
        r"""Loads recent records from Memanto in chronological order.

        Returns:
            List[Dict[str, Any]]: Stored memory records.
        """
        try:
            memories = self._client.recall_recent(limit=self.recall_limit)
            memories.reverse()
            return [self._memory_to_record_dict(memory) for memory in memories]
        except Exception as error:
            logger.error(f"Error loading memories from Memanto: {error}")
            return []

    def clear(self) -> None:
        r"""Removes all memories for the configured agent."""
        try:
            self._client.clear_all_memories()
            logger.info(
                f"Successfully cleared Memanto memories for agent "
                f"'{self.agent_id}'"
            )
        except Exception as error:
            logger.error(f"Error clearing Memanto memories: {error}")
