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

import warnings
from typing import List, Optional

from openai.resources.chat.chat import Chat

from camel.memories.base import AgentMemory, BaseContextCreator
from camel.memories.blocks import ChatHistoryBlock, VectorDBBlock
from camel.memories.records import ContextRecord, MemoryRecord
from camel.storages.key_value_storages.base import BaseKeyValueStorage
from camel.storages.vectordb_storages.base import BaseVectorStorage
from camel.types import OpenAIBackendRole
from camel.agents import ChatAgent

from camel.messages import BaseMessage
from camel.logger import get_logger 
import json

logger = get_logger(__name__)


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
        self._chat_history_block = ChatHistoryBlock(storage=storage)
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
                meta_dict = record.get('meta_dict', {})
                if meta_dict and 'tool_calls' in meta_dict:
                    indices_to_remove.append(i)

        # Remove records in-place
        for i in reversed(indices_to_remove):
            del record_dicts[i]

        # Save the modified records back to storage
        self._chat_history_block.storage.save(record_dicts)


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


class MarkdownMemory(ChatHistoryMemory):
    r"""An agent memory wrapper of :obj:`ChatHistoryMemory` that saves the
    chat history to a markdown file for a context clean-up. 

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
        context_cleanup_threshold (int, optional): The number of messages in the
            chat history that will trigger a context cleanup. (default: :obj:`30`)
    """
    def __init__(
        self,
        summary_agent: ChatAgent,
        context_creator: BaseContextCreator,
        storage: Optional[BaseKeyValueStorage] = None,
        window_size: Optional[int] = None,
        agent_id: Optional[str] = None,
        context_cleanup_threshold: int = 30,
    ) -> None:
        from camel.toolkits.markdown_memory_toolkit import MarkdownMemoryToolkit
        super().__init__(context_creator, storage, window_size, agent_id)
        self.summary_agent = summary_agent
        self._context_cleanup_threshold = context_cleanup_threshold
        self._markdown_memory_toolkit = MarkdownMemoryToolkit()

    def write_records(self, records: List[MemoryRecord]) -> None:
        r"""Writes the records to the memory and checks if the context needs to be refreshed."""
        super().write_records(records)

        memory_messages_count = len(self.retrieve())
        if memory_messages_count >= self._context_cleanup_threshold:
            self.refresh_context()

    def refresh_context(self) -> None:
        r"""Refreshes the context by saving the chat history to a markdown file,
        emptying the context, and intializing it with a summary of what has been
        done so far and needs to be done next."""

        # 1. Retrieve current memory records
        context_records = self.retrieve()
        if not context_records:
            return
        
        memory_records = [cr.memory_record for cr in context_records]

        # 2. Generate a summary of the context
        summary_content = self._generate_intelligent_summary(memory_records)

        # 3. Save the summary to a markdown file
        self._markdown_memory_toolkit._save_summary(summary_content)
        self._markdown_memory_toolkit._save_history(memory_records)

        # 4. Clear the current context
        self.clear()
        
        #5. Initialize the memory with the summary
        self._initialize_with_summary(summary_content)
        
    def _generate_intelligent_summary(self, memory_records: List[MemoryRecord]) -> dict:
        r"""Uses an agent to summarize the context.
        
        Args:
            memory_records (List[MemoryRecord]): The memory records to summarize.

        Returns:
            dict: A summary of the key information about the conversation.
        """

        conversation = self._format_conversation_for_summary(memory_records)

        summarize_prompt = f"""
        The following is a conversation history of a large language model agent.
        Analyze it and extract the key information from it. The information will be
        passed on to a new agent that will use it to understand the problem and continue
        working on it without having to start from scratch.

        Conversation:
        {conversation}

        Prive ONLY a JSON response with this exact structure:
        {{
            "task_description": "A description of the task the agent is assigned to do.",
            "work_completed": "A description of the work that has been completed so far. make sure to include all the main steps, what tools have been used so far, and for what purpose.",
            "user_preferences": "If there is any useful information about the user's preferences, their goals, or any other information that is relevant to the task, include it here.",
            "next_steps": "Include if the agent or user has provided any plans for the next steps. Do not infer anything yourself, and leavel empty if nothing is provided in the conversation history."
        }}
        """
        response = self.summary_agent.step(summarize_prompt)
        return self._parse_summary_response(response.msgs[-1].content)

    def _format_conversation_for_summary(self, memory_records: List[MemoryRecord]) -> str:
        r"""Prepare the conversation for the summary agent.

        Args:
            memory_records (List[MemoryRecord]): The memory records to format.

        Returns:
            str: The formatted conversation.
        """
        conversation_text = []

        for record in memory_records:
            role = record.role_at_backend.value if \
                hasattr(record.role_at_backend, 'value')\
                else str(record.role_at_backend)
            content = record.message.content
            conversation_text.append(f"{role}: {content}\n")
        
        return "\n".join(conversation_text)

    def _initialize_with_summary(self, summary_content: dict) -> None:
        r"""Initialize the empty memory with the summary.

        Args:
            summary_content (dict): The summary content to initialize the memory with.

        Returns:
            None
        """

        if not summary_content:
            logger.warning("No summary content provided. Skipping context refresh.")
            return

        # create a formatter summary text
        summary_text = """[Context Refresh]

You are resuming a conversation after context cleanup due to 
too many irrelevant messages or context bloat. The previous 
conversation has been saved to markdown files, and this summary
provides all the information you need to continue the conversation.
You must continue the conversation without making the user feel like
you are starting from scratch.

## How to Use This Summary:
- Reference previous work when relevant to new requests  
- Continue naturally without mentioning the context break
- Build upon the work completed and user preferences noted

## Previous Conversation Summary:
"""

        for key, value in summary_content.items():
            header = key.replace('_', ' ').title()
            summary_text += f"### {header}\n"
            if isinstance(value, list):
                for item in value:
                    summary_text += f"- {item}\n"
            else:
                summary_text += f"{value}\n"
            summary_text += "\n"
        
        # Add usage instructions
        summary_text += """
    ## Instructions:
    - You have full access to this context but should not explicitly mention "I see from the summary..." 
    - Act naturally as if you remember the previous conversation
    - The full conversation history is saved in markdown files if detailed reference is needed
    - Continue helping the user based on their preferences and next steps outlined above

    ---
    [END CONTEXT RESTORATION]
    """
        
        # create summary message
        summary_message = BaseMessage.make_assistant_message(
            role_name="System",
            content=summary_text
        )

        # add the summary message to the records
        system_record = MemoryRecord(
            message=summary_message,
            role_at_backend=OpenAIBackendRole.SYSTEM,
            agent_id=self.agent_id
        )

        super().write_records([system_record])

    def _parse_summary_response(self, summary_text: str) -> dict:
        r"""Parse the summary response into a dictionary.

        Args:
            summary_text (str): The summary text to parse.

        Returns:
            dict: The parsed summary JSON.
        """
        import json

        content = summary_text.strip()

        try:
            parsed_json = json.loads(content)
            return parsed_json 
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from summary response: {content}")
            return {}
        