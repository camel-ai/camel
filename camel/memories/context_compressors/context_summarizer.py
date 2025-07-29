# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

import os
from pathlib import Path
from datetime import datetime
from typing import List, TYPE_CHECKING, Optional

from camel.logger import get_logger
from camel.toolkits.note_taking_toolkit import NoteTakingToolkit

if TYPE_CHECKING:
    from camel.agents import ChatAgent
    from camel.memories.records import MemoryRecord

logger = get_logger(__name__)

class ContextCompressionService:
    r"""Handles the compression of conversation context including summarization and persistence.

    This class takes the conversation history or a list of memory records and
    creates intelligent summaries that preserve important context about work completed.
    It supports iterative summarization by storing previous summaries.

    Args:
        summary_agent (ChatAgent): The agent used to generate the summaries.
        working_directory (Optional[str]): Directory where memory files will be saved.
            If None, a default directory will be created.
    """

    def __init__(self, 
        summary_agent: "ChatAgent",
        working_directory: Optional[str] = None,
    ) -> None:
        self.summary_agent = summary_agent
        self.existing_summary: Optional[str] = ""
        
        # Setup file storage
        self._setup_storage(working_directory)

    def _setup_storage(self, working_directory: Optional[str]) -> None:
        r"""Setup the storage directory and note-taking toolkit."""
        self.session_id = self._generate_session_id()
        
        if working_directory:
            self.working_directory = Path(working_directory).resolve()
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                self.working_directory = Path(camel_workdir) / "context_compression"
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

    def summarize_messages(self, 
        memory_records: List["MemoryRecord"],
    ) -> str:
        r"""Generate a summary of the conversation context.
        
        Args:
            memory_records (List["MemoryRecord"]): A list of memory records to summarize.

        Returns:
            str: The summary of the conversation context.
        """
        if not memory_records:
            logger.warning("No memory records provided. Returning existing summary.")
            return self.existing_summary or ""

        try:
            # 0. set the is_compressing_context flag to True
            self.summary_agent.is_compressing_context = True

            # 1. format the conversation 
            conversation_text = self._format_conversation(memory_records)

            # 2. create the summary prompt
            summary_prompt = self._create_summary_prompt(conversation_text)

            # 3. generate summary using the agent
            response = self.summary_agent.step(summary_prompt)

            # 4. extract the summary from response and store
            summary_content = response.msgs[-1].content.strip()
            self.existing_summary = summary_content

            logger.info(f"Successfully generated summary for {len(memory_records)} messages.")
            return summary_content
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return self.existing_summary or ""
        
        finally:
            # 5. set the is_compressing_context flag to False as we're finished
            self.summary_agent.is_compressing_context = False

    def save_summary(self, summary: str) -> str:
        r"""Save a summary to a markdown file.

        Args:
            summary (str): The summary text to save.

        Returns:
            str: Success message or error message.
        """
        try:
            # Format summary with metadata
            summary_content = f"# Conversation Summary: {self.session_id}\n\n"
            summary_content += f"## Metadata\n\n"
            summary_content += f"- Save Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            summary_content += f"- Session ID: {self.session_id}\n\n"
            summary_content += f"## Summary\n\n{summary}\n"

            self._note_toolkit.create_note(self.summary_filename, summary_content)
            logger.info(f"Summary saved to {self.working_directory / f'{self.summary_filename}.md'}")
            return f"Summary saved successfully to {self.summary_filename}.md"
        except Exception as e:
            logger.error(f"Error saving summary: {e}")
            return f"Error saving summary: {e}"

    def save_history(self, memory_records: List["MemoryRecord"]) -> str:
        r"""Save the full conversation history to a markdown file.

        Args:
            memory_records (List["MemoryRecord"]): The list of memory records to save.

        Returns:
            str: Success message or error message.
        """
        try:
            # Format history with metadata
            history_content = f"# Conversation History: {self.session_id}\n\n"
            history_content += f"## Metadata\n\n"
            history_content += f"- Save Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            history_content += f"- Total Messages: {len(memory_records)}\n"
            history_content += f"- Session ID: {self.session_id}\n\n"
            history_content += f"## Full Transcript\n\n"

            for i, record in enumerate(memory_records):
                message = record.message
                role = getattr(message, "role_name", "unknown")
                content = getattr(message, "content", str(message))
                agent_id = record.agent_id or "unknown"
                role_at_backend = record.role_at_backend.value if \
                    hasattr(record.role_at_backend, 'value') else \
                        str(record.role_at_backend)

                history_content += f"### Message {i+1} - {role}\n"
                history_content += f"**Agent ID:** {agent_id}  \n"
                history_content += f"**Backend Role:** {role_at_backend}  \n"
                history_content += f"**Content:**\n```\n{content}\n```\n\n"
                history_content += f"---\n\n"

            self._note_toolkit.create_note(self.history_filename, history_content)
            logger.info(f"History saved to {self.working_directory / f'{self.history_filename}.md'}")
            return f"History saved successfully to {self.history_filename}.md"
        except Exception as e:
            logger.error(f"Error saving history: {e}")
            return f"Error saving history: {e}"

    def load_summary(self) -> str:
        r"""Load the summary from the markdown file.

        Returns:
            str: The summary content, or empty string if not found.
        """
        try:
            return self._note_toolkit.read_note(self.summary_filename)
        except Exception as e:
            logger.error(f"Error loading summary: {e}")
            return ""

    def load_history(self) -> str:
        r"""Load the history from the markdown file.

        Returns:
            str: The history content, or empty string if not found.
        """
        try:
            return self._note_toolkit.read_note(self.history_filename)
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return ""

    def compress_and_save(self, memory_records: List["MemoryRecord"]) -> str:
        r"""Complete compression pipeline: summarize and save both history and summary.

        Args:
            memory_records (List["MemoryRecord"]): The memory records to compress and save.

        Returns:
            str: The generated summary text.
        """
        try:
            # Generate summary
            summary = self.summarize_messages(memory_records)
            
            # Save both history and summary
            history_result = self.save_history(memory_records)
            summary_result = self.save_summary(summary)
            
            if "Error" not in history_result and "Error" not in summary_result:
                logger.info(f"Context compression completed successfully. Files saved to {self.working_directory}")
                return summary
            else:
                error_msg = f"Compression partially failed. History: {history_result}, Summary: {summary_result}"
                logger.error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error in compress_and_save: {e}")
            return self.existing_summary or ""
    
    def _format_conversation(
        self,
        memory_records: List["MemoryRecord"],
    ) -> str:
        r"""Format the conversation into a text string.

        Args:
            memory_records (List["MemoryRecord"]): A list of memory records to format.

        Returns:
            str: The formatted conversation.
        """
        conversation_lines = []

        for record in memory_records:
            role = record.role_at_backend.value if \
                hasattr(record.role_at_backend, 'value')\
                else str(record.role_at_backend)
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
        
        base_prompt = """The following is a conversation history of a large language model agent.
Analyze it and extract the key information from it. The information will be
passed on to a new agent that will use it to understand the problem and continue
working on it without having to start from scratch. Focus on:
- User's main goal (e.g. "The user wants my help with data analysis of customer sales data.")
- Key information about the user and their preferences (e.g. "The user is a student who prefers concise bullet-point responses.")
- Tasks that were accomplished (e.g. "I found the top 10 customers by total sales amounts, wrote a Python script to...")
- Tools and methods that were used **if tool/function calls have been made** (e.g. "I used CodeExecutionToolkit to execute a Python script to analyze the data.")
- Important discoveries or solutions found (e.g. "I found there are duplicate entries in the customer name column, which must be taken care of before proceeding with the analysis.")
- Technical approaches that worked **if the task is technical** (e.g. "Using Pandas + matplotlib seem to yield the best responses for the user's queries.)"""

        # if we want to extend an existing summary
        if self.existing_summary:
            base_prompt += f"""

Existing summary from before:
{self.existing_summary}

Provide an updated summary that incorporates both the previous work and the new conversation."""

        prompt = f"""{base_prompt}

Conversation:
{conversation_text}

Summary:"""
        return prompt

    def reset(self) -> None:
        r"""Reset the service by clearing the stored summary."""
        self.existing_summary = None
        logger.info("Context compression service reset - previous summary cleared")

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