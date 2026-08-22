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

import time
from typing import Dict, List, Optional
from uuid import uuid4

from camel.memories import ChatHistoryMemory
from camel.memories.context_creators.score_based import (
    ScoreBasedContextCreator,
)
from camel.memories.records import MemoryRecord
from camel.messages import BaseMessage
from camel.storages.key_value_storages.mem0_cloud import Mem0Storage
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.types import ModelType, OpenAIBackendRole, RoleType
from camel.utils import BaseTokenCounter, MCPServer, OpenAITokenCounter, dependencies_required


@MCPServer()
class Mem0CloudToolkit(BaseToolkit):
    r"""A toolkit for interacting with Mem0 cloud memory storage.

    This toolkit provides methods for adding, retrieving, searching, and
    deleting memories in Mem0's cloud storage system. Unlike the standard
    MemoryToolkit which works with local file-based memory, this toolkit
    provides cloud-based persistent memory with advanced search capabilities.

    Args:
        agent_id (str): The agent identifier for memory organization.
        user_id (str, optional): The user identifier for memory organization.
            (default: :obj:`"camel_memory"`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter
            for memory context management. If None, defaults to OpenAI GPT-4o-mini.
            (default: :obj:`None`)
        token_limit (int, optional): Maximum token limit for memory context.
            (default: :obj:`4096`)
        timeout (Optional[float], optional): Maximum execution time allowed for
            toolkit operations in seconds. If None, no timeout is applied.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        agent_id: str,
        user_id: str = "camel_memory",
        token_counter: Optional[BaseTokenCounter] = None,
        token_limit: int = 4096,
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)
        self.agent_id = agent_id
        self.user_id = user_id
        self.token_counter = token_counter or OpenAITokenCounter(ModelType.GPT_4O_MINI)
        self.token_limit = token_limit
        self.memory = self._setup_memory()

    def _setup_memory(self) -> ChatHistoryMemory:
        r"""Sets up CAMEL's memory components with Mem0 as the backend."""
        storage = Mem0Storage(agent_id=self.agent_id, user_id=self.user_id)
        context_creator = ScoreBasedContextCreator(
            token_counter=self.token_counter, token_limit=self.token_limit
        )
        return ChatHistoryMemory(
            context_creator=context_creator,
            storage=storage,
            agent_id=self.agent_id,
        )

    @dependencies_required("mem0")
    def add_memory(
        self, content: str, metadata: Optional[Dict[str, str]] = None
    ) -> str:
        r"""Adds a new memory record to Mem0 cloud storage.

        Args:
            content (str): The information to remember.
            metadata (Optional[Dict[str, str]], optional): Additional data to
                store with the memory. (default: :obj:`None`)

        Returns:
            str: A confirmation message indicating successful memory addition.
        """
        record = MemoryRecord(
            uuid=uuid4(),
            message=BaseMessage(
                role_name="User",
                role_type=RoleType.USER,
                meta_dict=metadata or {},
                content=content,
            ),
            role_at_backend=OpenAIBackendRole.USER,
            timestamp=time.time(),
            agent_id=self.agent_id,
        )
        self.memory.write_records([record])
        return "Memory added successfully to Mem0 cloud."

    @dependencies_required("mem0")
    def retrieve_memories(self) -> str:
        r"""Retrieves all memories from Mem0 cloud storage.

        Returns:
            str: Raw API response containing all stored memories as a string.
        """
        memories = self.memory._chat_history_block.storage.load()
        return f"Raw API Response:\n{memories!s}"

    @dependencies_required("mem0")
    def search_memories(self, query: str) -> str:
        r"""Searches for memories in Mem0 cloud storage based on a query.

        This uses Mem0's semantic search with:
        - Vector-based semantic matching
        - Metadata filtering
        - Reranking for better results

        Args:
            query (str): The search term to find relevant memories.

        Returns:
            str: Raw API response containing search results as a string.
        """
        try:
            # Use OR filter for better matching - match if either user_id or
            # agent_id matches
            filters = {
                "OR": [{"user_id": self.user_id}, {"agent_id": self.agent_id}]
            }

            results = self.memory._chat_history_block.storage.client.search(
                query,
                version="v2",
                filters=filters,
                output_format="v1.1",
                # Enable advanced features but with less restrictive settings
                rerank=True,  # Better result ordering
                threshold=0.01,  # Lower threshold for better recall
                top_k=10,  # Get more results
                keyword_search=True,  # Enable keyword matching alongside semantic search
            )
            return f"Raw API Response:\n{results!s}"
        except Exception as e:
            return f"API Error: {e!s}"

    @dependencies_required("mem0")
    def delete_memory(self, memory_id: str) -> str:
        r"""Deletes a specific memory from Mem0 cloud storage by ID.

        Args:
            memory_id (str): The unique identifier of the memory to delete.

        Returns:
            str: A confirmation message indicating successful memory deletion.
        """
        try:
            self.memory._chat_history_block.storage.client.delete(
                memory_id=memory_id
            )
            return f"Memory {memory_id} deleted successfully from Mem0 cloud."
        except Exception as e:
            return f"API Error: {e!s}"

    @dependencies_required("mem0")
    def clear_memory(self) -> str:
        r"""Clears all memories from Mem0 cloud storage for the current user
        and agent.

        Returns:
            str: A confirmation message indicating successful memory clearing.
        """
        self.memory.clear()
        return "All memories have been cleared from Mem0 cloud storage."

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.add_memory),
            FunctionTool(self.retrieve_memories),
            FunctionTool(self.search_memories),
            FunctionTool(self.delete_memory),
            FunctionTool(self.clear_memory),
        ]

