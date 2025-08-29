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

import glob
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.toolkits.note_taking_toolkit import NoteTakingToolkit

if TYPE_CHECKING:
    from camel.agents import ChatAgent
    from camel.memories.records import MemoryRecord

logger = get_logger(__name__)


class ContextSummarizerToolkit(BaseToolkit):
    r"""A toolkit that provides intelligent context summarization and
    management for agents.

    This toolkit enables agents to compress conversation context through
    intelligent summarization, save conversation history to markdown files,
    and search through past conversations. It handles all context management
    needs in a single toolkit.

    Key features:
    - Intelligent context compression with over-compression prevention
    - Markdown file storage with session management
    - Simple text-based search through conversation history
    - Configurable summarization prompts
    - Context loading and saving capabilities
    """

    def __init__(
        self,
        agent: "ChatAgent",
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
        summary_prompt_template: Optional[str] = None,
    ):
        r"""Initialize the ContextSummarizerToolkit.

        Args:
            agent (ChatAgent): The agent that is using the toolkit.
                This is required to access the agent's memory.
            working_directory (str, optional): The directory path where notes
                will be stored. If not provided, a default directory will be
                used.
            timeout (Optional[float]): The timeout for the toolkit.
            summary_prompt_template (Optional[str]): Custom prompt template
                for summarization. If None, a default task-focused template
                is used. Users can customize this for different use cases.
        """
        super().__init__(timeout=timeout)

        self.agent = agent
        self.working_directory_param = working_directory
        self.summary_prompt_template = summary_prompt_template

        # compression tracking to prevent over-compression
        self.compressed_message_uuids: set = set()
        self.compression_count = 0
        self.existing_summary: Optional[str] = ""

        # Create a separate agent for summarization without tools to avoid
        # circular calls
        from camel.agents import ChatAgent

        self.summary_agent = ChatAgent(
            system_message="You are a helpful assistant that creates concise "
            "summaries of conversations.",
            model=self.agent.model_backend,
            agent_id=f"{self.agent.agent_id}_summarizer",
        )

        # Setup storage and file management
        self._setup_storage(working_directory)

    def _setup_storage(self, working_directory: Optional[str]) -> None:
        r"""Setup the storage directory and note-taking toolkit."""
        self.session_id = self._generate_session_id()

        if working_directory:
            self.working_directory = Path(working_directory).resolve()
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                self.working_directory = (
                    Path(camel_workdir) / "context_compression"
                )
            else:
                self.working_directory = Path("context_compression")

        # Create session-specific directory
        self.working_directory = self.working_directory / self.session_id
        self.working_directory.mkdir(parents=True, exist_ok=True)

        # Initialize note-taking toolkit for file operations
        self._note_toolkit = NoteTakingToolkit(
            working_directory=str(self.working_directory)
        )

        # File names
        self.summary_filename = "summary"
        self.history_filename = "history"

    def _generate_session_id(self) -> str:
        r"""Generate a unique session ID for the current session."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        return f"session_{timestamp}"

    # ========= CORE COMPRESSION METHODS =========

    def _summarize_messages(
        self,
        memory_records: List["MemoryRecord"],
    ) -> str:
        r"""Generate a summary of the conversation context.

        Args:
            memory_records (List["MemoryRecord"]): A list of memory records to
                summarize.

        Returns:
            str: The summary of the conversation context.
        """
        if not memory_records:
            logger.warning(
                "No memory records provided. Returning existing summary."
            )
            return self.existing_summary or ""

        # check for over-compression prevention
        record_uuids = {record.uuid for record in memory_records}
        already_compressed = record_uuids.intersection(
            self.compressed_message_uuids
        )

        if already_compressed:
            logger.warning(
                f"Preventing over-compression: {len(already_compressed)} "
                f"records have already been compressed. Returning existing "
                f"summary."
            )
            return self.existing_summary or ""

        try:
            # 1. reset summary agent state for clean summarization
            self.summary_agent.reset()

            # 2. format the conversation
            conversation_text = self._format_conversation(memory_records)

            # 3. create the summary prompt
            summary_prompt = self._create_summary_prompt(conversation_text)

            # 4. generate summary using the agent
            response = self.summary_agent.step(summary_prompt)

            # 5. extract the summary from response and store
            summary_content = response.msgs[-1].content.strip()
            self.existing_summary = summary_content

            # 6. mark these records as compressed to prevent re-compression
            record_uuids = {record.uuid for record in memory_records}
            self.compressed_message_uuids.update(record_uuids)
            self.compression_count += 1

            logger.info(
                f"Successfully generated summary for {len(memory_records)} "
                f"messages. Compression count: {self.compression_count}"
            )
            return summary_content

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return self.existing_summary or ""

    def _save_summary(self, summary: str) -> str:
        r"""Save a summary to a markdown file.

        Args:
            summary (str): The summary text to save.

        Returns:
            str: Success message or error message.
        """
        try:
            # Format summary with metadata
            summary_content = f"# Conversation Summary: {self.session_id}\n\n"
            summary_content += "## Metadata\n\n"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            summary_content += f"- Save Time: {timestamp}\n"
            summary_content += f"- Session ID: {self.session_id}\n\n"
            summary_content += f"## Summary\n\n{summary}\n"

            self._create_or_update_note(self.summary_filename, summary_content)
            logger.info(
                f"Summary saved to "
                f"{self.working_directory / f'{self.summary_filename}.md'}"
            )
            return f"Summary saved successfully to {self.summary_filename}.md"
        except Exception as e:
            logger.error(f"Error saving summary: {e}")
            return f"Error saving summary: {e}"

    def _save_history(self, memory_records: List["MemoryRecord"]) -> str:
        r"""Save the full conversation history to a markdown file.

        Args:
            memory_records (List["MemoryRecord"]): The list of memory records
                to save.

        Returns:
            str: Success message or error message.
        """
        try:
            # Format history with metadata
            history_content = f"# Conversation History: {self.session_id}\n\n"
            history_content += "## Metadata\n\n"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            history_content += f"- Save Time: {timestamp}\n"
            history_content += f"- Total Messages: {len(memory_records)}\n"
            history_content += f"- Session ID: {self.session_id}\n\n"
            history_content += "## Full Transcript\n\n"

            for i, record in enumerate(memory_records):
                message = record.message
                role = getattr(message, "role_name", "unknown")
                content = getattr(message, "content", str(message))
                agent_id = record.agent_id or "unknown"
                role_at_backend = (
                    record.role_at_backend.value
                    if hasattr(record.role_at_backend, 'value')
                    else str(record.role_at_backend)
                )

                history_content += f"### Message {i + 1} - {role}\n"
                history_content += f"**Agent ID:** {agent_id}  \n"
                history_content += f"**Backend Role:** {role_at_backend}  \n"
                history_content += f"**Content:**\n```\n{content}\n```\n\n"
                history_content += "---\n\n"

            self._create_or_update_note(self.history_filename, history_content)
            logger.info(
                f"History saved to "
                f"{self.working_directory / f'{self.history_filename}.md'}"
            )
            return f"History saved successfully to {self.history_filename}.md"
        except Exception as e:
            logger.error(f"Error saving history: {e}")
            return f"Error saving history: {e}"

    def _compress_and_save(self, memory_records: List["MemoryRecord"]) -> str:
        r"""Complete compression pipeline: summarize and save both history and
        summary.

        Args:
            memory_records (List["MemoryRecord"]): The memory records to
                compress and save.

        Returns:
            str: The generated summary text.
        """
        try:
            # Generate summary
            summary = self._summarize_messages(memory_records)

            # Save both history and summary
            history_result = self._save_history(memory_records)
            summary_result = self._save_summary(summary)

            if "Error" not in history_result and "Error" not in summary_result:
                logger.info(
                    f"Context compression completed successfully. Files saved "
                    f"to {self.working_directory}"
                )
                return summary
            else:
                error_msg = (
                    f"Compression partially failed. History: {history_result},"
                    f" Summary: {summary_result}"
                )
                logger.error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error in compress_and_save: {e}")
            return self.existing_summary or ""

    # ========= FILE MANAGEMENT METHODS =========

    def _create_or_update_note(self, note_name: str, content: str) -> str:
        r"""Create a new note or update existing one.

        Args:
            note_name (str): Name of the note (without .md extension).
            content (str): Content to write to the note.

        Returns:
            str: Success message.
        """
        return self._note_toolkit.create_note(
            note_name, content, overwrite=True
        )

    def _load_summary(self) -> str:
        r"""Load the summary from the markdown file.

        Returns:
            str: The summary content, or empty string if not found.
        """
        try:
            summary_path = (
                self.working_directory / f"{self.summary_filename}.md"
            )
            if summary_path.exists():
                return summary_path.read_text(encoding="utf-8")
            else:
                return ""
        except Exception as e:
            logger.error(f"Error loading summary: {e}")
            return ""

    def _load_history(self) -> str:
        r"""Load the history from the markdown file.

        Returns:
            str: The history content, or empty string if not found.
        """
        try:
            history_path = (
                self.working_directory / f"{self.history_filename}.md"
            )
            if history_path.exists():
                return history_path.read_text(encoding="utf-8")
            else:
                return ""
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return ""

    # ========= PROMPT GENERATION METHODS =========

    def _format_conversation(
        self,
        memory_records: List["MemoryRecord"],
    ) -> str:
        r"""Format the conversation into a text string.

        Args:
            memory_records (List["MemoryRecord"]): A list of memory records to
                format.

        Returns:
            str: The formatted conversation.
        """
        conversation_lines = []

        for record in memory_records:
            role = (
                record.role_at_backend.value
                if hasattr(record.role_at_backend, 'value')
                else str(record.role_at_backend)
            )
            content = record.message.content
            conversation_lines.append(f"{role}: {content}")

        return "\n".join(conversation_lines)

    def _create_summary_prompt(
        self,
        conversation_text: str,
    ) -> str:
        r"""Create a prompt for the summary agent.

        Args:
            conversation_text (str): The formatted conversation to summarize.

        Returns:
            str: The complete prompt for summarization.
        """

        # use custom template if provided, otherwise use default
        if self.summary_prompt_template:
            base_prompt = self.summary_prompt_template
        else:
            base_prompt = """The following is a conversation history of a \
