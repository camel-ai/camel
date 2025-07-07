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
from typing import List, Optional

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool


class NoteTakingToolkit(BaseToolkit):
    r"""A toolkit for taking notes in a Markdown file.

    This toolkit allows an agent to create, append to, and update a specific
    Markdown file for note-taking purposes.
    """

    def __init__(
        self,
        note_file_path: str = "notes/notes.md",
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the NoteTakingToolkit.

        Args:
            note_file_path (str): The path to the note file.
                (default: :obj:`notes/notes.md`)
            timeout (Optional[float]): The timeout for the toolkit.
        """
        super().__init__(timeout=timeout)
        self.note_file_path = Path(note_file_path)
        self.note_file_path.parent.mkdir(parents=True, exist_ok=True)

    def append_note(self, content: str) -> str:
        r"""Appends a note to the note file.

        Args:
            content (str): The content of the note to be appended.

        Returns:
            str: A message indicating the result of the operation.
        """
        try:
            with self.note_file_path.open("a", encoding="utf-8") as f:
                f.write(content + "\n")
            return f"Note successfully appended to in {self.note_file_path}."
        except Exception as e:
            return f"Error appending note: {e}"

    def read_note(self) -> str:
        r"""Reads the content of the note file.

        Returns:
            str: The content of the note file, or an error message if the
                 file cannot be read.
        """
        try:
            if not self.note_file_path.exists():
                return "Note file does not exist yet."
            return self.note_file_path.read_text(encoding="utf-8")
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
        ]
