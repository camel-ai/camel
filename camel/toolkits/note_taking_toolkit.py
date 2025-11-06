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
import time
from pathlib import Path
from typing import List, Optional

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool


class NoteTakingToolkit(BaseToolkit):
    r"""A toolkit for managing and interacting with markdown note files.

    This toolkit provides tools for creating, reading, appending to, and
    listing notes. All notes are stored as `.md` files in a dedicated working
    directory and are tracked in a registry.
    """

    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the NoteTakingToolkit.

        Args:
            working_directory (str, optional): The directory path where notes
                will be stored. If not provided, it will be determined by the
                `CAMEL_WORKDIR` environment variable (if set). If the
                environment variable is not set, it defaults to
                `camel_working_dir`.
            timeout (Optional[float]): The timeout for the toolkit.
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
        self.registry_file = self.working_directory / ".note_register"
        self._load_registry()

    def append_note(self, note_name: str, content: str) -> str:
        r"""Appends content to a note.

        If the note does not exist, it will be created with the given content.
        If the note already exists, the new content will be added to the end of
        the note.

        Args:
            note_name (str): The name of the note (without the .md extension).
            content (str): The content to append to the note.

        Returns:
            str: A message confirming that the content was appended or the note
                 was created.
        """
        try:
            # Reload registry to get latest state
            self._load_registry()
            note_path = self.working_directory / f"{note_name}.md"
            if note_name not in self.registry or not note_path.exists():
                self.create_note(note_name, content)
                return f"Note '{note_name}' created with content added."

            with note_path.open("a", encoding="utf-8") as f:
                f.write(content + "\n")
            return f"Content successfully appended to '{note_name}.md'."
        except Exception as e:
            return f"Error appending note: {e}"

    def _load_registry(self) -> None:
        r"""Load the note registry from file."""
        max_retries = 5
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                if self.registry_file.exists():
                    content = self.registry_file.read_text(
                        encoding='utf-8'
                    ).strip()
                    self.registry = content.split('\n') if content else []
                else:
                    self.registry = []
                return
            except (IOError, OSError):
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    # If all retries failed, initialize with empty registry
                    self.registry = []

    def _save_registry(self) -> None:
        r"""Save the note registry to file using atomic write."""
        max_retries = 5
        retry_delay = 0.1

        for attempt in range(max_retries):
            try:
                # Use atomic write with temporary file for all platforms
                temp_file = self.registry_file.with_suffix('.tmp')
                temp_file.write_text(
                    '\n'.join(self.registry), encoding='utf-8'
                )

                # Atomic rename - works on all platforms
                temp_file.replace(self.registry_file)
                return
            except (IOError, OSError):
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    raise

    def _register_note(self, note_name: str) -> None:
        r"""Register a new note in the registry with thread-safe operations."""
        # Reload registry to get latest state
        self._load_registry()
        if note_name not in self.registry:
            self.registry.append(note_name)
            self._save_registry()

    def create_note(
        self, note_name: str, content: str, overwrite: bool = False
    ) -> str:
        r"""Creates a new note with a unique name.

        This function will create a new file for your note.
        By default, you must provide a `note_name` that does not already exist.
        If you want to add content to an existing note, use the `append_note`
        function instead. If you want to overwrite an existing note, set
        `overwrite=True`.

        Args:
            note_name (str): The name for your new note (without the .md
                extension). This name must be unique unless overwrite is True.
            content (str): The initial content to write in the note.
            overwrite (bool): Whether to overwrite an existing note.
                Defaults to False.

        Returns:
            str: A message confirming the creation of the note or an error if
                the note name is not valid or already exists
                (when overwrite=False).
        """
        try:
            note_path = self.working_directory / f"{note_name}.md"
            existed_before = note_path.exists()

            if existed_before and not overwrite:
                return f"Error: Note '{note_name}.md' already exists."

            note_path.write_text(content, encoding="utf-8")
            self._register_note(note_name)

            if existed_before and overwrite:
                return f"Note '{note_name}.md' successfully overwritten."
            else:
                return f"Note '{note_name}.md' successfully created."
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
                note_path = self.working_directory / f"{note_name}.md"
                if note_path.exists():
                    size = note_path.stat().st_size
                    notes_info.append(f"- {note_name}.md ({size} bytes)")
                else:
                    notes_info.append(f"- {note_name}.md (file missing)")

            return "Available notes:\n" + "\n".join(notes_info)
        except Exception as e:
            return f"Error listing notes: {e}"

    def read_note(self, note_name: Optional[str] = "all_notes") -> str:
        r"""Reads the content of a specific note or all notes.

        You can use this function in two ways:
        1.  **Read a specific note:** Provide the `note_name` (without the .md
            extension) to get the content of that single note.
        2.  **Read all notes:** Use `note_name="all_notes"` (default), and this
            function will return the content of all your notes, concatenated
            together.

        Args:
            note_name (str, optional): The name of the note you want to read.
                Defaults to "all_notes" which reads all notes.

        Returns:
            str: The content of the specified note(s), or an error message if
                a note cannot be read.
        """
        try:
            # Reload registry to get latest state
            self._load_registry()
            if note_name and note_name != "all_notes":
                if note_name not in self.registry:
                    return (
                        f"Error: Note '{note_name}' is not registered "
                        f"or was not created by this toolkit."
                    )
                note_path = self.working_directory / f"{note_name}.md"
                if not note_path.exists():
                    return f"Note file '{note_path.name}' does not exist."
                return note_path.read_text(encoding="utf-8")
            else:
                if not self.registry:
                    return "No notes have been created yet."

                all_notes = []
                for registered_note in self.registry:
                    note_path = (
                        self.working_directory / f"{registered_note}.md"
                    )
                    if note_path.exists():
                        content = note_path.read_text(encoding="utf-8")
                        all_notes.append(
                            f"=== {registered_note}.md ===\n{content}"
                        )
                    else:
                        all_notes.append(
                            f"=== {registered_note}.md ===\n[File not found]"
                        )

                return "\n\n".join(all_notes)
        except Exception as e:
            return f"Error reading note: {e}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Return a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects.
        """
        return [
            FunctionTool(self.append_note),
            FunctionTool(self.read_note),
            FunctionTool(self.create_note),
            FunctionTool(self.list_note),
        ]
