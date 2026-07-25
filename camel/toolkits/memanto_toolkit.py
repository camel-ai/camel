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
from typing import List, Optional

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import dependencies_required


class MemantoToolkit(BaseToolkit):
    r"""A class representing a toolkit for Memanto long-term agent memory.

    Args:
        agent_id (str, optional): Default agent ID for Memanto operations.
            (default: :obj:`None`, checks `MEMANTO_AGENT_ID`).
        api_key (str, optional): The API key for Memanto authentication.
            (default: :obj:`None`, checks `MEMANTO_API_KEY`).
        base_url (str, optional): Base URL for the Memanto REST API.
            (default: :obj:`None`, checks `MEMANTO_BASE_URL`).
    """

    @dependencies_required('memanto')
    def __init__(
        self,
        agent_id: Optional[str] = None,
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

        self.client = Memanto(
            api_key=self.api_key,
            base_url=self.base_url,
            agent_id=self.agent_id,
        )

    def memanto_remember(
        self,
        content: str,
        type: str = "fact",
        tags: Optional[List[str]] = None,
        confidence: float = 1.0,
    ) -> str:
        r"""Stores a typed memory (fact, preference, goal, decision, etc.)
        into Memanto.

        Args:
            content (str): The text content or fact to remember.
            type (str, optional): Category of memory (e.g. 'fact',
                'preference', 'goal').
            tags (List[str], optional): Optional tags for filtering memories.
            confidence (float, optional): Confidence score between 0.0 and 1.0.

        Returns:
            str: Confirmation message with memory ID.
        """
        try:
            res = self.client.remember(
                agent_id=self.agent_id,
                content=content,
                type=type,
                tags=tags or [],
                confidence=confidence,
            )
            return f"Successfully saved memory to Memanto: {res}"
        except Exception as e:
            return f"Failed to save memory to Memanto: {e}"

    def memanto_recall(
        self,
        query: str,
        limit: int = 5,
        type: Optional[str] = None,
    ) -> str:
        r"""Performs semantic search over stored agent memories.

        Args:
            query (str): The search query to locate relevant memories.
            limit (int, optional): Maximum number of memories to return.
                (default: 5)
            type (str, optional): Optional memory type filter.

        Returns:
            str: String representation of recalled memories.
        """
        try:
            results = self.client.recall(
                agent_id=self.agent_id,
                query=query,
                limit=limit,
                type=type,
            )
            return f"Recalled memories: {results}"
        except Exception as e:
            return f"Failed to recall memories from Memanto: {e}"

    def memanto_answer(
        self,
        question: str,
    ) -> str:
        r"""Generates a RAG-style answer grounded strictly in stored
        Memanto memories.

        Args:
            question (str): The question to answer based on memory history.

        Returns:
            str: The grounded answer returned by Memanto.
        """
        try:
            answer = self.client.answer(
                agent_id=self.agent_id,
                question=question,
            )
            return f"Memanto Grounded Answer: {answer}"
        except Exception as e:
            return f"Failed to get grounded answer from Memanto: {e}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects available in this
        toolkit.
        """
        return [
            FunctionTool(self.memanto_remember),
            FunctionTool(self.memanto_recall),
            FunctionTool(self.memanto_answer),
        ]
