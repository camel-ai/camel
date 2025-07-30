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
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from camel.logger import get_logger
from camel.memories.context_compressors import ContextCompressionService
from camel.retrievers import AutoRetriever
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.toolkits.retrieval_toolkit import RetrievalToolkit
from camel.types import StorageType

if TYPE_CHECKING:
    from camel.agents import ChatAgent

logger = get_logger(__name__)


class MarkdownMemoryToolkit(BaseToolkit):
    r"""A toolkit that provides memory storage in Markdown files for agents.
    With this toolkit, agents can save and manage their conversation
    memory using markdown files, and search through conversation history
    using semantic search.
    """

    def __init__(
        self,
        agent: "ChatAgent",
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        r"""Initialize the MarkdownMemoryToolkit.

        Args:
            agent (ChatAgent): The agent to use for the toolkit.
                This is required to access the agent's memory.
            working_directory (str, optional): The directory path where notes
                will be stored. If not provided, a default directory will be
                used.
            timeout (Optional[float]): The timeout for the toolkit.
        """
        super().__init__(timeout=timeout)

        self.agent = agent
        self.working_directory = working_directory
        self.retrieval_toolkit: Optional[RetrievalToolkit] = None

        # Note: This toolkit provides manual memory management.
        # It does not automatically enable auto-compression to avoid conflicts.

        # Create a separate agent for summarization without tools to avoid
        # circular calls
        from camel.agents import ChatAgent

        self.summary_agent = ChatAgent(
            system_message="You are a helpful assistant that creates concise "
            "summaries of conversations.",
            model=self.agent.model_backend,
            agent_id=f"{self.agent.agent_id}_summarizer",
        )

        # initialize the context compression service for this toolkit
        self.compression_service = ContextCompressionService(
            summary_agent=self.summary_agent,  # Use new agent without tools
            working_directory=self.working_directory,
        )

        # initialize the retrieval
        try:
            vector_storage_path = str(
                Path(self.compression_service.working_directory).parent
                / "conversation_vectors"
            )

            self.retrieval_toolkit = RetrievalToolkit(
                auto_retriever=AutoRetriever(
                    vector_storage_local_path=vector_storage_path,
                    storage_type=StorageType.QDRANT,
                ),
            )
            logger.info("Semantic search enabled for conversation history")
        except Exception as e:
            logger.warning(
                f"Failed to initialize semantic search: {e}. Semantic search "
                f"disabled."
            )
            self.retrieval_toolkit = None

    def summarize_context_and_save_memory(self) -> str:
        r"""Save the conversation history and generate an intelligent summary.

        This function should be used when the memory becomes cluttered with too
        many unrelated conversations or information that might be irrelevant to
        the core task. It will generate a summary and save both the summary
        and full conversation history to markdown files. Then it clears the
        memory and replaces it with the summary for a context refresh.

        Returns:
            str: Success message with brief summary, or error message.
        """
        try:
            # Get current memory count before compression
            context_records = self.agent.memory.retrieve()
            message_count = len(context_records)

            if message_count == 0:
                return "No conversation history found to save."

            # Get memory records and compress directly using compression
            # service
            memory_records = [cr.memory_record for cr in context_records]

            # Use compression service directly to avoid tool calling loops
            summary = self.compression_service.compress_and_save(
                memory_records
            )

            # empty memory and replace it with the summary
            self.agent.refresh_context_with_summary(summary)

            logger.info(
                f"Used compression service directly - {message_count} "
                f"messages processed"
            )

            # Use the summary we just generated for the success message
            summary_preview = (
                summary[:100] + "..." if len(summary) > 100 else summary
            )

            success_msg = (
                f"Memory saved and refreshed successfully!\n"
                f"Session directory: "
                f"{self.compression_service.working_directory.name}\n"
                f"Messages processed: {message_count}\n"
                f"Summary: {summary_preview}"
            )

            return success_msg

        except Exception as e:
            error_msg = f"Failed to save conversation memory: {e}"
            logger.error(error_msg)
            return error_msg

    def load_memory_context(self) -> str:
        r"""Load the saved summary to restore previous context.

        This function loads the previously saved summary file to help the agent
        understand the prior conversation context without loading the full
        history.

        Returns:
            str: The loaded summary content, or message if no summary found.
        """
        try:
            summary_content = self.compression_service.load_summary()

            if summary_content.strip():
                return f"Previous context loaded:\n\n{summary_content}"
            else:
                return "No previous summary found to load."

        except Exception as e:
            error_msg = f"Failed to load memory context: {e}"
            logger.error(error_msg)
            return error_msg

    def get_memory_info(self) -> str:
        r"""Get information about the current memory state and saved files.

        Returns:
            str: Information about current memory and saved files.
        """
        try:
            # Current memory info
            current_records = self.agent.memory.retrieve()
            current_count = len(current_records)

            info_msg = f"Current messages in memory: {current_count}\n"
            working_dir = self.compression_service.working_directory
            info_msg += f"Save directory: {working_dir}\n"

            # Check if saved files exist
            try:
                summary_content = self.compression_service.load_summary()
                history_content = self.compression_service.load_history()

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

            # Add semantic search status
            if self.retrieval_toolkit:
                info_msg += "Semantic search: Enabled\n"

                # Count available session histories
                base_dir = Path(
                    self.compression_service.working_directory
                ).parent
                session_pattern = str(base_dir / "session_*" / "history.md")
                session_count = len(glob.glob(session_pattern))
                info_msg += f"Searchable sessions: {session_count}\n"
            else:
                info_msg += "Semantic search: Disabled\n"

            return info_msg

        except Exception as e:
            error_msg = f"Failed to get memory info: {e}"
            logger.error(error_msg)
            return error_msg

    def search_conversation_history(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.4,
        search_current_session: bool = True,
        search_all_sessions: bool = False,
    ) -> str:
        r"""Search the conversation history using semantic search.

        Searches through the history.md files to find relevant past
        conversations based on the query.

        Args:
            query (str): The query to search for.
            top_k (int): The number of results to return.
            similarity_threshold (float): The similarity threshold for the
                results.
            search_current_session (bool): Whether to search the current
                session.
            search_all_sessions (bool): Whether to search all sessions.

        Returns:
            str: The search results or error message.
        """
        if not self.retrieval_toolkit:
            return (
                "Semantic search is not available. Retrieval toolkit "
                "failed to initialize."
            )

        try:
            history_files = []
            base_dir = Path(self.compression_service.working_directory).parent

            similarity_threshold = 0.4

            if search_current_session:
                # Add current session history
                current_history = (
                    self.compression_service.working_directory / "history.md"
                )
                if current_history.exists():
                    history_files.append(str(current_history))

            if search_all_sessions:
                # Add all session histories
                session_pattern = str(base_dir / "session_*" / "history.md")
                session_histories = glob.glob(session_pattern)
                history_files.extend(session_histories)

            if not history_files:
                return "No history files found to search."

            # remove duplicates and preserving order
            history_files = list(dict.fromkeys(history_files))

            logger.info(
                f"Searching through {len(history_files)} history file(s)"
            )

            # Perform semantic retrieval
            search_results = self.retrieval_toolkit.information_retrieval(
                query=query,
                contents=history_files,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

            if search_results and search_results.strip():
                formatted_results = (
                    f"Found relevant conversation excerpts for query: "
                    f"'{query}'\n\n"
                    f"--- Search Results ---\n"
                    f"{search_results}\n"
                    f"--- End Results ---\n\n"
                    f"Note: Results are ordered by semantic similarity to "
                    f"your query."
                )
                return formatted_results
            else:
                return (
                    f"No relevant conversations found for query: '{query}'. "
                    f"Try different keywords or lower the similarity "
                    f"threshold."
                )

        except Exception as e:
            error_msg = f"Failed to search conversation history: {e}"
            logger.error(error_msg)
            return error_msg

    def get_tools(self) -> List[FunctionTool]:
        r"""Get the tools for the MarkdownMemoryToolkit.

        Returns:
            List[FunctionTool]: The list of tools.
        """
        return [
            FunctionTool(self.summarize_context_and_save_memory),
            FunctionTool(self.load_memory_context),
            FunctionTool(self.get_memory_info),
            FunctionTool(self.search_conversation_history),
        ]
