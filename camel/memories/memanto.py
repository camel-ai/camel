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

import os
from typing import Any, Dict, List, Optional
from uuid import NAMESPACE_URL, uuid5

import httpx

from camel.memories.agent_memories import ChatHistoryMemory
from camel.memories.base import BaseContextCreator
from camel.memories.records import ContextRecord, MemoryRecord
from camel.messages import BaseMessage, FunctionCallingMessage
from camel.storages.key_value_storages.base import BaseKeyValueStorage
from camel.types import OpenAIBackendRole


class _MemantoRESTClient:
    r"""Session-aware client for Memanto memory writes and semantic recall."""

    def __init__(self, agent_id: str, base_url: str, timeout: float) -> None:
        self._url = f"{base_url.rstrip('/')}/api/v2/agents/{agent_id}"
        self._client = httpx.Client(timeout=timeout)
        self._session_token = ""
        try:
            self._activate()
        except Exception:
            self.close()
            raise

    def _activate(self) -> None:
        response = self._client.post(f"{self._url}/activate")
        response.raise_for_status()
        self._session_token = response.json()["session_token"]

    def _request(
        self, operation: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        for attempt in range(2):
            response = self._client.post(
                f"{self._url}/{operation}",
                headers={"X-Session-Token": self._session_token},
                json=payload,
            )
            if response.status_code == 401 and attempt == 0:
                self._activate()
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError("Memanto session retry exhausted")

    def remember(self, content: str, record_id: str) -> None:
        self._request(
            "remember",
            {
                "content": content,
                "type": "context",
                "tags": [f"camel-record:{record_id}"],
            },
        )

    def recall(self, query: str, limit: int) -> List[Dict[str, Any]]:
        return self._request("recall", {"query": query, "limit": limit}).get(
            "memories", []
        )

    def close(self) -> None:
        self._client.close()


class MemantoMemory(ChatHistoryMemory):
    r"""Chat history augmented with automatic Memanto semantic memory.

    Complete conversation records remain in the chat-history storage. User
    and assistant text is also stored in Memanto. Retrieval searches Memanto
    using the latest user message and adds matching text as recalled context.
    System instructions, tool-call metadata, and attachments are kept in chat
    history; Memanto is not a lossless backup of that history.

    Clearing or rolling back this memory only changes chat history. Archived
    Memanto memories survive agent initialization and conversation resets.
    HTTP errors propagate to the caller; a failed remote write leaves the
    original records in chat history.

    Args:
        context_creator (BaseContextCreator): Creates model context.
        agent_id (Optional[str], optional): Existing Memanto agent identifier.
            Defaults to the MEMANTO_AGENT_ID environment variable.
        base_url (Optional[str], optional): Memanto server URL. Defaults to
            MEMANTO_BASE_URL or http://localhost:8000.
        storage (Optional[BaseKeyValueStorage], optional): Chat-history
            storage. Defaults to in-memory storage.
        window_size (Optional[int], optional): Recent chat-history window.
            Defaults to the complete current conversation.
        retrieve_limit (int, optional): Maximum semantic recall results,
            between 1 and 100. (default: :obj:`3`)
        timeout (float, optional): HTTP timeout in seconds.
            (default: :obj:`30.0`)
    """

    def __init__(
        self,
        context_creator: BaseContextCreator,
        agent_id: Optional[str] = None,
        base_url: Optional[str] = None,
        storage: Optional[BaseKeyValueStorage] = None,
        window_size: Optional[int] = None,
        retrieve_limit: int = 3,
        timeout: float = 30.0,
    ) -> None:
        resolved_agent_id = agent_id or os.getenv("MEMANTO_AGENT_ID")
        if not resolved_agent_id:
            raise ValueError(
                "agent_id must be provided or set via MEMANTO_AGENT_ID."
            )
        if not 1 <= retrieve_limit <= 100:
            raise ValueError("retrieve_limit must be between 1 and 100.")
        super().__init__(
            context_creator, storage, window_size, resolved_agent_id
        )
        self._memanto_agent_id = resolved_agent_id
        self._retrieve_limit = retrieve_limit
        self._client = _MemantoRESTClient(
            resolved_agent_id,
            base_url
            or os.getenv("MEMANTO_BASE_URL")
            or "http://localhost:8000",
            timeout,
        )

    def write_records(self, records: List[MemoryRecord]) -> None:
        r"""Keep complete chat records and archive conversational text."""
        super().write_records(records)
        for record in records:
            if (
                record.role_at_backend
                in {OpenAIBackendRole.USER, OpenAIBackendRole.ASSISTANT}
                and not isinstance(record.message, FunctionCallingMessage)
                and record.message.content.strip()
            ):
                self._client.remember(
                    f"{record.role_at_backend.value}: "
                    f"{record.message.content}",
                    str(record.uuid),
                )

    def retrieve(self) -> List[ContextRecord]:
        r"""Combine recent chat history with relevant long-term memories."""
        history = super().retrieve()
        query = next(
            (
                item.memory_record.message.content
                for item in reversed(history)
                if item.memory_record.role_at_backend == OpenAIBackendRole.USER
            ),
            "",
        )
        if not query.strip():
            return history

        memories = self._client.recall(query, self._retrieve_limit)
        local_tags = {
            f"camel-record:{item.memory_record.uuid}" for item in history
        }
        recalled = []
        # Place recalled context before the conversation, so it cannot split
        # assistant tool calls from their tool responses.
        prefix = 0
        while history[prefix].memory_record.role_at_backend in {
            OpenAIBackendRole.SYSTEM,
            OpenAIBackendRole.DEVELOPER,
        }:
            prefix += 1
        timestamp = history[prefix].timestamp
        for memory in memories:
            if local_tags.intersection(memory.get("tags") or []):
                continue
            content = memory.get("content")
            if not content:
                continue
            memory_id = memory["id"]
            record = MemoryRecord(
                uuid=uuid5(
                    NAMESPACE_URL,
                    f"memanto:{self._memanto_agent_id}:{memory_id}",
                ),
                message=BaseMessage.make_user_message(
                    role_name="Memanto memory",
                    content=(
                        f"Recalled memory (historical context):\n{content}"
                    ),
                ),
                role_at_backend=OpenAIBackendRole.USER,
                extra_info={"memanto_id": memory_id},
                timestamp=timestamp,
                agent_id=self.agent_id or "",
            )
            recalled.append(
                ContextRecord(
                    memory_record=record, score=1.0, timestamp=timestamp
                )
            )
        # Semantic recall can change content without changing message count.
        # Cached estimates for an append-only conversation are then stale.
        clear_cache = getattr(self._context_creator, "clear_cache", None)
        if callable(clear_cache):
            clear_cache()
        return history[:prefix] + recalled + history[prefix:]

    def clear(self) -> None:
        r"""Clear current chat history while retaining Memanto memories."""
        super().clear()

    def close(self) -> None:
        r"""Close the HTTP client without deleting any memories."""
        self._client.close()
