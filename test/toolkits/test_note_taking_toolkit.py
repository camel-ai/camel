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

import pytest

from camel.toolkits import NoteTakingToolkit


@pytest.fixture
def note_taking_toolkit():
    # Create a toolkit with a temporary note file
    return NoteTakingToolkit(working_directory="test_notes.md")


def test_append_note(note_taking_toolkit):
    # Test appending a note
    note_file = Path("test_notes.md")
    if note_file.exists():
        note_file.unlink()

    result = note_taking_toolkit.append_note("First note.")
    assert "appended" in result
    assert note_file.read_text() == "First note.\n"

    result = note_taking_toolkit.append_note("Second note.")
    assert "appended" in result
    assert note_file.read_text() == "First note.\nSecond note.\n"

    # Clean up the test file
    if note_file.exists():
        note_file.unlink()


def test_read_note(note_taking_toolkit):
    # Test reading a note
    note_file = Path("test_notes.md")
    if note_file.exists():
        note_file.unlink()

    # Test reading non-existent file
    assert "does not exist" in note_taking_toolkit.read_note()

    note_taking_toolkit.append_note("Hello, world!")
    assert note_taking_toolkit.read_note() == "Hello, world!\n"

    # Clean up the test file
    if note_file.exists():
        note_file.unlink()
