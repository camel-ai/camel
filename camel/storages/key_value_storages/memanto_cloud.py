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
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from camel.memories.records import MemoryRecord
from camel.messages import BaseMessage
from camel.storages.key_value_storages import BaseKeyValueStorage
from camel.types import OpenAIBackendRole, RoleType
from camel.utils import dependencies_required

logger = logging.getLogger(__name__)


class MemantoStorage(BaseKeyValueStorage):
    r"""A concrete implementation of :obj:`BaseKeyValueStorage` using Memanto
    Cloud or local instance as the persistent memory backend.

    Args:
        agent_id (str): Default agent ID to associate memories with.
        api_key (str, optional): The API key for Memanto authentication.
            (default: :obj:`None`, checks `MEMANTO_API_KEY`).
        base_url (str, optional): Base URL for the Memanto REST API.
            (default: :obj:`None`, checks `MEMANTO_BASE_URL` or defaults to
            `"http://localhost:8000"`).
    """

    @dependencies_required('memanto')
    def __init__(
        self,
        agent_id: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        from memanto import Memanto  # type: ignore[import-not-found]

        self.agent_id = agent_id or os.getenv(
            "MEMANTO_AGENT_ID", "default_agent"
        )
        self.api_key = api_key or os.getenv("MEMANTO_API_KEY")
        raw_url = (  # type: ignore[union-attr]
            base_url or os.getenv("MEMANTO_BASE_URL", "http://localhost:8000")
        )
        self.base_url = raw_url.rstrip('/')  # type: ignore[union-attr]

        # Initialize Memanto client SDK
        self.client = Memanto(
            api_key=self.api_key,
            base_url=self.base_url,
            agent_id=self.agent_id,
        )

    def _prepare_messages(
        self,
        records: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        r"""Prepare message dictionaries from records for Memanto API calls."""
        messages = []
        for record in records:
            content = record["message"]["content"]
            role = record["role_at_backend"].value
            messages.append({"role": role, "content": content})
        return messages

    def save(self, records: List[Dict[str, Any]]) -> None:
        r"""Saves a batch of records into Memanto persistent memory."""
        if not records:
            return

        try:
            messages = self._prepare_messages(records)
            for msg in messages:
                # Calls POST /api/v2/agents/{agent_id}/remember via SDK
                self.client.remember(
                    agent_id=self.agent_id,
                    content=msg["content"],
                    role=msg["role"],
                )
        except Exception as e:
            logger.error(f"Error saving memories to Memanto: {e}")

    def load(self) -> List[Dict[str, Any]]:
        r"""Loads stored records from Memanto persistent memory."""
        try:
            # Calls POST /api/v2/agents/{agent_id}/recall_recent via SDK
            results = self.client.recall_recent(agent_id=self.agent_id)

            transformed_results = []
            for result in results:
                metadata = result.get("metadata") or {}

                # Fall back to a random UUID if not provided by backend
                record_id = UUID(result["id"]) if "id" in result else uuid4()

                memory_record = MemoryRecord(
                    uuid=record_id,
                    message=BaseMessage(
                        role_name="memory",
                        role_type=RoleType.USER,
                        meta_dict=metadata,
                        content=result.get(
                            "content", result.get("memory", "")
                        ),
                    ),
                    role_at_backend=OpenAIBackendRole.USER,
                    extra_info=metadata,
                    timestamp=datetime.now().timestamp(),
                    agent_id=self.agent_id,
                )
                transformed_results.append(memory_record.to_dict())

            return transformed_results
        except Exception as e:
            logger.error(f"Error loading memories from Memanto: {e}")
            return []

    def clear(
        self,
        agent_id: Optional[str] = None,
    ) -> None:
        r"""Removes all stored records for the agent from Memanto."""
        target_agent = agent_id or self.agent_id
        try:
            self.client.clear(agent_id=target_agent)
            logger.info(
                f"Successfully cleared Memanto memories for agent: "
                f"{target_agent}"
            )
        except Exception as e:
            logger.error(f"Error clearing Memanto memories: {e}")
