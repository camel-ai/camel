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

import warnings
from typing import List, Optional

from camel.memories.base import AgentMemory, BaseContextCreator
from camel.memories.blocks import ChatHistoryBlock, VectorDBBlock
from camel.memories.context_creators.multimodal import (
    MultimodalContextCreator,
)
from camel.memories.blocks.multimodal_vectordb_block import (
    MultimodalVectorDBBlock,
)
from camel.memories.records import ContextRecord, MemoryRecord
from camel.storages.key_value_storages.base import BaseKeyValueStorage
from camel.storages.vectordb_storages.base import BaseVectorStorage
from camel.types import OpenAIBackendRole


class ChatHistoryMemory(AgentMemory):
    r"""An agent memory wrapper of :obj:`ChatHistoryBlock`.

    Args:
        context_creator (BaseContextCreator): A model context creator.
        storage (BaseKeyValueStorage, optional): A storage backend for storing
            chat history. If `None`, an :obj:`InMemoryKeyValueStorage`
            will be used. (default: :obj:`None`)
        window_size (int, optional): The number of recent chat messages to
            retrieve. If not provided, the entire chat history will be
            retrieved.  (default: :obj:`None`)
        agent_id (str, optional): The ID of the agent associated with the chat
            history.
    """

    def __init__(
        self,
        context_creator: BaseContextCreator,
        storage: Optional[BaseKeyValueStorage] = None,
        window_size: Optional[int] = None,
        agent_id: Optional[str] = None,
    ) -> None:
        if window_size is not None and not isinstance(window_size, int):
            raise TypeError("`window_size` must be an integer or None.")
        if window_size is not None and window_size < 0:
            raise ValueError("`window_size` must be non-negative.")
        self._context_creator = context_creator
        self._window_size = window_size
        self._chat_history_block = ChatHistoryBlock(
            storage=storage,
        )
        self._agent_id = agent_id

    @property
    def agent_id(self) -> Optional[str]:
        return self._agent_id

    @agent_id.setter
    def agent_id(self, val: Optional[str]) -> None:
        self._agent_id = val

    def retrieve(self) -> List[ContextRecord]:
        records = self._chat_history_block.retrieve(self._window_size)
        if self._window_size is not None and len(records) == self._window_size:
            warnings.warn(
                f"Chat history window size limit ({self._window_size}) "
                f"reached. Some earlier messages will not be included in "
                f"the context. Consider increasing window_size if you need "
                f"a longer context.",
                UserWarning,
                stacklevel=2,
            )
        return records

    def write_records(self, records: List[MemoryRecord]) -> None:
        for record in records:
            # assign the agent_id to the record
            if record.agent_id == "" and self.agent_id is not None:
                record.agent_id = self.agent_id
        self._chat_history_block.write_records(records)

    def get_context_creator(self) -> BaseContextCreator:
        return self._context_creator

    def clear(self) -> None:
        self._chat_history_block.clear()

    def clean_tool_calls(self) -> None:
        r"""Removes tool call messages from memory.
        This method removes all FUNCTION/TOOL role messages and any ASSISTANT
        messages that contain tool_calls in their meta_dict to save token
        usage.
        """
        from camel.types import OpenAIBackendRole

        # Get all messages from storage
        record_dicts = self._chat_history_block.storage.load()
        if not record_dicts:
            return

        # Track indices to remove (reverse order for efficient deletion)
        indices_to_remove = []

        # Identify indices of tool-related messages
        for i, record in enumerate(record_dicts):
            role = record.get('role_at_backend')

            # Mark FUNCTION messages for removal
            if role == OpenAIBackendRole.FUNCTION.value:
                indices_to_remove.append(i)
            # Mark TOOL messages for removal
            elif role == OpenAIBackendRole.TOOL.value:
                indices_to_remove.append(i)
            # Mark ASSISTANT messages with tool_calls for removal
            elif role == OpenAIBackendRole.ASSISTANT.value:
                message_dict = record.get('message', {})
                # Check for tool_calls in message
                has_tool_calls = 'tool_calls' in message_dict
                is_func_calling = (
                    message_dict.get('__class__') == 'FunctionCallingMessage'
                    and 'args' in message_dict
                )

                if has_tool_calls or is_func_calling:
                    indices_to_remove.append(i)

        # Remove records in-place
        for i in reversed(indices_to_remove):
            del record_dicts[i]

        # Clear storage and save the modified records back
        self._chat_history_block.storage.clear()
        self._chat_history_block.storage.save(record_dicts)

    def pop_records(self, count: int) -> List[MemoryRecord]:
        r"""Removes the most recent records from chat history memory."""
        return self._chat_history_block.pop_records(count)

    def remove_records_by_indices(
        self, indices: List[int]
    ) -> List[MemoryRecord]:
        r"""Removes records at specified indices from chat history memory."""
        return self._chat_history_block.remove_records_by_indices(indices)


