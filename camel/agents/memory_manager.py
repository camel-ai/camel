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
from pathlib import Path
from typing import Optional

from camel.logger import get_logger
from camel.memories import (
    AgentMemory,
    ChatHistoryMemory,
    MemoryRecord,
    ScoreBasedContextCreator,
)
from camel.messages import BaseMessage, FunctionCallingMessage
from camel.storages import JsonStorage
from camel.types import OpenAIBackendRole

logger = get_logger(__name__)


class MemoryManager:
    r"""Class for unified management of agent memory in CAMEL Agents.

    The `MemoryManager` is responsible for handling all memory-related
    operations for agents, including updating, loading, saving,
    and clearing conversation history.
    It abstracts the underlying memory implementation
    (such as `ChatHistoryMemory` or other strategies),
    and provides a single interface for managing message context,
    windowing, and persistence.

    Args:
        model_backend:
            The model backend used for token counting and context management.
        token_limit (int, optional):
            The maximum number of tokens allowed in the context window.
            If `None`,
            it will use the default token limit from the model backend.
        message_window_size (int, optional):
            The maximum number of previous messages to include
            in the context window. If `None`, no windowing is performed.
        agent_id (str, optional):
            The unique identifier for the agent. Used for memory records.
        memory (AgentMemory, optional):
            An optional custom memory instance. If not provided,
            a default `ChatHistoryMemory` will be used.

    Attributes:
        memory (AgentMemory):
            The underlying memory object used to store and retrieve messages.

    """

    def __init__(
        self,
        model_backend,
        token_limit=None,
        message_window_size=None,
        agent_id=None,
        memory: Optional[AgentMemory] = None,
        system_message=None,
    ):
        # 初始化 context_creator
        context_creator = ScoreBasedContextCreator(
            model_backend.token_counter,
            token_limit or model_backend.token_limit,
        )
        # 初始化 memory
        self.memory: AgentMemory = memory or ChatHistoryMemory(
            context_creator,
            window_size=message_window_size,
            agent_id=agent_id,
        )

    def update_memory(
        self,
        message: BaseMessage,
        role: OpenAIBackendRole,
        agent_id: str,
        timestamp: Optional[float] = None,
    ) -> None:
        r"""Updates the agent memory with a new message.

        If the single *message* exceeds the model's context window, it will
        be **automatically split into multiple smaller chunks** before being
        written into memory. This prevents later failures in
        `ScoreBasedContextCreator` where an over-sized message cannot fit
        into the available token budget at all.

        This slicing logic handles both regular text messages (in the
        `content` field) and long tool call results (in the `result` field of
        a `FunctionCallingMessage`).

        Args:
            message (BaseMessage): The new message to add to the stored
                messages.
            role (OpenAIBackendRole): The backend role type.
            timestamp (Optional[float], optional): Custom timestamp for the
                memory record. If `None`, the current time will be used.
                (default: :obj:`None`)
                    (default: obj:`None`)
        """
        import math
        import time
        import uuid as _uuid

        # 1. Helper to write a record to memory
        def _write_single_record(
            message: BaseMessage, role: OpenAIBackendRole, timestamp: float
        ):
            self.memory.write_record(
                MemoryRecord(
                    message=message,
                    role_at_backend=role,
                    timestamp=timestamp,
                    agent_id=agent_id,
                )
            )

        base_ts = (
            timestamp
            if timestamp is not None
            else time.time_ns() / 1_000_000_000
        )

        # 2. Get token handling utilities, fallback if unavailable
        try:
            context_creator = self.memory.get_context_creator()
            token_counter = context_creator.token_counter
            token_limit = context_creator.token_limit
        except AttributeError:
            _write_single_record(message, role, base_ts)
            return

        # 3. Check if slicing is necessary
        try:
            current_tokens = token_counter.count_tokens_from_messages(
                [message.to_openai_message(role)]
            )
            _, ctx_tokens = self.memory.get_context()
            remaining_budget = max(0, token_limit - ctx_tokens)

            if current_tokens <= remaining_budget:
                _write_single_record(message, role, base_ts)
                return
        except Exception as e:
            logger.warning(
                f"Token calculation failed before chunking, "
                f"writing message as-is. Error: {e}"
            )
            _write_single_record(message, role, base_ts)
            return

        # 4. Perform slicing
        logger.warning(
            f"Message with {current_tokens} tokens exceeds remaining budget "
            f"of {remaining_budget}. Slicing into smaller chunks."
        )

        text_to_chunk: Optional[str] = None
        is_function_result = False

        if isinstance(message, FunctionCallingMessage) and isinstance(
            message.result, str
        ):
            text_to_chunk = message.result
            is_function_result = True
        elif isinstance(message.content, str):
            text_to_chunk = message.content

        if not text_to_chunk or not text_to_chunk.strip():
            _write_single_record(message, role, base_ts)
            return
        # Encode the entire text to get a list of all token IDs
        try:
            all_token_ids = token_counter.encode(text_to_chunk)
        except Exception as e:
            logger.error(f"Failed to encode text for chunking: {e}")
            _write_single_record(message, role, base_ts)  # Fallback
            return

        if not all_token_ids:
            _write_single_record(message, role, base_ts)  # Nothing to chunk
            return

        # 1.  Base chunk size: one-tenth of the smaller of (a) total token
        # limit and (b) current remaining budget.  This prevents us from
        # creating chunks that are guaranteed to overflow the
        # immediate context window.
        base_chunk_size = max(1, remaining_budget) // 10

        # 2.  Each chunk gets a textual prefix such as:
        #        "[chunk 3/12 of a long message]\n"
        #     The prefix itself consumes tokens, so if we do not subtract its
        #     length the *total* tokens of the outgoing message (prefix + body)
        #     can exceed the intended bound.  We estimate the prefix length
        #     with a representative example that is safely long enough for the
        #     vast majority of cases (three-digit indices).
        sample_prefix = "[chunk 1/1000 of a long message]\n"
        prefix_token_len = len(token_counter.encode(sample_prefix))

        # 3.  The real capacity for the message body is therefore the base
        #     chunk size minus the prefix length.  Fallback to at least one
        #     token to avoid zero or negative sizes.
        chunk_body_limit = max(1, base_chunk_size - prefix_token_len)

        # 4.  Calculate how many chunks we will need with this body size.
        num_chunks = math.ceil(len(all_token_ids) / chunk_body_limit)
        group_id = str(_uuid.uuid4())

        for i in range(num_chunks):
            start_idx = i * chunk_body_limit
            end_idx = start_idx + chunk_body_limit
            chunk_token_ids = all_token_ids[start_idx:end_idx]

            chunk_body = token_counter.decode(chunk_token_ids)

            prefix = f"[chunk {i + 1}/{num_chunks} of a long message]\n"
            new_body = prefix + chunk_body

            if is_function_result and isinstance(
                message, FunctionCallingMessage
            ):
                new_msg: BaseMessage = FunctionCallingMessage(
                    role_name=message.role_name,
                    role_type=message.role_type,
                    meta_dict=message.meta_dict,
                    content=message.content,
                    func_name=message.func_name,
                    args=message.args,
                    result=new_body,
                    tool_call_id=message.tool_call_id,
                )
            else:
                new_msg = message.create_new_instance(new_body)

            meta = (new_msg.meta_dict or {}).copy()
            meta.update(
                {
                    "chunk_idx": i + 1,
                    "chunk_total": num_chunks,
                    "chunk_group_id": group_id,
                }
            )
            new_msg.meta_dict = meta

            # Increment timestamp slightly to maintain order
            _write_single_record(new_msg, role, base_ts + i * 1e-6)

    def load_memory(self, memory: AgentMemory) -> None:
        r"""Load the provided memory into the agent.

        Args:
            memory (AgentMemory): The memory to load into the agent.

        Returns:
            None
        """

        for context_record in memory.retrieve():
            self.memory.write_record(context_record.memory_record)
        logger.info(f"Memory loaded from {memory}")

    def load_memory_from_path(
        self,
        path: str,
        agent_id: Optional[str] = None,
    ) -> None:
        r"""Loads memory records from a JSON file filtered by this agent's ID.

        Args:
            path (str): The file path to a JSON memory file that uses
                JsonStorage.

        Raises:
            ValueError: If no matching records for the agent_id are found
                (optional check; commented out below).
        """
        json_store = JsonStorage(Path(path))
        all_records = json_store.load()

        if not all_records:
            raise ValueError(
                f"No records found for agent_id={agent_id} in {path}"
            )

        for record_dict in all_records:
            # Validate the record dictionary before conversion
            required_keys = ['message', 'role_at_backend', 'agent_id']
            if not all(key in record_dict for key in required_keys):
                logger.warning(
                    f"Skipping invalid record: missing required "
                    f"keys in {record_dict}"
                )
                continue

            # Validate message structure in the record
            if (
                not isinstance(record_dict['message'], dict)
                or '__class__' not in record_dict['message']
            ):
                logger.warning(
                    f"Skipping invalid record: malformed message "
                    f"structure in {record_dict}"
                )
                continue

            try:
                record = MemoryRecord.from_dict(record_dict)
                self.memory.write_records([record])
            except Exception as e:
                logger.warning(
                    f"Error converting record to MemoryRecord: {e}. "
                    f"Record: {record_dict}"
                )
        logger.info(f"Memory loaded from {path}")

    def save_memory(self, path: str) -> None:
        r"""Retrieves the current conversation data from memory and writes it
        into a JSON file using JsonStorage.

        Args:
            path (str): Target file path to store JSON data.
        """
        json_store = JsonStorage(Path(path))
        context_records = self.memory.retrieve()
        to_save = [cr.memory_record.to_dict() for cr in context_records]
        json_store.save(to_save)
        logger.info(f"Memory saved to {path}")

    def clear_memory(self, agent_id: str, system_message=None) -> None:
        r"""Clear the agent's memory and reset to initial state.

        Returns:
            None
        """
        self.memory.clear()
        if system_message is not None:
            self.update_memory(
                system_message, OpenAIBackendRole.SYSTEM, agent_id
            )

    def get_context(self):
        return self.memory.get_context()

    def retrieve(self):
        return self.memory.retrieve()