large language model agent.
Analyze it and extract the key information from it. The information will be
passed on to a new agent that will use it to understand the problem and \
continue working on it without having to start from scratch. Focus on:
- User's main goal (e.g. "The user wants my help with data analysis of \
customer sales data.")
- Key information about the user and their preferences (e.g. "The user is a \
student who prefers concise bullet-point responses.")
- Tasks that were accomplished (e.g. "I found the top 10 customers by total \
sales amounts, wrote a Python script to...")
- Tools and methods that were used **if tool/function calls have been made** \
(e.g. "I used CodeExecutionToolkit to execute a Python script to analyze the \
data.")
- Important discoveries or solutions found (e.g. "I found there are duplicate \
entries in the customer name column, which must be taken care of before \
proceeding with the analysis.")
- Technical approaches that worked **if the task is technical** (e.g. "Using \
Pandas + matplotlib seem to yield the best responses for the user's \
queries.)"""

        # if we want to extend an existing summary
        if self.existing_summary:
            base_prompt += f"""

Existing summary from before:
{self.existing_summary}

Provide an updated summary that incorporates both the previous work and the \
new conversation."""

        prompt = f"""{base_prompt}

Conversation:
{conversation_text}

Summary:"""
        return prompt

    # ========= SEARCH METHODS =========

    def _simple_text_search(self, keywords: List[str], top_k: int = 4) -> str:
        r"""Perform simple keyword-based search through current session
        history.

        Args:
            keywords (List[str]): List of keywords to search for.
            top_k (int): Maximum number of results to return.

        Returns:
            str: Formatted search results.
        """
        results: List[Dict[str, Any]] = []
        keyword_terms = [keyword.lower() for keyword in keywords]

        # Read current session history file
        history_file = self.working_directory / "history.md"
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split content into message sections
            # (each message starts with "### Message")
            sections = content.split('### Message')[1:]  # Skip the header part

            for i, section in enumerate(sections):
                if not section.strip():
                    continue

                section_lower = section.lower()

                # count how many keywords appear in this section
                keyword_matches = sum(
                    1 for keyword in keyword_terms if keyword in section_lower
                )

                if keyword_matches > 0:
                    results.append(
                        {
                            'content': f"### Message{section.strip()}",
                            'keyword_count': keyword_matches,
                            'message_num': i + 1,
                        }
                    )

        except Exception as e:
            logger.warning(f"Error reading history file: {e}")
            return ""

        # sort by keyword count and limit results
        results.sort(key=lambda x: x['keyword_count'], reverse=True)
        results = results[:top_k]

        if not results:
            return ""

        # format results
        formatted_sections = []
        for result in results:
            formatted_sections.append(
                f"Message {result['message_num']} "
                f"(keyword matches: {result['keyword_count']}):\n"
                f"{result['content']}\n"
            )

        return "\n---\n".join(formatted_sections)

    # ========= PUBLIC TOOL INTERFACE METHODS =========

    def summarize_full_conversation_history(self) -> str:
        r"""Save the conversation history and generate an intelligent summary.

        This function should be used when the memory becomes cluttered with too
        many unrelated conversations or information that might be irrelevant to
        the core task. It will generate a summary and save both the summary
        and full conversation history to markdown files. Then it clears the
        memory and replaces it with the summary for a context refresh. The
        conversation must flow naturally from the summary.

        Returns:
            str: Success message with brief summary, or error message.
        """
        try:
            # Get current memory count before compression
            context_records = self.agent.memory.retrieve()
            message_count = len(context_records)

            if message_count == 0:
                return "No conversation history found to save."

            # Get memory records and compress directly
            memory_records = [cr.memory_record for cr in context_records]

            # Use compression service directly to avoid tool calling loops
            summary = self._compress_and_save(memory_records)

            # empty memory and replace it with the summary
            self._refresh_context_with_summary(summary)

            logger.info(
                f"Context compression completed - {message_count} "
                f"messages processed"
            )

            return (
                "Full context summarized, summary added as system message, "
                "and full history removed."
            )

        except Exception as e:
            error_msg = f"Failed to save conversation memory: {e}"
            logger.error(error_msg)
            return error_msg

    def _refresh_context_with_summary(self, summary: str) -> bool:
        r"""Empty the agent's memory and replace it with a summary
        of the conversation history.

        Args:
            summary (str): The summary of the conversation history.

        Returns:
            bool: True if the context was refreshed successfully, False
                otherwise.
        """
        try:
            # clear the memory
            self.agent.clear_memory()

            # add summary as context
            if summary and summary.strip():
                from camel.messages import BaseMessage
                from camel.types import OpenAIBackendRole

                summary_message = BaseMessage.make_assistant_message(
                    role_name="Assistant",
                    content=f"[Context Summary]\n\n{summary}",
                )
                self.agent.update_memory(
                    summary_message, OpenAIBackendRole.SYSTEM
                )
                return True
            return False

        except Exception as e:
            logger.error(
                f"Failed to empty memory and replace it with summary: {e}"
            )
            return False

    def get_conversation_memory_info(self) -> str:
        r"""Get information about the current conversation memory state
        and saved files. The information includes:
        - Number of messages in memory
        - Save directory
        - If summary and history files exist and how many
        characters they have

        Returns:
            str: Information about current memory and saved files.
        """
        try:
            # Current memory info
            current_records = self.agent.memory.retrieve()
            current_count = len(current_records)

            info_msg = f"Current messages in memory: {current_count}\n"
            info_msg += f"Save directory: {self.working_directory}\n"

            # Check if saved files exist
            try:
                summary_content = self._load_summary()
                history_content = self._load_history()

                if summary_content.strip():
                    info_msg += (
                        f"Summary file: Available ({len(summary_content)} "
                        f"chars)\n"
                    )
                else:
                    info_msg += "Summary file: Not found\n"

                if history_content.strip():
                    info_msg += (
                        f"History file: Available ({len(history_content)} "
                        f"chars)\n"
                    )
                else:
                    info_msg += "History file: Not found\n"

            except Exception:
                info_msg += "Saved files: Unable to check\n"

            # Add search capability status
            info_msg += "Text search: Enabled (lightweight file-based)\n"

            # Count available session histories
            base_dir = self.working_directory.parent
            session_pattern = str(base_dir / "session_*" / "history.md")
            session_count = len(glob.glob(session_pattern))
            info_msg += f"Searchable sessions: {session_count}\n"

            return info_msg

        except Exception as e:
            error_msg = f"Failed to get memory info: {e}"
            logger.error(error_msg)
            return error_msg

    def search_full_conversation_history(
        self,
        keywords: List[str],
        top_k: int = 4,
    ) -> str:
        r"""Search the conversation history using keyword matching. This is
        used when information is missing from the summary and the current
        conversation, and can potentially be found in the full conversation
        history before it was summarized.

        Searches through the current session's history.md file to find the
        top messages that contain the most keywords.

        Args:
            keywords (List[str]): List of keywords to search for. The
                keywords must be explicitly related to the information
                the user is looking for, and not general terms that
                might be found about any topic. For example, if the user
                is searching for the price of the flight to "Paris"
                which was discussed previously, the keywords should be
                ["Paris", "price", "flight", "$", "costs"].
            top_k (int): The number of results to return (default 4).

        Returns:
            str: The search results or error message.
        """
        try:
            # Only search current session history
            current_history = self.working_directory / "history.md"
            if not current_history.exists():
                return "No history file found in current session."

            logger.info("Searching through current session history")

            # Perform keyword-based search
            search_results = self._simple_text_search(
                keywords=keywords,
                top_k=top_k,
            )

            if search_results and search_results.strip():
                keywords_str = ", ".join(keywords)
                formatted_results = (
                    f"Found relevant conversation excerpts for keywords: "
                    f"'{keywords_str}'\n\n"
                    f"--- Search Results ---\n"
                    f"{search_results}\n"
                    f"--- End Results ---\n\n"
                    f"Note: Results are ordered by keyword match count."
                )
                return formatted_results
            else:
                keywords_str = ", ".join(keywords)
                return (
                    f"No relevant conversations found for keywords: "
                    f"'{keywords_str}'. "
                    f"Try different keywords."
                )

        except Exception as e:
            error_msg = f"Failed to search conversation history: {e}"
            logger.error(error_msg)
            return error_msg

    def should_compress_context(
        self, message_limit: int = 40, token_limit: Optional[int] = None
    ) -> bool:
        r"""Check if context should be compressed based on limits.

        Args:
            message_limit (int): Maximum number of messages before compression.
            token_limit (Optional[int]): Maximum number of tokens before
                compression.

        Returns:
            bool: True if context should be compressed.
        """
        try:
            conversation_message_count = len(self.agent.memory.retrieve())

            # check token limit first (more efficient)
            if token_limit:
                _, token_count = self.agent.memory.get_context()
                if token_count > token_limit:
                    return True

            # check message limit
            if conversation_message_count > message_limit:
                return True

            return False

        except Exception as e:
            logger.error(
                f"Error checking if context should be compressed: {e}"
            )
            return False

    # ========= UTILITY METHODS =========

    def reset(self) -> None:
        r"""Reset the service by clearing the stored summary."""
        self.existing_summary = None
        self.compressed_message_uuids.clear()
        self.compression_count = 0
        logger.info(
            "Context summarizer toolkit reset - previous summary and "
            "compression tracking cleared"
        )

    def get_current_summary(self) -> Optional[str]:
        r"""Get the current stored summary without generating a new one.

        Returns:
            Optional[str]: The current summary, or None if no summary exists.
        """
        return self.existing_summary

    def set_summary(self, summary: str) -> None:
        r"""Manually set the current summary.

        Args:
            summary (str): The summary to store.
        """
        self.existing_summary = summary
        logger.info("Summary manually set")

    def get_tools(self) -> List[FunctionTool]:
        r"""Get the tools for the ContextSummarizerToolkit.

        Returns:
            List[FunctionTool]: The list of tools.
        """
        return [
            FunctionTool(self.summarize_full_conversation_history),
            FunctionTool(self.search_full_conversation_history),
            FunctionTool(self.get_conversation_memory_info),
        ]