class VectorDBMemory(AgentMemory):
    r"""An agent memory wrapper of :obj:`VectorDBBlock`. This memory queries
    messages stored in the vector database. Notice that the most recent
    messages will not be added to the context.

    Args:
        context_creator (BaseContextCreator): A model context creator.
        storage (BaseVectorStorage, optional): A vector storage storage. If
            `None`, an :obj:`QdrantStorage` will be used.
            (default: :obj:`None`)
        retrieve_limit (int, optional): The maximum number of messages
            to be added into the context.  (default: :obj:`3`)
        agent_id (str, optional): The ID of the agent associated with
            the messages stored in the vector database.
    """

    def __init__(
        self,
        context_creator: BaseContextCreator,
        storage: Optional[BaseVectorStorage] = None,
        retrieve_limit: int = 3,
        agent_id: Optional[str] = None,
    ) -> None:
        self._context_creator = context_creator
        self._retrieve_limit = retrieve_limit
        self._vectordb_block = VectorDBBlock(storage=storage)
        self._agent_id = agent_id

        self._current_topic: str = ""

    @property
    def agent_id(self) -> Optional[str]:
        return self._agent_id

    @agent_id.setter
    def agent_id(self, val: Optional[str]) -> None:
        self._agent_id = val

    def retrieve(self) -> List[ContextRecord]:
        return self._vectordb_block.retrieve(
            self._current_topic,
            limit=self._retrieve_limit,
        )

    def write_records(self, records: List[MemoryRecord]) -> None:
        # Assume the last user input is the current topic.
        for record in records:
            if record.role_at_backend == OpenAIBackendRole.USER:
                self._current_topic = record.message.content

            # assign the agent_id to the record
            if record.agent_id == "" and self.agent_id is not None:
                record.agent_id = self.agent_id

        self._vectordb_block.write_records(records)

    def get_context_creator(self) -> BaseContextCreator:
        return self._context_creator

    def clear(self) -> None:
        r"""Removes all records from the vector database memory."""
        self._vectordb_block.clear()

    def pop_records(self, count: int) -> List[MemoryRecord]:
        r"""Rolling back is unsupported for vector database memory."""
        raise NotImplementedError(
            "VectorDBMemory does not support removing historical records."
        )

    def remove_records_by_indices(
        self, indices: List[int]
    ) -> List[MemoryRecord]:
        r"""Removing by indices is unsupported for vector database memory."""
        raise NotImplementedError(
            "VectorDBMemory does not support removing records by indices."
        )


