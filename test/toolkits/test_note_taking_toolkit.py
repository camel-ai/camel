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
from pathlib import Path
from unittest.mock import patch

import pytest

from camel.toolkits import NoteTakingToolkit
from camel.toolkits.note_taking_toolkit import (
    FileNotReadyError,
    InvalidNoteNameError,
)


@pytest.fixture
def note_taking_toolkit(tmp_path):
    """Create a toolkit with a temporary directory (auto-cleaned by pytest)."""
    toolkit = NoteTakingToolkit(working_directory=str(tmp_path))
    return toolkit


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
    assert "created" in result and "specified content" in result

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


def test_get_tools(note_taking_toolkit):
    tools = note_taking_toolkit.get_tools()
    assert len(tools) == 4
    tool_names = [tool.func.__name__ for tool in tools]
    assert "append_note" in tool_names
    assert "read_note" in tool_names
    assert "create_note" in tool_names
    assert "list_note" in tool_names


def test_load_registry_retry_on_io_error(note_taking_toolkit):
    """Test that _load_registry_content retries on IOError and falls back."""
    # Create a note first so registry file exists
    note_taking_toolkit.create_note("test_note", "content")

    call_count = 0

    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        nonlocal call_count
        if ".note_register" in str(self):
            call_count += 1
            if call_count < 3:
                raise IOError("Simulated IO error")
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, 'read_text', mock_read_text):
        note_taking_toolkit._load_registry()

    # Should have retried and succeeded on 3rd attempt
    assert call_count == 3
    assert "test_note" in note_taking_toolkit.registry


def test_load_registry_fallback_after_max_retries(note_taking_toolkit):
    """Test that _load_registry_content returns fallback after max retries."""
    # Create a note first so registry file exists
    note_taking_toolkit.create_note("test_note", "content")

    original_read_text = Path.read_text

    def mock_read_text(self, *args, **kwargs):
        if ".note_register" in str(self):
            raise IOError("Persistent IO error")
        return original_read_text(self, *args, **kwargs)

    with patch.object(Path, 'read_text', mock_read_text):
        note_taking_toolkit._load_registry()

    # Should fall back to empty list after all retries exhausted
    assert note_taking_toolkit.registry == []


def test_load_registry_file_not_ready_retry(note_taking_toolkit):
    """Test that _load_registry_content retries when file doesn't exist."""
    call_count = 0

    original_exists = Path.exists

    def mock_exists(self):
        nonlocal call_count
        if ".note_register" in str(self):
            call_count += 1
            if call_count < 3:
                return False
            return True
        return original_exists(self)

    # Pre-create the registry file
    note_taking_toolkit.registry_file.write_text("existing_note")

    with patch.object(Path, 'exists', mock_exists):
        note_taking_toolkit._load_registry()

    # Should have retried and succeeded when file "appeared"
    assert call_count == 3
    assert "existing_note" in note_taking_toolkit.registry


def test_save_registry_retry_on_os_error(note_taking_toolkit):
    """Test that _save_registry retries on OSError."""
    note_taking_toolkit.registry = ["note1", "note2"]

    call_count = 0
    original_write_text = Path.write_text

    def mock_write_text(self, content, *args, **kwargs):
        nonlocal call_count
        if ".tmp" in str(self):
            call_count += 1
            if call_count < 3:
                raise OSError("Simulated OS error")
        return original_write_text(self, content, *args, **kwargs)

    with patch.object(Path, 'write_text', mock_write_text):
        note_taking_toolkit._save_registry()

    # Should have retried and succeeded
    assert call_count == 3
    # Verify the registry was saved
    content = note_taking_toolkit.registry_file.read_text()
    assert "note1" in content
    assert "note2" in content


def test_save_registry_raises_after_max_retries(note_taking_toolkit):
    """Test that _save_registry raises after max retries (no fallback)."""
    note_taking_toolkit.registry = ["note1"]

    def mock_write_text(self, content, *args, **kwargs):
        if ".tmp" in str(self):
            raise OSError("Persistent OS error")

    with patch.object(Path, 'write_text', mock_write_text):
        with pytest.raises(OSError, match="Persistent OS error"):
            note_taking_toolkit._save_registry()


def test_file_not_ready_error_exception():
    """Test FileNotReadyError can be raised and caught."""
    with pytest.raises(FileNotReadyError):
        raise FileNotReadyError("Test error message")


