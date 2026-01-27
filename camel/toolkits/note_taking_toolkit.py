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
from pathlib import Path

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import retry_on_error


class FileNotReadyError(Exception):
    r"""Raised when a file is not ready to be read."""

    pass


class InvalidNoteNameError(ValueError):
    r"""Raised when a note name is invalid."""

    pass


class NoteTakingToolkit(BaseToolkit):
    r"""A toolkit for managing and interacting with markdown note files.

    This toolkit provides tools for creating, reading, appending to, and
    listing notes. All notes are stored as `.md` files in a dedicated working
    directory and are tracked in a registry.
    """

    _REGISTRY_FILENAME = ".note_register"
    _NOTE_EXT = ".md"
    _MAX_NOTE_NAME_LENGTH = 255

    # Invalid characters for filenames across different operating systems:
    # < > : " / \ | ? * - Reserved characters on Windows
    # \x00 (NUL) - Invalid on all systems (Unix, Windows, macOS)
    # TODO: ensure these to all file name created by llm from other tools
    _INVALID_CHARS = '<>:"/\\|?*\x00'

    def __init__(
        self,
        working_directory: str | None = None,
        timeout: float | None = None,
    ) -> None:
        r"""Initialize the NoteTakingToolkit.

        Args:
            working_directory (str, optional): The directory path where notes
                will be stored. If not provided, it will be determined by the
                :obj:`CAMEL_WORKDIR` environment variable (if set). If the
                environment variable is not set, it defaults to
                :obj:`camel_working_dir`.
            timeout (float, optional): The timeout for the toolkit.
        """
        super().__init__(timeout=timeout)
        camel_workdir = os.environ.get("CAMEL_WORKDIR")
        if working_directory:
            path = Path(working_directory)
        elif camel_workdir:
            path = Path(camel_workdir)
        else:
            path = Path("camel_working_dir")

        self.working_directory = path
        self.working_directory.mkdir(parents=True, exist_ok=True)
        self.registry_file = self.working_directory / self._REGISTRY_FILENAME
        self._load_registry()

    def _get_note_path(self, note_name: str) -> Path:
        r"""Get the file path for a note.

        Args:
            note_name (str): The name of the note (without extension).

        Returns:
            Path: The full path to the note file.
        """
        return self.working_directory / f"{note_name}{self._NOTE_EXT}"

    def _format_note_content(self, note_name: str, content: str) -> str:
        r"""Format a note with header and content for display.

        Args:
            note_name (str): The name of the note file.
            content (str): The content of the note.

        Returns:
            str: Formatted note like "=== note_name ===\ncontent".
        """
        return f"=== {note_name} ===\n{content}"

    def _validate_note_name(self, note_name: str) -> str | None:
        r"""Validate a note name for filesystem safety.

        Args:
            note_name (str): The note name to validate.

        Returns:
            str | None: An error message if validation fails, None if valid.
        """
        if not note_name or not note_name.strip():
            return "Note name cannot be empty or whitespace only."

        if len(note_name) > self._MAX_NOTE_NAME_LENGTH:
            return (
                f"Note name exceeds maximum length of "
                f"{self._MAX_NOTE_NAME_LENGTH} characters."
            )

        # Check for invalid characters
        for char in self._INVALID_CHARS:
            if char in note_name:
                return (
                    f"Note name contains invalid character: "
                    f"'{char}' (not allowed in filenames)."
                )

        # Check for path traversal attempts
        if '..' in note_name or note_name.startswith('/'):
            return "Note name cannot contain path traversal sequences."

        # Check for reserved names on Windows
        reserved_names = {
            'CON',
            'PRN',
            'AUX',
            'NUL',
            'COM1',
            'COM2',
            'COM3',
            'COM4',
            'COM5',
            'COM6',
            'COM7',
            'COM8',
            'COM9',
            'LPT1',
            'LPT2',
            'LPT3',
            'LPT4',
            'LPT5',
            'LPT6',
            'LPT7',
            'LPT8',
            'LPT9',
        }
        if note_name.upper() in reserved_names:
            return f"Note name '{note_name}' is a reserved system name."

        # Check for names that are only dots or spaces
        if note_name.strip('.') == '' or note_name.strip() == '':
            return "Note name cannot consist only of dots or spaces."

        return None

    def append_note(self, note_name: str, content: str) -> str:
        r"""Appends content to a note.

        If the note does not exist, it will be created with the given content.
        If the note already exists, the new content will be added to the end of
        the note specified by the :obj:`note_name`.

        Args:
            note_name (str): The name of the note (without the .md extension).
                Should consist of letters, numbers, underscores, hyphens, or
                spaces (e.g., "meeting_notes", "project-ideas").
            content (str): The content to append to the note.

        Returns:
            str: A message confirming that the content was appended or the note
                 was created.
        """
        try:
            validation_error = self._validate_note_name(note_name)
            if validation_error:
                return f"Error: {validation_error}"

            # Reload registry to get latest state
            self._load_registry()
            note_path = self._get_note_path(note_name)
            if note_name not in self.registry or not note_path.exists():
                self.create_note(note_name, content)
                return (
                    f"Note '{note_name}' is created "
                    f"with the specified content."
                )

            with note_path.open("a", encoding="utf-8") as f:
                f.write(content + "\n")
            return (
                f"Content successfully appended to existing "
                f"note '{note_path.name}'."
            )
        except Exception as e:
            return f"Error appending note: {e}"

    def _load_registry(self) -> None:
        r"""Load the note registry from file."""
        self.registry = self._load_registry_content()

    @retry_on_error(
        max_retries=5,
        initial_delay=0.1,
        backoff="linear",
        retry_on=(IOError, OSError, FileNotReadyError),
        fallback=[],
    )
    def _load_registry_content(self) -> list[str]:
        r"""Load the note registry content from file with retry logic."""
        if not self.registry_file.exists():
            raise FileNotReadyError("Registry file not yet available")
        content = self.registry_file.read_text(encoding='utf-8').strip()
        return content.split('\n') if content else []

    @retry_on_error(
        max_retries=5,
        initial_delay=0.1,
        backoff="linear",
        retry_on=(IOError, OSError),
    )
    def _save_registry(self) -> None:
        r"""Save the note registry to file using atomic write."""
        # Use atomic write with temporary file for all platforms
        temp_file = self.registry_file.with_suffix('.tmp')
        temp_file.write_text('\n'.join(self.registry), encoding='utf-8')

        # Atomic rename - works on all platforms
        temp_file.replace(self.registry_file)

    def _register_note(self, note_name: str) -> None:
        r"""Register a new note in the registry with thread-safe operations."""
        # Reload registry to get latest state
        self._load_registry()
        if note_name not in self.registry:
            self.registry.append(note_name)
            self._save_registry()

    def create_note(
        self,
        note_name: str,
        content: str,
        overwrite: bool = False,
    ) -> str:
        r"""Creates a new note with a unique note name, which will
        create a new file for your note. You must provide a :obj:`note_name`
        that does not already exist. If you want to add content to an
        existing note, use the :func:`append_note` function instead.

        Args:
            note_name (str): The name for your new note (without the .md
                extension). This name must be unique unless overwrite is True.
                Should consist of letters, numbers, underscores, hyphens, or
                spaces (e.g., "meeting_notes", "project-ideas").
            content (str): The initial content to write in the note.
            overwrite (bool): Whether to overwrite an existing note.
                Defaults to False.

        Returns:
            str: A message confirming the creation of the note or an error if
                the note name is not valid or already exists
                (when overwrite=False).
        """
        try:
            validation_error = self._validate_note_name(note_name)
            if validation_error:
                return f"Error: {validation_error}"

            note_path = self._get_note_path(note_name)
            existed_before = note_path.exists()

            if existed_before and not overwrite:
                return f"Error: Note '{note_path.name}' already exists."

            note_path.write_text(content, encoding="utf-8")
            self._register_note(note_name)

            if existed_before and overwrite:
                return f"Note '{note_path.name}' successfully overwritten."
            else:
                return f"Note '{note_path.name}' successfully created."
        except Exception as e:
            return f"Error creating note: {e}"

    def list_note(self) -> str:
        r"""Lists all the notes you have created.

        This function will show you a list of all your notes, along with their
        sizes in bytes. This is useful for seeing what notes you have available
        to read or append to.

        Returns:
            str: A string containing a list of available notes and their sizes,
                or a message indicating that no notes have been created yet.
        """
        try:
            # Reload registry to get latest state
            self._load_registry()
            if not self.registry:
                return "No notes have been created yet."

            notes_info = []
            for note_name in self.registry:
                note_path = self._get_note_path(note_name)
                if note_path.exists():
                    size = note_path.stat().st_size
                    notes_info.append(f"- {note_path.name} ({size} bytes)")
                else:
                    notes_info.append(f"- {note_path.name} (file missing)")

            return "Available notes:\n" + "\n".join(notes_info)
        except Exception as e:
            return f"Error listing notes: {e}"

    def read_note(self, note_name: str = "all_notes") -> str:
        r"""Reads the content of a specific note or all notes.

        You can use this function in two ways:
        1.  **Read a specific note:** Provide the `note_name` (without the .md
            extension) to get the content of that single note.
        2.  **Read all notes:** Use `note_name="all_notes"` (default), and this
            function will return the content of all your notes, concatenated
            together.

        Args:
            note_name (str): The name of the note you want to read.
                Defaults to "all_notes" which reads all notes.

        Returns:
            str: The content of the specified note(s), or an error message if
                a note cannot be read.
        """
        try:
            # Reload registry to get latest state
            self._load_registry()
            if note_name != "all_notes":
                if note_name not in self.registry:
                    return (
                        f"Error: Note '{note_name}' is not registered "
                        f"or was not created by this toolkit."
                    )
                note_path = self._get_note_path(note_name)
                if not note_path.exists():
                    return f"Note file '{note_path.name}' does not exist."
                return note_path.read_text(encoding="utf-8")
            else:
                if not self.registry:
                    return "No notes have been created yet."

                all_notes = []
                for registered_note in self.registry:
                    note_path = self._get_note_path(registered_note)
                    if note_path.exists():
                        content = note_path.read_text(encoding="utf-8")
                    else:
                        content = "[File not found]"
                    all_notes.append(
                        self._format_note_content(note_path.name, content)
                    )

                return "\n\n".join(all_notes)
        except Exception as e:
            return f"Error reading note: {e}"

    def get_tools(self) -> list[FunctionTool]:
        r"""Return a list of :obj:`FunctionTool` objects representing the
        functions in the toolkit.

        Returns:
            List of FunctionTool: A list of :obj:`FunctionTool` objects.
        """
        return [
            FunctionTool(self.append_note),
            FunctionTool(self.read_note),
            FunctionTool(self.create_note),
            FunctionTool(self.list_note),
        ]
