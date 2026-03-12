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

import json
import threading
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, ValidationError

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer

logger = get_logger(__name__)

_STATUS_EMOJI = {
    "pending": "⬜",
    "in_progress": "🔄",
    "completed": "✅",
}


class TodoItem(BaseModel):
    r"""Schema for a single todo item.

    Attributes:
        content: A brief, actionable title for the task.
        active_form: Present-continuous label shown in a UI spinner while
            the task is in progress.
        status: Current status of the task.
    """

    content: str
    active_form: str
    status: Literal["pending", "in_progress", "completed"]


@MCPServer()
class TodoToolkit(BaseToolkit):
    r"""A toolkit for managing a todo list persisted to local files.

    The toolkit exposes a single :obj:`todo_write` tool that lets an agent
    replace the current todo list with a new set of items. Each item carries
    a short content string, an active-form label for UI spinners, and a
    status drawn from ``pending``, ``in_progress``, or ``completed``.

    Two files are maintained inside *working_dir*:

    - ``todo.md``  — a clean, human-readable Markdown checklist.
    - ``.todo.json`` — structured data used to reload state across sessions.

    A thread lock prevents concurrent write conflicts within the same
    process.

    Args:
        working_dir (Optional[str]): Directory where files are stored.
            Defaults to the current working directory.
        timeout (Optional[float]): The timeout for the toolkit.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)
        self._working_dir = Path(working_dir) if working_dir else Path.cwd()
        self._md_path = self._working_dir / "todo.md"
        self._json_path = self._working_dir / ".todo.json"
        self._lock = threading.Lock()
        with self._lock:
            self.todos: List[TodoItem] = self._load()

    # ── persistence helpers ──────────────────────────────────────────

    def _load(self) -> List[TodoItem]:
        r"""Load todos from the JSON data file, if it exists."""
        if not self._json_path.exists():
            return []
        try:
            data = json.loads(self._json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "Failed to read %s, starting with empty list: %s",
                self._json_path,
                exc,
            )
            return []
        if not isinstance(data, list):
            logger.warning(
                "Expected a JSON array in %s, got %s; starting with empty "
                "list.",
                self._json_path,
                type(data).__name__,
            )
            return []
        items: List[TodoItem] = []
        for entry in data:
            try:
                items.append(TodoItem.model_validate(entry))
            except ValidationError as exc:
                logger.warning(
                    "Skipping malformed todo entry in %s: %s",
                    self._json_path,
                    exc,
                )
        return items

    def _save(self) -> None:
        r"""Write todos to both the JSON data file and the Markdown file."""
        self._working_dir.mkdir(parents=True, exist_ok=True)
        # JSON — source of truth for reloading
        self._json_path.write_text(
            json.dumps(
                [item.model_dump() for item in self.todos],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        # Markdown — clean, human-readable view
        lines = ["# Todo", ""]
        for item in self.todos:
            emoji = _STATUS_EMOJI.get(item.status, "⬜")
            lines.append(f"- {emoji} {item.content}")
        self._md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── tool methods ─────────────────────────────────────────────────

    def todo_write(
        self,
        todos: List[TodoItem],
    ) -> str:
        r"""Replace the current todo list with a new set of items.

        Args:
            todos (List[TodoItem]): The new todo list that will replace
                the current one.

        Returns:
            str: A success message, or an error string prefixed with
                ``[ERROR]`` if validation fails.
        """
        # Validate & normalise: accept both TodoItem instances (from
        # FunctionTool coercion) and raw dicts (from direct calls).
        validated: List[TodoItem] = []
        try:
            for item in todos:
                if isinstance(item, TodoItem):
                    validated.append(item)
                else:
                    validated.append(TodoItem.model_validate(item))
        except ValidationError as exc:
            return f"[ERROR] Failed to update todos: {exc}"

        with self._lock:
            self.todos = validated
            self._save()
        return "Todos have been modified successfully."

    def get_tools(self) -> List[FunctionTool]:
        r"""Get all tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of tools.
        """
        return [
            FunctionTool(self.todo_write),
        ]