class LongtermAgentMemory(AgentMemory):
    r"""An implementation of the :obj:`AgentMemory` abstract base class for
    augmenting ChatHistoryMemory with VectorDBMemory.

    Args:
        context_creator (BaseContextCreator): A model context creator.
        chat_history_block (Optional[ChatHistoryBlock], optional): A chat
            history block. If `None`, a :obj:`ChatHistoryBlock` will be used.
            (default: :obj:`None`)
        vector_db_block (Optional[VectorDBBlock], optional): A vector database
            block. If `None`, a :obj:`VectorDBBlock` will be used.
            (default: :obj:`None`)
        retrieve_limit (int, optional): The maximum number of messages
            to be added into the context.  (default: :obj:`3`)
        agent_id (str, optional): The ID of the agent associated with the chat
            history and the messages stored in the vector database.
    """

    def __init__(
        self,
        context_creator: BaseContextCreator,
        chat_history_block: Optional[ChatHistoryBlock] = None,
        vector_db_block: Optional[VectorDBBlock] = None,
        retrieve_limit: int = 3,
        agent_id: Optional[str] = None,
    ) -> None:
        self.chat_history_block = chat_history_block or ChatHistoryBlock()
        self.vector_db_block = vector_db_block or VectorDBBlock()
        self.retrieve_limit = retrieve_limit
        self._context_creator = context_creator
        self._current_topic: str = ""
        self._agent_id = agent_id

    @property
    def agent_id(self) -> Optional[str]:
        return self._agent_id

    @agent_id.setter
    def agent_id(self, val: Optional[str]) -> None:
        self._agent_id = val

    def get_context_creator(self) -> BaseContextCreator:
        r"""Returns the context creator used by the memory.

        Returns:
            BaseContextCreator: The context creator used by the memory.
        """
        return self._context_creator

    def retrieve(self) -> List[ContextRecord]:
        r"""Retrieves context records from both the chat history and the vector
        database.

        Returns:
            List[ContextRecord]: A list of context records retrieved from both
                the chat history and the vector database.
        """
        chat_history = self.chat_history_block.retrieve()
        vector_db_retrieve = self.vector_db_block.retrieve(
            self._current_topic,
            self.retrieve_limit,
        )
        return chat_history[:1] + vector_db_retrieve + chat_history[1:]

    def write_records(self, records: List[MemoryRecord]) -> None:
        r"""Converts the provided chat messages into vector representations and
        writes them to the vector database.

        Args:
            records (List[MemoryRecord]): Messages to be added to the vector
                database.
        """
        self.vector_db_block.write_records(records)
        self.chat_history_block.write_records(records)

        for record in records:
            if record.role_at_backend == OpenAIBackendRole.USER:
                self._current_topic = record.message.content

    def clear(self) -> None:
        r"""Removes all records from the memory."""
        self.chat_history_block.clear()
        self.vector_db_block.clear()

    def pop_records(self, count: int) -> List[MemoryRecord]:
        r"""Removes recent chat history records while leaving vector memory."""
        return self.chat_history_block.pop_records(count)

    def remove_records_by_indices(
        self, indices: List[int]
    ) -> List[MemoryRecord]:
        r"""Removes records at specified indices from chat history."""
        return self.chat_history_block.remove_records_by_indices(indices)