def test_format_note_content(note_taking_toolkit):
    """Test _format_note_content formats note with header correctly."""
    result = note_taking_toolkit._format_note_content("test.md", "Hello world")
    assert result == "=== test.md ===\nHello world"

    # Test with multi-line content
    content = "Line 1\nLine 2\nLine 3"
    result = note_taking_toolkit._format_note_content("notes.md", content)
    assert result == "=== notes.md ===\nLine 1\nLine 2\nLine 3"

    # Test with empty content
    result = note_taking_toolkit._format_note_content("empty.md", "")
    assert result == "=== empty.md ===\n"

    # Test with file not found placeholder
    result = note_taking_toolkit._format_note_content(
        "missing.md", "[File not found]"
    )
    assert result == "=== missing.md ===\n[File not found]"


def test_validate_note_name_empty(note_taking_toolkit):
    """Test validation rejects empty note names."""
    result = note_taking_toolkit.create_note("", "content")
    assert "Error" in result
    assert "empty" in result.lower()

    result = note_taking_toolkit.create_note("   ", "content")
    assert "Error" in result
    assert "empty" in result.lower() or "whitespace" in result.lower()


def test_validate_note_name_too_long(note_taking_toolkit):
    """Test validation rejects note names exceeding max length."""
    long_name = "a" * 300
    result = note_taking_toolkit.create_note(long_name, "content")
    assert "Error" in result
    assert "maximum length" in result.lower() or "exceeds" in result.lower()


def test_validate_note_name_invalid_chars(note_taking_toolkit):
    """Test validation rejects note names with invalid characters."""
    invalid_names = [
        "note<test",
        "note>test",
        "note:test",
        'note"test',
        "note/test",
        "note\\test",
        "note|test",
        "note?test",
        "note*test",
    ]
    for invalid_name in invalid_names:
        result = note_taking_toolkit.create_note(invalid_name, "content")
        assert "Error" in result, f"Expected error for name: {invalid_name}"
        assert "invalid character" in result.lower()


def test_validate_note_name_path_traversal(note_taking_toolkit):
    """Test validation rejects path traversal attempts."""
    # Note: '../' contains '/' which is caught by invalid character check first
    result = note_taking_toolkit.create_note("../../../etc/passwd", "content")
    assert "Error" in result
    assert (
        "invalid character" in result.lower()
        or "path traversal" in result.lower()
    )

    result = note_taking_toolkit.create_note("/absolute/path", "content")
    assert "Error" in result
    assert (
        "invalid character" in result.lower()
        or "path traversal" in result.lower()
    )

    # Test path traversal without slash (using valid chars but '..')
    result = note_taking_toolkit.create_note("..secret", "content")
    assert "Error" in result
    assert "path traversal" in result.lower()


def test_validate_note_name_windows_reserved(note_taking_toolkit):
    """Test validation rejects Windows reserved names."""
    reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1", "con", "nul"]
    for reserved in reserved_names:
        result = note_taking_toolkit.create_note(reserved, "content")
        assert (
            "Error" in result
        ), f"Expected error for reserved name: {reserved}"
        assert "reserved" in result.lower()


def test_validate_note_name_dots_only(note_taking_toolkit):
    """Test validation rejects names consisting only of dots."""
    # Note: '...' contains '..' which is caught by path traversal check first
    result = note_taking_toolkit.create_note("...", "content")
    assert "Error" in result
    assert "path traversal" in result.lower() or "dots" in result.lower()

    # Single dot is also invalid (dots-only check)
    result = note_taking_toolkit.create_note(".", "content")
    assert "Error" in result


def test_validate_note_name_valid(note_taking_toolkit):
    """Test validation accepts valid note names."""
    valid_names = [
        "my_note",
        "my-note",
        "my.note",
        "MyNote123",
        "note with spaces",
        "日本語ノート",
        "note_2024",
    ]
    for valid_name in valid_names:
        result = note_taking_toolkit.create_note(valid_name, "content")
        assert (
            "successfully created" in result
        ), f"Expected success for: {valid_name}"


def test_append_note_validation(note_taking_toolkit):
    """Test that append_note also validates note names."""
    result = note_taking_toolkit.append_note("", "content")
    assert "Error" in result
    assert "empty" in result.lower()

    result = note_taking_toolkit.append_note("note<invalid", "content")
    assert "Error" in result
    assert "invalid character" in result.lower()


def test_invalid_note_name_error_exception():
    """Test InvalidNoteNameError can be raised and caught."""
    with pytest.raises(InvalidNoteNameError):
        raise InvalidNoteNameError("Test error message")
