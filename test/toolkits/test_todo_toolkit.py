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

import pytest

from camel.toolkits import TodoToolkit
from camel.toolkits.todo_toolkit import TodoItem


@pytest.fixture
def todo_toolkit(tmp_path):
    r"""Create a TodoToolkit instance backed by a temp directory."""
    return TodoToolkit(working_dir=str(tmp_path))


def test_todo_write_with_raw_dicts(todo_toolkit):
    r"""Test updating the todo list with raw dicts."""
    todos = [
        {
            "content": "Install pptxgenjs dependencies",
            "active_form": "Installing pptxgenjs dependencies",
            "status": "completed",
        },
        {
            "content": "Wire TodoWrite into toolkit exports",
            "active_form": "Wiring TodoWrite into toolkit exports",
            "status": "in_progress",
        },
    ]

    result = todo_toolkit.todo_write(todos)

    assert result == "Todos have been modified successfully."
    assert len(todo_toolkit.todos) == 2
    for stored, raw in zip(todo_toolkit.todos, todos):
        assert isinstance(stored, TodoItem)
        assert stored.model_dump() == raw


def test_todo_write_with_todoitem_instances(todo_toolkit):
    r"""Test updating the todo list with TodoItem instances."""
    items = [
        TodoItem(
            content="First task",
            active_form="Working on first task",
            status="pending",
        ),
        TodoItem(
            content="Second task",
            active_form="Working on second task",
            status="completed",
        ),
    ]

    result = todo_toolkit.todo_write(items)

    assert result == "Todos have been modified successfully."
    assert len(todo_toolkit.todos) == 2
    assert todo_toolkit.todos[0] is items[0]
    assert todo_toolkit.todos[1] is items[1]


def test_todo_write_empty_list_clears_todos(todo_toolkit):
    r"""Test that writing an empty list clears existing todos."""
    todo_toolkit.todo_write(
        [
            {
                "content": "Some task",
                "active_form": "Doing some task",
                "status": "pending",
            }
        ]
    )
    assert len(todo_toolkit.todos) == 1

    result = todo_toolkit.todo_write([])

    assert result == "Todos have been modified successfully."
    assert todo_toolkit.todos == []


def test_todo_write_keeps_previous_state_on_validation_error(todo_toolkit):
    r"""Test that invalid todo payloads do not overwrite prior state."""
    existing = [
        {
            "content": "Keep previous widget state",
            "active_form": "Keeping previous widget state",
            "status": "pending",
        }
    ]
    todo_toolkit.todo_write(existing)

    result = todo_toolkit.todo_write(
        [
            {
                "content": "Use an unsupported status",
                "active_form": "Using an unsupported status",
                "status": "done",
            }
        ]
    )

    assert result.startswith("[ERROR] Failed to update todos:")
    assert len(todo_toolkit.todos) == 1
    assert todo_toolkit.todos[0].content == "Keep previous widget state"


def test_persistence_creates_files(tmp_path):
    r"""Test that todo_write creates both todo.md and .todo.json."""
    tk = TodoToolkit(working_dir=str(tmp_path))
    tk.todo_write(
        [
            {
                "content": "Persisted task",
                "active_form": "Persisting task",
                "status": "pending",
            }
        ]
    )

    # Markdown — clean, human-readable, no metadata
    md_file = tmp_path / "todo.md"
    assert md_file.exists()
    md_content = md_file.read_text(encoding="utf-8")
    assert "# Todo" in md_content
    assert "Persisted task" in md_content
    assert "<!--" not in md_content
    assert "active_form" not in md_content

    # JSON — structured data for reloading
    json_file = tmp_path / ".todo.json"
    assert json_file.exists()


def test_persistence_survives_reload(tmp_path):
    r"""Test that a new TodoToolkit instance loads from existing .todo.json."""
    tk1 = TodoToolkit(working_dir=str(tmp_path))
    tk1.todo_write(
        [
            {
                "content": "Task A",
                "active_form": "Working on A",
                "status": "completed",
            },
            {
                "content": "Task B",
                "active_form": "Working on B",
                "status": "in_progress",
            },
            {
                "content": "Task C",
                "active_form": "Working on C",
                "status": "pending",
            },
        ]
    )

    # Create a new instance pointing to the same directory
    tk2 = TodoToolkit(working_dir=str(tmp_path))

    assert len(tk2.todos) == 3
    for original, reloaded in zip(tk1.todos, tk2.todos):
        assert reloaded.model_dump() == original.model_dump()


def _resolve_ref(schema, root):
    r"""Resolve a ``$ref`` pointer against *root*."""
    ref = schema.get("$ref")
    if ref is None:
        return schema
    parts = ref.lstrip("#/").split("/")
    node = root
    for part in parts:
        node = node[part]
    return node


def test_get_tools_exposes_todo_write_schema(todo_toolkit):
    r"""Test todo_write tool registration and schema generation."""
    tools = todo_toolkit.get_tools()

    assert len(tools) == 1
    assert tools[0].get_function_name() == "todo_write"

    schema = tools[0].get_openai_tool_schema()
    parameters = schema["function"]["parameters"]
    todos_schema = parameters["properties"]["todos"]
    # Pydantic may emit $ref + $defs; resolve if necessary.
    item_schema = _resolve_ref(todos_schema["items"], parameters)
    status_schema = item_schema["properties"]["status"]

    assert parameters["required"] == ["todos"]
    assert parameters["additionalProperties"] is False
    assert todos_schema["type"] == "array"
    assert set(item_schema["properties"]) == {
        "content",
        "active_form",
        "status",
    }
    assert item_schema["additionalProperties"] is False
    assert status_schema["enum"] == ["pending", "in_progress", "completed"]
