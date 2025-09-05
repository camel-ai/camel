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

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.logger import get_logger

if TYPE_CHECKING:
    from camel.agents import ChatAgent
    from camel.memories.records import MemoryRecord

logger = get_logger(__name__)


class ContextUtility:
    r"""Utility class for context management and file operations.

    This utility provides generic functionality for managing context files,
    markdown generation, and session management that can be used by
    context-related features.

    Key features:
    - Session-based directory management
    - Generic markdown file operations
    - Text-based search through files
    - File metadata handling
    - Agent memory record retrieval
    """

    def __init__(self, working_directory: Optional[str] = None):
        r"""Initialize the ContextUtility.

        Args:
            working_directory (str, optional): The directory path where files
                will be stored. If not provided, a default directory will be
                used.
        """
        self.working_directory_param = working_directory
        self._setup_storage(working_directory)

    def _setup_storage(self, working_directory: Optional[str]) -> None:
        r"""Initialize session-specific storage paths and create directory
        structure for context file management."""
        self.session_id = self._generate_session_id()

        if working_directory:
            self.working_directory = Path(working_directory).resolve()
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                self.working_directory = Path(camel_workdir) / "context_files"
            else:
                self.working_directory = Path("context_files")

        # Create session-specific directory
        self.working_directory = self.working_directory / self.session_id
        self.working_directory.mkdir(parents=True, exist_ok=True)

    def _generate_session_id(self) -> str:
        r"""Create timestamp-based unique identifier for isolating
        current session files from other sessions."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        return f"session_{timestamp}"

    # ========= GENERIC FILE MANAGEMENT METHODS =========

    def _create_or_update_note(self, note_name: str, content: str) -> str:
        r"""Write content to markdown file, creating new file or
        overwriting existing one with UTF-8 encoding.

        Args:
            note_name (str): Name of the note (without .md extension).
            content (str): Content to write to the note.

        Returns:
            str: Success message.
        """
        try:
            file_path = self.working_directory / f"{note_name}.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Note '{note_name}.md' created successfully"
        except Exception as e:
            logger.error(f"Error creating note {note_name}: {e}")
            return f"Error creating note: {e}"

    def save_markdown_file(
        self,
        filename: str,
        content: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        r"""Generic method to save any markdown content to a file.

        Args:
            filename (str): Name without .md extension.
            content (str): Main content to save.
            title (str, optional): Title for the markdown file.
            metadata (Dict, optional): Additional metadata to include.

        Returns:
            str: Success message or error message.
        """
        try:
            markdown_content = ""

            # Add title if provided
            if title:
                markdown_content += f"# {title}\n\n"

            # Add metadata section if provided
            if metadata:
                markdown_content += "## Metadata\n\n"
                for key, value in metadata.items():
                    markdown_content += f"- {key}: {value}\n"
                markdown_content += "\n"

            # Add main content
            markdown_content += content

            self._create_or_update_note(filename, markdown_content)
            logger.info(
                f"Markdown file saved to "
                f"{self.working_directory / f'{filename}.md'}"
            )
            return f"Markdown file '{filename}.md' saved successfully"

        except Exception as e:
            logger.error(f"Error saving markdown file {filename}: {e}")
            return f"Error saving markdown file: {e}"

    def load_markdown_file(self, filename: str) -> str:
        r"""Generic method to load any markdown file.

        Args:
            filename (str): Name without .md extension.

        Returns:
            str: File content or empty string if not found.
        """
        try:
            file_path = self.working_directory / f"{filename}.md"
            if file_path.exists():
                return file_path.read_text(encoding="utf-8")
            return ""
        except Exception as e:
            logger.error(f"Error loading markdown file {filename}: {e}")
            return ""

    def file_exists(self, filename: str) -> bool:
        r"""Verify presence of markdown file in current session directory.

        Args:
            filename (str): Name without .md extension.

        Returns:
            bool: True if file exists, False otherwise.
        """
        file_path = self.working_directory / f"{filename}.md"
        return file_path.exists()

    def list_markdown_files(self) -> List[str]:
        r"""Discover all markdown files in current session directory
        and return their base names for reference.

        Returns:
            List[str]: List of filenames without .md extension.
        """
        try:
            md_files = list(self.working_directory.glob("*.md"))
            return [f.stem for f in md_files]
        except Exception as e:
            logger.error(f"Error listing markdown files: {e}")
            return []

    # ========= GENERIC AGENT MEMORY METHODS =========

    def get_agent_memory_records(
        self, agent: "ChatAgent"
    ) -> List["MemoryRecord"]:
        r"""Retrieve conversation history from agent's memory system.

        Args:
            agent (ChatAgent): The agent to extract memory records from.

        Returns:
            List[MemoryRecord]: List of memory records from the agent.
        """
        try:
            context_records = agent.memory.retrieve()
            return [cr.memory_record for cr in context_records]
        except Exception as e:
            logger.error(f"Error extracting memory records: {e}")
            return []

    def format_memory_as_conversation(
        self, memory_records: List["MemoryRecord"]
    ) -> str:
        r"""Transform structured memory records into human-readable
        conversation format with role labels and message content.

        Args:
            memory_records (List[MemoryRecord]): Memory records to format.

        Returns:
            str: Formatted conversation text.
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

    # ========= SESSION MANAGEMENT METHODS =========

    def create_session_directory(
        self, base_dir: Optional[str] = None, session_id: Optional[str] = None
    ) -> Path:
        r"""Create a session-specific directory.

        Args:
            base_dir (str, optional): Base directory. If None, uses current
                working directory.
            session_id (str, optional): Custom session ID. If None, generates
                new one.

        Returns:
            Path: The created session directory path.
        """
        if session_id is None:
            session_id = self._generate_session_id()

        if base_dir:
            base_path = Path(base_dir).resolve()
        else:
            base_path = self.working_directory.parent

        session_dir = base_path / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def get_session_metadata(self) -> Dict[str, Any]:
        r"""Collect comprehensive session information including identifiers,
        timestamps, and directory paths for tracking and reference.

        Returns:
            Dict[str, Any]: Session metadata including ID, timestamp,
                directory.
        """
        return {
            'session_id': self.session_id,
            'working_directory': str(self.working_directory),
            'created_at': datetime.now().isoformat(),
            'base_directory': str(self.working_directory.parent),
        }

    def list_sessions(self, base_dir: Optional[str] = None) -> List[str]:
        r"""Discover all available session directories for browsing
        historical conversations and context files.

        Args:
            base_dir (str, optional): Base directory to search. If None, uses
                parent of working directory.

        Returns:
            List[str]: List of session directory names.
        """
        try:
            if base_dir:
                search_dir = Path(base_dir)
            else:
                search_dir = self.working_directory.parent

            session_dirs = [
                d.name
                for d in search_dir.iterdir()
                if d.is_dir() and d.name.startswith('session_')
            ]
            return sorted(session_dirs)
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    # ========= GENERIC SEARCH METHODS =========

    def search_in_file(
        self, file_path: Path, keywords: List[str], top_k: int = 4
    ) -> str:
        r"""Perform keyword-based search through file sections,
        ranking results by keyword frequency and returning top matches.

        Args:
            file_path (Path): Path to the file to search.
            keywords (List[str]): Keywords to search for.
            top_k (int): Maximum number of results to return.

        Returns:
            str: Formatted search results.
        """
        results: List[Dict[str, Any]] = []
        keyword_terms = [keyword.lower() for keyword in keywords]

        try:
            if not file_path.exists():
                return ""

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split content into sections (assuming ### headers)
            sections = content.split('### ')[1:]  # Skip the header part

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
                            'content': f"### {section.strip()}",
                            'keyword_count': keyword_matches,
                            'section_num': i + 1,
                        }
                    )

        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {e}")
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
                f"Section {result['section_num']} "
                f"(keyword matches: {result['keyword_count']}):\n"
                f"{result['content']}\n"
            )

        return "\n---\n".join(formatted_sections)

    # ========= UTILITY METHODS =========

    def get_working_directory(self) -> Path:
        r"""Retrieve the session-specific directory path where
        all context files are stored.

        Returns:
            Path: The working directory path.
        """
        return self.working_directory

    def get_session_id(self) -> str:
        r"""Retrieve the unique identifier for the current session
        used for file organization and tracking.

        Returns:
            str: The session ID.
        """
        return self.session_id
