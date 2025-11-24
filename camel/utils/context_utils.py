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
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field

from camel.logger import get_logger

if TYPE_CHECKING:
    from camel.agents import ChatAgent
    from camel.memories.records import MemoryRecord

logger = get_logger(__name__)


class WorkflowSummary(BaseModel):
    r"""Pydantic model for structured workflow summaries.

    This model defines the schema for workflow memories that can be reused
    by future agents for similar tasks.
    """

    task_title: str = Field(
        description="A short, generic title of the main task (≤ 10 words). "
        "Avoid product- or case-specific names. "
        "Example: 'List GitHub stargazers', "
        "'Remind weekly meetings on Slack', "
        "'Find best leads and turn them into a table on Notion'."
    )
    task_description: str = Field(
        description="One-paragraph summary of what the user asked for "
        "(≤ 80 words). "
        "No implementation details; just the outcome the user wants. "
        "Example: Find academic professors who might be interested in the "
        "upcoming research paper on Graph-based Agentic Memory, extract "
        "their email addresses, affiliations, and research interests, "
        "and create a table on Notion with this information."
    )
    tools: List[str] = Field(
        description="Bullet list of tool calls or functions calls used. "
        "For each: name → what it did → why it was useful (one line each). "
        "This field is explicitly for tool call messages or the MCP "
        "servers used."
        "Example: - ArxivToolkit: get authors from a paper title, "
        "it helped find academic professors who authored a particular "
        "paper, and then get their email addresses, affiliations, and "
        "research interests.",
        default_factory=list,
    )
    steps: List[str] = Field(
        description="Numbered, ordered actions the agent took to complete "
        "the task. Each step starts with a verb and is generic "
        "enough to be repeatable. "
        "Example: 1. Find the upcoming meetings on Google Calendar "
        " today. 2. Send participants a reminder on Slack...",
        default_factory=list,
    )
    failure_and_recovery_strategies: List[str] = Field(
        description="[Optional] Bullet each incident with symptom, "
        " cause (if known), fix/workaround, verification of "
        "recovery. Leave empty if no failures. "
        "failures. Example: Running the script for consumer data "
        "analysis failed since Pandas package was not installed. "
        "Fixed by running 'pip install pandas'.",
        default_factory=list,
    )
    notes_and_observations: str = Field(
        description="[Optional] Anything not covered in previous fields "
        "that is critical to know for future executions of the task. "
        "Leave empty if no notes. Do not repeat any information, or "
        "mention trivial details. Only what is essential. "
        "Example: The user likes to be in the "
        "loop of the task execution, make sure to check with them the "
        "plan before starting to work, and ask them for approval "
        "mid-task by using the HumanToolkit.",
        default="",
    )
    tags: List[str] = Field(
        description="3-10 categorization tags that describe the workflow "
        "type, domain, and key capabilities. Use lowercase with hyphens. "
        "Tags should be broad, reusable categories to help with semantic "
        "matching to similar tasks. "
        "Examples: 'data-analysis', 'web-scraping', 'api-integration', "
        "'code-generation', 'file-processing', 'database-query', "
        "'text-processing', 'image-manipulation', 'email-automation', "
        "'report-generation'.",
        default_factory=list,
    )

    @classmethod
    def get_instruction_prompt(cls) -> str:
        r"""Get the instruction prompt for this model.

        Returns:
            str: The instruction prompt that guides agents to produce
                structured output matching this schema.
        """
        return (
            'You are writing a compact "workflow memory" so future agents '
            'can reuse what you just did for future tasks. '
            'Be concise, precise, and action-oriented. Analyze the '
            'conversation and extract the key workflow information '
            'following the provided schema structure. If a field has no '
            'content, still include it per the schema, but keep it empty. '
            'The length of your workflow must be proportional to the '
            'complexity of the task. Example: If the task is simply '
            'about a simple math problem, the workflow must be short, '
            'e.g. <60 words. By contrast, if the task is complex and '
            'multi-step, such as finding particular job applications based '
            'on user CV, the workflow must be longer, e.g. about 120 words. '
            'For tags, provide 3-5 broad categorization tags using lowercase '
            'with hyphens (e.g., "data-analysis", "web-scraping") that '
            'describe the workflow domain, type, and key capabilities to '
            'help future agents discover this workflow when working on '
            'similar tasks.'
        )


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
    - Shared session management for workforce workflows
    """

    # maximum filename length for workflow files (chosen for filesystem
    # compatibility and readability)
    MAX_WORKFLOW_FILENAME_LENGTH: ClassVar[int] = 50

    # Class variables for shared session management
    _shared_sessions: ClassVar[Dict[str, 'ContextUtility']] = {}
    _default_workforce_session: ClassVar[Optional['ContextUtility']] = None

    def __init__(
        self,
        working_directory: Optional[str] = None,
        session_id: Optional[str] = None,
        create_folder: bool = True,
    ):
        r"""Initialize the ContextUtility.

        Args:
            working_directory (str, optional): The directory path where files
                will be stored. If not provided, a default directory will be
                used.
            session_id (str, optional): The session ID to use. If provided,
                this instance will use the same session folder as other
                instances with the same session_id. If not provided, a new
                session ID will be generated.
            create_folder (bool): Whether to create the session folder
                immediately. If False, the folder will be created only when
                needed (e.g., when saving files). Default is True for
                backward compatibility.
        """
        self.working_directory_param = working_directory
        self._setup_storage(working_directory, session_id, create_folder)

    def _setup_storage(
        self,
        working_directory: Optional[str],
        session_id: Optional[str] = None,
        create_folder: bool = True,
    ) -> None:
        r"""Initialize session-specific storage paths and optionally create
        directory structure for context file management."""
        self.session_id = session_id or self._generate_session_id()

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

        # Only create directory if requested
        if create_folder:
            self.working_directory.mkdir(parents=True, exist_ok=True)

    def _generate_session_id(self) -> str:
        r"""Create timestamp-based unique identifier for isolating
        current session files from other sessions."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        return f"session_{timestamp}"

    @staticmethod
    def sanitize_workflow_filename(
        name: str,
        max_length: Optional[int] = None,
    ) -> str:
        r"""Sanitize a name string for use as a workflow filename.

        Converts the input string to a safe filename by:
        - converting to lowercase
        - replacing spaces with underscores
        - removing special characters (keeping only alphanumeric and
          underscores)
        - truncating to maximum length if specified

        Args:
            name (str): The name string to sanitize (e.g., role_name or
                task_title).
            max_length (Optional[int]): Maximum length for the sanitized
                filename. If None, uses MAX_WORKFLOW_FILENAME_LENGTH.
                (default: :obj:`None`)

        Returns:
            str: Sanitized filename string suitable for filesystem use.
                Returns "agent" if sanitization results in empty string.

        Example:
            >>> ContextUtility.sanitize_workflow_filename("Data Analyst!")
            'data_analyst'
            >>> ContextUtility.sanitize_workflow_filename("Test@123", 5)
            'test1'
        """
        if max_length is None:
            max_length = ContextUtility.MAX_WORKFLOW_FILENAME_LENGTH

        # sanitize: lowercase, spaces to underscores, remove special chars
        clean_name = name.lower().replace(" ", "_")
        clean_name = re.sub(r'[^a-z0-9_]', '', clean_name)

        # truncate if too long
        if len(clean_name) > max_length:
            clean_name = clean_name[:max_length]

        # ensure it's not empty after sanitization
        if not clean_name:
            clean_name = "agent"

        return clean_name

    # ========= GENERIC FILE MANAGEMENT METHODS =========

    def _ensure_directory_exists(self) -> None:
        r"""Ensure the working directory exists, creating it if necessary."""
        self.working_directory.mkdir(parents=True, exist_ok=True)

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
            # Ensure directory exists before writing
            self._ensure_directory_exists()
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
            str: "success" on success, error message starting with "Error:"
                on failure.
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
                f"Markdown file '{filename}.md' saved successfully to "
                f"{self.working_directory / f'{filename}.md'}"
            )
            return "success"

        except Exception as e:
            logger.error(f"Error saving markdown file {filename}: {e}")
            return f"Error: {e}"

    def structured_output_to_markdown(
        self,
        structured_data: BaseModel,
        metadata: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None,
        field_mappings: Optional[Dict[str, str]] = None,
    ) -> str:
        r"""Convert any Pydantic BaseModel instance to markdown format.

        Args:
            structured_data: Any Pydantic BaseModel instance
            metadata: Optional metadata to include in the markdown
            title: Optional custom title, defaults to model class name
            field_mappings: Optional mapping of field names to custom
                section titles

        Returns:
            str: Markdown formatted content
        """
        markdown_content = []

        # Add metadata if provided
        if metadata:
            markdown_content.append("## Metadata\n")
            for key, value in metadata.items():
                markdown_content.append(f"- {key}: {value}")
            markdown_content.append("")

        # Add title
        if title:
            markdown_content.extend([f"## {title}", ""])
        else:
            model_name = structured_data.__class__.__name__
            markdown_content.extend([f"## {model_name}", ""])

        # Get model fields and values
        model_dict = structured_data.model_dump()

        for field_name, field_value in model_dict.items():
            # Use custom mapping or convert field name to title case
            if field_mappings and field_name in field_mappings:
                section_title = field_mappings[field_name]
            else:
                # Convert snake_case to Title Case
                section_title = field_name.replace('_', ' ').title()

            markdown_content.append(f"### {section_title}")

            # Handle different data types
            if isinstance(field_value, list):
                if field_value:
                    for i, item in enumerate(field_value):
                        if isinstance(item, str):
                            # Check if it looks like a numbered item already
                            if item.strip() and not item.strip()[0].isdigit():
                                # For steps or numbered lists, add numbers
                                if 'step' in field_name.lower():
                                    markdown_content.append(f"{i + 1}. {item}")
                                else:
                                    markdown_content.append(f"- {item}")
                            else:
                                markdown_content.append(f"- {item}")
                        else:
                            markdown_content.append(f"- {item!s}")
                else:
                    markdown_content.append(
                        f"(No {section_title.lower()} recorded)"
                    )
            elif isinstance(field_value, str):
                if field_value.strip():
                    markdown_content.append(field_value)
                else:
                    markdown_content.append(
                        f"(No {section_title.lower()} provided)"
                    )
            elif isinstance(field_value, dict):
                for k, v in field_value.items():
                    markdown_content.append(f"- **{k}**: {v}")
            else:
                markdown_content.append(str(field_value))

            markdown_content.append("")

        return "\n".join(markdown_content)

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

    def set_session_id(self, session_id: str) -> None:
        r"""Set a new session ID and update the working directory accordingly.

        This allows sharing session directories between multiple ContextUtility
        instances by using the same session_id.

        Args:
            session_id (str): The session ID to use.
        """
        self.session_id = session_id

        # Update working directory with new session_id
        if self.working_directory_param:
            base_dir = Path(self.working_directory_param).resolve()
        else:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                base_dir = Path(camel_workdir) / "context_files"
            else:
                base_dir = Path("context_files")

        self.working_directory = base_dir / self.session_id
        self.working_directory.mkdir(parents=True, exist_ok=True)

    def load_markdown_context_to_memory(
        self, agent: "ChatAgent", filename: str, include_metadata: bool = False
    ) -> str:
        r"""Load context from a markdown file and append it to agent memory.

        Args:
            agent (ChatAgent): The agent to append context to.
            filename (str): Name of the markdown file (without .md extension).
            include_metadata (bool): Whether to include metadata section in the
                loaded content. Defaults to False.

        Returns:
            str: Status message indicating success or failure with details.
        """
        try:
            content = self.load_markdown_file(filename)

            if not content.strip():
                return f"Context file not found or empty: {filename}"

            # Filter out metadata section if not requested
            if not include_metadata:
                content = self._filter_metadata_from_content(content)

            from camel.types import OpenAIBackendRole

            prefix_prompt = (
                "The following is the context from a previous "
                "session or workflow which might be useful for "
                "to the current task. This information might help you "
                "understand the background, choose which tools to use, "
                "and plan your next steps."
            )

            # Append workflow content to the agent's system message
            # This ensures the context persists when agents are cloned
            workflow_content = (
                f"\n\n--- Workflow Memory ---\n{prefix_prompt}\n\n{content}"
            )

            # Update the original system message to include workflow
            if agent._original_system_message is None:
                logger.error(
                    f"Agent {agent.agent_id} has no system message. "
                    "Cannot append workflow memory to system message."
                )
                return (
                    "Error: Agent has no system message to append workflow to"
                )

            # Update the current system message
            current_system_message = agent._system_message
            if current_system_message is not None:
                new_sys_content = (
                    current_system_message.content + workflow_content
                )
                agent._system_message = (
                    current_system_message.create_new_instance(new_sys_content)
                )

                # Replace the system message in memory
                # Clear and re-initialize with updated system message
                agent.memory.clear()
                agent.update_memory(
                    agent._system_message, OpenAIBackendRole.SYSTEM
                )

            char_count = len(content)
            log_msg = (
                f"Context appended to agent {agent.agent_id} "
                f"({char_count} characters)"
            )
            logger.info(log_msg)

            return log_msg

        except Exception as e:
            error_msg = f"Failed to load markdown context to memory: {e}"
            logger.error(error_msg)
            return error_msg

    def _filter_metadata_from_content(self, content: str) -> str:
        r"""Filter out metadata section from markdown content.

        Args:
            content (str): The full markdown content including metadata.

        Returns:
            str: Content with metadata section removed.
        """
        lines = content.split('\n')
        filtered_lines = []
        skip_metadata = False

        for line in lines:
            # Check if we're starting a metadata section
            if line.strip() == "## Metadata":
                skip_metadata = True
                continue

            # Check if we're starting a new section after metadata
            if (
                skip_metadata
                and line.startswith("## ")
                and "Metadata" not in line
            ):
                skip_metadata = False

            # Add line if we're not in metadata section
            if not skip_metadata:
                filtered_lines.append(line)

        # Clean up any extra whitespace at the beginning
        result = '\n'.join(filtered_lines).strip()
        return result

    # ========= WORKFLOW INFO METHODS =========

    def extract_workflow_info(self, file_path: str) -> Dict[str, Any]:
        r"""Extract info from a workflow markdown file.

        This method reads only the essential info from a workflow file
        (title, description, tags) for use in workflow selection without
        loading the entire workflow content.

        Args:
            file_path (str): Full path to the workflow markdown file.

        Returns:
            Dict[str, Any]: Workflow info including title, description,
                tags, and file_path. Returns empty dict on error.
        """
        import re

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            metadata: Dict[str, Any] = {'file_path': file_path}

            # extract task title
            title_match = re.search(
                r'### Task Title\s*\n(.+?)(?:\n###|\n\n|$)', content, re.DOTALL
            )
            if title_match:
                metadata['title'] = title_match.group(1).strip()
            else:
                metadata['title'] = ""

            # extract task description
            desc_match = re.search(
                r'### Task Description\s*\n(.+?)(?:\n###|\n\n|$)',
                content,
                re.DOTALL,
            )
            if desc_match:
                metadata['description'] = desc_match.group(1).strip()
            else:
                metadata['description'] = ""

            # extract tags
            tags_match = re.search(
                r'### Tags\s*\n(.+?)(?:\n###|\n\n|$)', content, re.DOTALL
            )
            if tags_match:
                tags_section = tags_match.group(1).strip()
                # Parse bullet list of tags
                tags = [
                    line.strip().lstrip('- ')
                    for line in tags_section.split('\n')
                    if line.strip().startswith('-')
                ]
                metadata['tags'] = tags
            else:
                metadata['tags'] = []

            return metadata

        except Exception as e:
            logger.warning(
                f"Error extracting workflow info from {file_path}: {e}"
            )
            return {}

    def get_all_workflows_info(
        self, session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        r"""Get info from all workflow files in workforce_workflows.

        This method scans the workforce_workflows directory for workflow
        markdown files and extracts their info for use in workflow
        selection.

        Args:
            session_id (Optional[str]): If provided, only return workflows
                from this specific session. If None, returns workflows from
                all sessions.

        Returns:
            List[Dict[str, Any]]: List of workflow info dicts, sorted
                by session timestamp (newest first).
        """
        import glob
        import re

        workflows_metadata = []

        # Determine base directory for workforce workflows
        camel_workdir = os.environ.get("CAMEL_WORKDIR")
        if camel_workdir:
            base_dir = os.path.join(camel_workdir, "workforce_workflows")
        else:
            base_dir = "workforce_workflows"

        # Build search pattern
        if session_id:
            search_pattern = os.path.join(
                base_dir, session_id, "*_workflow.md"
            )
        else:
            search_pattern = os.path.join(base_dir, "*", "*_workflow.md")

        # Find all workflow files
        workflow_files = glob.glob(search_pattern)

        if not workflow_files:
            logger.info(f"No workflow files found in {base_dir}")
            return []

        # Sort by session timestamp (newest first)
        def extract_session_timestamp(filepath: str) -> str:
            match = re.search(r'session_(\d{8}_\d{6}_\d{6})', filepath)
            return match.group(1) if match else ""

        workflow_files.sort(key=extract_session_timestamp, reverse=True)

        # Extract info from each file
        for file_path in workflow_files:
            metadata = self.extract_workflow_info(file_path)
            if metadata:  # Only add if extraction succeeded
                workflows_metadata.append(metadata)

        logger.info(
            f"Found {len(workflows_metadata)} workflow file(s) with info"
        )
        return workflows_metadata

    # ========= SHARED SESSION MANAGEMENT METHODS =========

    @classmethod
    def get_workforce_shared(
        cls, session_id: Optional[str] = None
    ) -> 'ContextUtility':
        r"""Get or create shared workforce context utility with lazy init.

        This method provides a centralized way to access shared context
        utilities for workforce workflows, ensuring all workforce components
        use the same session directory.

        Args:
            session_id (str, optional): Custom session ID. If None, uses the
                default workforce session.

        Returns:
            ContextUtility: Shared context utility instance for workforce.
        """
        if session_id is None:
            # Use default workforce session
            if cls._default_workforce_session is None:
                camel_workdir = os.environ.get("CAMEL_WORKDIR")
                if camel_workdir:
                    base_path = os.path.join(
                        camel_workdir, "workforce_workflows"
                    )
                else:
                    base_path = "workforce_workflows"

                cls._default_workforce_session = cls(
                    working_directory=base_path,
                    create_folder=False,  # Don't create folder until needed
                )
            return cls._default_workforce_session

        # Use specific session
        if session_id not in cls._shared_sessions:
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                base_path = os.path.join(camel_workdir, "workforce_workflows")
            else:
                base_path = "workforce_workflows"

            cls._shared_sessions[session_id] = cls(
                working_directory=base_path,
                session_id=session_id,
                create_folder=False,  # Don't create folder until needed
            )
        return cls._shared_sessions[session_id]

    @classmethod
    def reset_shared_sessions(cls) -> None:
        r"""Reset shared sessions (useful for testing).

        This method clears all shared session instances, forcing new ones
        to be created on next access. Primarily used for testing to ensure
        clean state between tests.
        """
        cls._shared_sessions.clear()
        cls._default_workforce_session = None
