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
import shutil
from pathlib import Path

import pytest

from camel.toolkits import NoteTakingToolkit


@pytest.fixture
def note_taking_toolkit():
    # Create a toolkit with a temporary directory
    test_dir = Path("test_notes_dir")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    toolkit = NoteTakingToolkit(working_directory=str(test_dir))
    yield toolkit
    # Cleanup after tests
    if test_dir.exists():
        shutil.rmtree(test_dir)


def test_create_note(note_taking_toolkit):
    # Test creating a new note
    result = note_taking_toolkit.create_note("test_note", "Initial content")
    assert "successfully created" in result

    # Test creating a note that already exists
    result = note_taking_toolkit.create_note("test_note", "Another content")
    assert "already exists" in result

    # Test creating a note with empty content
    result = note_taking_toolkit.create_note("empty_note", "")
    assert "successfully created" in result


def test_append_note(note_taking_toolkit):
    # Test appending to a non-existent note (should create it)
    result = note_taking_toolkit.append_note("new_note", "First line")
    assert "created with content added" in result

    # Test appending to an existing note
    result = note_taking_toolkit.append_note("new_note", "Second line")
    assert "successfully appended" in result

    # Read and verify content
    content = note_taking_toolkit.read_note("new_note")
    assert "First line" in content
    assert "Second line" in content


def test_list_note(note_taking_toolkit):
    # Test listing when no notes exist
    result = note_taking_toolkit.list_note()
    assert "No notes have been created yet" in result

    # Create some notes
    note_taking_toolkit.create_note("note1", "Content 1")
    note_taking_toolkit.create_note("note2", "Content 2")

    # Test listing notes
    result = note_taking_toolkit.list_note()
    assert "Available notes:" in result
    assert "note1.md" in result
    assert "note2.md" in result
    assert "bytes" in result


def test_read_note(note_taking_toolkit):
    # Test reading non-existent registry
    result = note_taking_toolkit.read_note()
    assert "No notes have been created yet" in result

    # Create notes
    note_taking_toolkit.create_note("note1", "Content of note 1")
    note_taking_toolkit.create_note("note2", "Content of note 2")

    # Test reading a specific note
    result = note_taking_toolkit.read_note("note1")
    assert result == "Content of note 1"

    # Test reading a non-registered note
    result = note_taking_toolkit.read_note("non_existent")
    assert "not registered" in result

    # Test reading all notes
    result = note_taking_toolkit.read_note()
    assert "=== note1.md ===" in result
    assert "Content of note 1" in result
    assert "=== note2.md ===" in result
    assert "Content of note 2" in result


def test_registry_persistence(note_taking_toolkit):
    # Create a note
    note_taking_toolkit.create_note("persistent_note", "Test content")

    # Create a new toolkit instance with the same directory
    toolkit2 = NoteTakingToolkit(
        working_directory=str(note_taking_toolkit.working_directory)
    )

    # Verify the note is still in the registry
    result = toolkit2.read_note("persistent_note")
    assert result == "Test content"

    # Verify listing shows the note
    result = toolkit2.list_note()
    assert "persistent_note.md" in result


def test_registry_security(note_taking_toolkit):
    # Manually create a file that's not in the registry
    test_dir = note_taking_toolkit.working_directory
    unauthorized_file = test_dir / "unauthorized.md"
    unauthorized_file.write_text("Unauthorized content")

    # Try to read the unauthorized file
    result = note_taking_toolkit.read_note("unauthorized")
    assert "not registered" in result

    # Verify it doesn't appear in list
    result = note_taking_toolkit.list_note()
    assert "unauthorized.md" not in result

    # Clean up
    unauthorized_file.unlink()


def test_get_tools(note_taking_toolkit):
    tools = note_taking_toolkit.get_tools()
    assert len(tools) == 4
    tool_names = [tool.func.__name__ for tool in tools]
    assert "append_note" in tool_names
    assert "read_note" in tool_names
    assert "create_note" in tool_names
    assert "list_note" in tool_names