class MultimodalAgentMemory(AgentMemory):
    r"""Agent memory with full multimodal support.

    Combines :obj:`ChatHistoryBlock` (recency-based) with
    :obj:`MultimodalVectorDBBlock` (semantic multimodal retrieval).
    Structurally similar to :obj:`LongtermAgentMemory` but uses
    multimodal-aware components.

    Args:
        context_creator: A model context creator. Recommended:
            :obj:`ScoreBasedContextCreator` for standard use.
        chat_history_block: Chat history block.
            (default: None → creates default :obj:`ChatHistoryBlock`)
        multimodal_vector_block: Multimodal vector block.
            (default: None → creates default :obj:`MultimodalVectorDBBlock`)
        retrieve_limit: Max vector retrieval results. (default: 3)
        agent_id: Agent identifier.
    """

    def __init__(
        self,
        context_creator: BaseContextCreator,
        chat_history_block: Optional[ChatHistoryBlock] = None,
        multimodal_vector_block: Optional[MultimodalVectorDBBlock] = None,
        retrieve_limit: int = 3,
        agent_id: Optional[str] = None,
    ) -> None:
        self.chat_history_block = chat_history_block or ChatHistoryBlock()
        self.multimodal_vector_block = (
            multimodal_vector_block or MultimodalVectorDBBlock()
        )
        self.retrieve_limit = retrieve_limit
        self._context_creator = context_creator
        if (
            isinstance(self._context_creator, MultimodalContextCreator)
            and self._context_creator.media_store is None
            and self.multimodal_vector_block.media_store is not None
        ):
            self._context_creator.bind_media_store(
                self.multimodal_vector_block.media_store
            )
        self._current_topic: str = ""
        self._current_query_images: List = []
        self._current_query_audio: Optional[bytes] = None
        self._agent_id = agent_id

    @property
    def agent_id(self) -> Optional[str]:
        return self._agent_id

    @agent_id.setter
    def agent_id(self, val: Optional[str]) -> None:
        self._agent_id = val

    def get_context_creator(self) -> BaseContextCreator:
        r"""Returns the context creator used by the memory.

        Returns:
            BaseContextCreator: The context creator used by the memory.
        """
        return self._context_creator

    def retrieve(self) -> List[ContextRecord]:
        r"""Retrieve from both chat history and multimodal vector store.

        Follows :obj:`LongtermAgentMemory` pattern:
        chat[:1] + vector_results + chat[1:]

        When the topic is empty but images exist, uses the first image
        as the retrieval query for cross-modal recall.

        Returns:
            List[ContextRecord]: A list of context records.
        """
        chat_history = self.chat_history_block.retrieve()

        # Choose query: prefer text topic, then images, then audio
        if self._current_topic:
            query = self._current_topic
        elif self._current_query_images:
            query = self._current_query_images[0]
        elif self._current_query_audio:
            query = self._current_query_audio
        else:
            query = " "

        vector_results = self.multimodal_vector_block.retrieve(
            query,
            limit=self.retrieve_limit,
        )

        # Interleave: system message + vector results + remaining chat
        system_msg = chat_history[:1]
        rest = chat_history[1:]
        return system_msg + vector_results + rest

    def write_records(self, records: List[MemoryRecord]) -> None:
        r"""Write records to both chat history and vector store.

        Args:
            records: Memory records to write.
        """
        # Track topic from USER messages
        for record in records:
            if record.role_at_backend == OpenAIBackendRole.USER:
                if record.message.content and record.message.content.strip():
                    self._current_topic = record.message.content
                    self._current_query_images = []
                    self._current_query_audio = None
                elif record.message.image_list:
                    self._current_topic = ""
                    self._current_query_images = record.message.image_list
                    self._current_query_audio = None
                elif getattr(record.message, "audio_bytes", None):
                    self._current_topic = ""
                    self._current_query_images = []
                    self._current_query_audio = record.message.audio_bytes

            # Propagate agent_id
            if record.agent_id == "" and self.agent_id is not None:
                record.agent_id = self.agent_id

        # Write to both stores
        self.chat_history_block.write_records(records)
        self.multimodal_vector_block.write_records(
            records, agent_id=self._agent_id or ""
        )

    def clear(self) -> None:
        r"""Remove all records from both stores."""
        self.chat_history_block.clear()
        self.multimodal_vector_block.clear()
        self._current_topic = ""
        self._current_query_images = []
        self._current_query_audio = None

    def close(self) -> None:
        r"""Release resources owned by multimodal memory."""
        self.multimodal_vector_block.close()

    def pop_records(self, count: int) -> List[MemoryRecord]:
        r"""Remove recent chat history records."""
        return self.chat_history_block.pop_records(count)

    def remove_records_by_indices(
        self, indices: List[int]
    ) -> List[MemoryRecord]:
        r"""Remove records at specified indices from chat history."""
        return self.chat_history_block.remove_records_by_indices(indices)
