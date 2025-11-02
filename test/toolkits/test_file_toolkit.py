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

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from camel.toolkits import FileToolkit, FileWriteToolkit


@pytest.fixture
def file_write_toolkit():
    r"""Create a FileToolkit instance for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Use FileToolkit (new name) for testing
        toolkit = FileToolkit(working_directory=temp_dir)
        yield toolkit


@pytest.fixture
def temp_dir():
    r"""Create a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_initialization():
    r"""Test the initialization of FileToolkit with default parameters."""
    toolkit = FileToolkit()

    assert toolkit.working_directory == Path("./camel_working_dir").resolve()
    assert toolkit.default_encoding == "utf-8"
    assert toolkit.backup_enabled is True


def test_initialization_with_custom_parameters():
    r"""Test the initialization of FileToolkit with custom parameters."""
    working_directory = "./custom_dir"
    default_encoding = "latin-1"
    backup_enabled = False

    toolkit = FileToolkit(
        working_directory=working_directory,
        default_encoding=default_encoding,
        backup_enabled=backup_enabled,
    )

    assert toolkit.working_directory == Path(working_directory).resolve()
    assert toolkit.default_encoding == default_encoding
    assert toolkit.backup_enabled is backup_enabled


def test_write_to_file_text(file_write_toolkit):
    r"""Test writing plain text to a file."""
    content = "Hello, world!"
    filename = "test.txt"

    result = file_write_toolkit.write_to_file(
        "Test Document", content, filename
    )

    # Check the result message
    assert "successfully written" in result

    # Check the file exists and has correct content
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()

    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()

    assert file_content == content


def test_write_to_file_markdown(file_write_toolkit):
    r"""Test writing markdown content to a file."""
    content = "# Heading\n\nThis is a paragraph with **bold** text."
    filename = "test.md"

    result = file_write_toolkit.write_to_file(
        "Markdown Document", content, filename
    )

    # Check the result message
    assert "successfully written" in result

    # Check the file exists and has correct content
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()

    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()

    assert file_content == content


def test_write_to_file_json(file_write_toolkit):
    r"""Test writing JSON data to a file."""
    data = {"name": "John", "age": 30, "city": "New York"}
    filename = "test.json"

    result = file_write_toolkit.write_to_file("JSON Document", data, filename)

    # Check the result message
    assert "successfully written" in result

    # Check the file exists and has correct content
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()

    with open(file_path, "r", encoding="utf-8") as f:
        file_content = json.load(f)

    assert file_content == data


def test_write_to_file_yaml(file_write_toolkit):
    r"""Test writing YAML data to a file."""
    data = {"name": "John", "age": 30, "city": "New York"}
    filename = "test.yaml"

    result = file_write_toolkit.write_to_file("YAML Document", data, filename)

    # Check the result message
    assert "successfully written" in result

    # Check the file exists and has correct content
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()

    with open(file_path, "r", encoding="utf-8") as f:
        file_content = yaml.safe_load(f)

    assert file_content == data


def test_write_to_file_csv_string(file_write_toolkit):
    r"""Test writing CSV content as a string to a file."""
    content = "name,age,city\nJohn,30,New York\nJane,25,San Francisco"
    filename = "test.csv"

    result = file_write_toolkit.write_to_file(
        "CSV Document", content, filename
    )

    # Check the result message
    assert "successfully written" in result

    # Check the file exists and has correct content
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()

    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()

    assert file_content == content


def test_write_to_file_csv_list(file_write_toolkit):
    r"""Test writing CSV content as a list of lists to a file."""
    content = [
        ["name", "age", "city"],
        ["John", 30, "New York"],
        ["Jane", 25, "San Francisco"],
    ]
    filename = "test_list.csv"

    result = file_write_toolkit.write_to_file(
        "CSV List Document", content, filename
    )

    # Check the result message
    assert "successfully written" in result

    # Check the file exists
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()

    # Read the CSV file and check content
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert lines[0].strip() == "name,age,city"
    assert lines[1].strip() == "John,30,New York"
    assert lines[2].strip() == "Jane,25,San Francisco"


def test_write_to_file_html(file_write_toolkit):
    r"""Test writing HTML content to a file."""
    content = '<head>\n    <meta charset="utf-8"><body><h1>Hello, '
    'world!</h1></body></html>'
    filename = "test.html"

    result = file_write_toolkit.write_to_file(
        "HTML Document", content, filename
    )

    # Check the result message
    assert "successfully written" in result

    # Check the file exists and has correct content
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()

    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()

    assert file_content == content


def test_write_to_file_no_extension(file_write_toolkit):
    r"""Test writing content to a file with no extension (should use default
    format).
    """
    content = "# Default format test"
    filename = "test_no_extension"

    result = file_write_toolkit.write_to_file(
        "Default Format Document", content, filename
    )

    # Check the result message
    assert "successfully written" in result

    # Check the file exists with default extension (.md) and has correct
    # content
    file_path = file_write_toolkit._resolve_filepath(filename + ".md")
    assert file_path.exists()

    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()

    assert file_content == content


def test_write_to_file_custom_encoding(file_write_toolkit):
    r"""Test writing content with a custom encoding."""
    content = "Hello, world with custom encoding!"
    filename = "test_encoding.txt"
    encoding = "latin-1"

    result = file_write_toolkit.write_to_file(
        "Custom Encoding Document", content, filename, encoding=encoding
    )

    # Check the result message
    assert "successfully written" in result

    # Check the file exists and has correct content when read with the same
    # encoding
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()

    with open(file_path, "r", encoding=encoding) as f:
        file_content = f.read()

    assert file_content == content


def test_write_to_file_nested_directory(file_write_toolkit):
    r"""Test writing to a file in a nested directory that doesn't exist yet."""
    content = "Content in nested directory"
    filename = "nested/dir/test.txt"

    result = file_write_toolkit.write_to_file(
        "Nested Directory Document", content, filename
    )

    # Check the result message
    assert "successfully written" in result

    # Check the file exists and has correct content
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()

    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()

    assert file_content == content


def test_write_to_file_absolute_path(temp_dir):
    r"""Test writing to a file using an absolute path."""
    toolkit = FileToolkit(working_directory="./default")
    content = "Content with absolute path"
    filename = os.path.join(temp_dir, "absolute_path.txt")

    result = toolkit.write_to_file("Absolute Path Document", content, filename)

    # Check the result message
    assert "successfully written" in result

    # Check the file exists and has correct content
    assert os.path.exists(filename)

    with open(filename, "r", encoding="utf-8") as f:
        file_content = f.read()

    assert file_content == content


def test_get_tools(file_write_toolkit):
    r"""Test that get_tools returns the correct function tools."""
    tools = file_write_toolkit.get_tools()

    # Check that we have the expected number of tools
    # (now 4: write_to_file, read_file, edit_file, search_files)
    assert len(tools) == 4

    # Check that the tools have the correct function names
    tool_names = [tool.get_function_name() for tool in tools]
    assert "write_to_file" in tool_names
    assert "read_file" in tool_names
    assert "edit_file" in tool_names
    assert "search_files" in tool_names


def test_sanitize_and_resolve_filepath(file_write_toolkit):
    r"""Test that _resolve_filepath sanitizes filenames
    with spaces and special characters.
    """
    # Filename with spaces and special characters
    unsafe_filename = "My Video: How to Fix! File @ Name?.md"
    # Expected sanitized filename (all disallowed characters replaced by
    # underscores)
    expected_sanitized = file_write_toolkit._sanitize_filename(unsafe_filename)

    # Resolve the filepath using the toolkit
    resolved_path = file_write_toolkit._resolve_filepath(unsafe_filename)
    # Expected path is in the toolkit's working_directory with the sanitized
    # filename
    expected_path = file_write_toolkit.working_directory / expected_sanitized

    # Check that the resolved path matches the expected path
    assert (
        resolved_path == expected_path.resolve()
    ), "The resolved file path does not match the expected sanitized path."


def test_backup_functionality(file_write_toolkit):
    r"""Test that backup files are created when backup_enabled is True."""
    # Write initial file
    content = "Initial content"
    filename = "test_backup.txt"
    result = file_write_toolkit.write_to_file(
        title="Test", content=content, filename=filename
    )
    assert "successfully" in result.lower()

    # Write again with backup enabled (default)
    new_content = "Updated content"
    result = file_write_toolkit.write_to_file(
        title="Test", content=new_content, filename=filename
    )
    assert "successfully" in result.lower()

    # Check that backup file exists
    import glob

    backup_files = glob.glob(
        str(file_write_toolkit.working_directory / f"{filename}.*.bak")
    )
    assert len(backup_files) == 1, "Backup file should have been created"

    # Read backup file and verify it contains original content
    with open(backup_files[0], 'r') as f:
        backup_content = f.read()
    assert "Initial content" in backup_content


def test_no_backup_when_disabled(tmp_path):
    r"""Test that no backup is created when backup_enabled is False."""
    # Use a temporary directory for this test
    toolkit = FileToolkit(
        working_directory=str(tmp_path), backup_enabled=False
    )

    # Write initial file
    content = "Initial content"
    filename = "test_no_backup.txt"
    result = toolkit.write_to_file(
        title="Test", content=content, filename=filename
    )
    assert "successfully" in result.lower()

    # Read the file to verify content
    file_path = toolkit.working_directory / filename
    assert file_path.exists()
    with open(file_path, 'r') as f:
        file_content = f.read()
    assert "Initial content" in file_content

    # Write again with backup disabled - should overwrite
    new_content = "Updated content"
    result = toolkit.write_to_file(
        title="Test", content=new_content, filename=filename
    )
    assert "successfully" in result.lower()

    # Check that no backup file exists
    import glob

    backup_files = glob.glob(
        str(toolkit.working_directory / f"{filename}.*.bak")
    )
    assert len(backup_files) == 0, "No backup file should have been created"

    # Check that the original file was overwritten (only 1 file exists)
    all_files = glob.glob(
        str(toolkit.working_directory / "test_no_backup*.txt")
    )
    assert len(all_files) == 1, "Should have only 1 file (overwritten)"

    # Verify the file contains the updated content
    with open(file_path, 'r') as f:
        file_content = f.read()
    assert "Updated content" in file_content
    assert "Initial content" not in file_content


def test_deprecated_alias():
    r"""Test that FileWriteToolkit still works with deprecation warning."""
    import warnings

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # This should trigger a deprecation warning
        toolkit = FileWriteToolkit()

        # Check that a deprecation warning was issued
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "FileWriteToolkit is deprecated" in str(w[0].message)

        # Verify the toolkit still works
        assert toolkit is not None
        assert hasattr(toolkit, 'write_to_file')
        assert hasattr(toolkit, 'read_file')
        assert hasattr(toolkit, 'edit_file')


def test_search_files_basic(file_write_toolkit):
    r"""Test basic file search functionality with default markdown files."""
    # create test files with content
    file_write_toolkit.write_to_file("Test", "CAMEL is great", "test1.md")
    file_write_toolkit.write_to_file("Test", "Python is awesome", "test2.md")
    file_write_toolkit.write_to_file("Test", "CAMEL framework", "test3.md")

    # search for pattern
    result = file_write_toolkit.search_files("CAMEL")
    result_data = json.loads(result)

    # verify results
    assert result_data["pattern"] == "CAMEL"
    assert result_data["total_matches"] == 2
    assert result_data["files_searched"] == 3
    assert len(result_data["matches"]) == 2


def test_search_files_with_file_types(file_write_toolkit):
    r"""Test file search with specific file types."""
    # create test files
    file_write_toolkit.write_to_file("Test", "Python code", "test.py")
    file_write_toolkit.write_to_file("Test", "Text file", "test.txt")
    file_write_toolkit.write_to_file("Test", "Markdown", "test.md")

    # search in python and text files only
    result = file_write_toolkit.search_files("file", file_types=["py", "txt"])
    result_data = json.loads(result)

    # verify results
    assert result_data["total_matches"] == 1
    assert result_data["file_types"] == ["py", "txt"]
    assert result_data["matches"][0]["file"] in ["test.py", "test.txt"]


def test_search_files_with_file_pattern(file_write_toolkit):
    r"""Test file search with glob pattern."""
    # create test files
    file_write_toolkit.write_to_file(
        "Test", "workflow data", "main_workflow.md"
    )
    file_write_toolkit.write_to_file(
        "Test", "workflow info", "test_workflow.md"
    )
    file_write_toolkit.write_to_file("Test", "other data", "readme.md")

    # search with file pattern
    result = file_write_toolkit.search_files(
        "workflow", file_pattern="*_workflow.md"
    )
    result_data = json.loads(result)

    # verify results
    assert result_data["file_pattern"] == "*_workflow.md"
    assert result_data["total_matches"] == 2
    assert result_data["files_searched"] == 2


def test_search_files_case_insensitive(file_write_toolkit):
    r"""Test that search is case-insensitive."""
    # create test file
    file_write_toolkit.write_to_file(
        "Test", "CAMEL is great\ncamel is small", "test.md"
    )

    # search for uppercase
    result_upper = file_write_toolkit.search_files("CAMEL")
    result_upper_data = json.loads(result_upper)

    # search for lowercase
    result_lower = file_write_toolkit.search_files("camel")
    result_lower_data = json.loads(result_lower)

    # verify case insensitivity - both should find 2 matches
    assert result_upper_data["total_matches"] == 2
    assert result_lower_data["total_matches"] == 2
    # verify both lines are found regardless of search case
    assert len(result_upper_data["matches"]) == 2
    assert len(result_lower_data["matches"]) == 2


def test_search_files_no_matches(file_write_toolkit):
    r"""Test search when no matches are found."""
    # create test files
    file_write_toolkit.write_to_file("Test", "Python code", "test.md")

    # search for non-existent pattern
    result = file_write_toolkit.search_files("nonexistent")
    result_data = json.loads(result)

    # verify no matches
    assert result_data["total_matches"] == 0
    assert len(result_data["matches"]) == 0
    assert result_data["files_searched"] == 1


def test_search_files_line_numbers(file_write_toolkit):
    r"""Test that line numbers are correct."""
    # create test file with multiple lines
    content = "line 1\nline 2 CAMEL\nline 3\nline 4 CAMEL\nline 5"
    file_write_toolkit.write_to_file("Test", content, "test.md")

    # search
    result = file_write_toolkit.search_files("CAMEL")
    result_data = json.loads(result)

    # verify line numbers
    assert result_data["total_matches"] == 2
    assert result_data["matches"][0]["line"] == 2
    assert result_data["matches"][1]["line"] == 4


def test_search_files_nested_directory(file_write_toolkit):
    r"""Test search in nested directories."""
    # create nested files
    file_write_toolkit.write_to_file("Test", "nested content", "dir1/file1.md")
    file_write_toolkit.write_to_file(
        "Test", "nested data", "dir1/dir2/file2.md"
    )

    # search recursively
    result = file_write_toolkit.search_files("nested")
    result_data = json.loads(result)

    # verify recursive search works
    assert result_data["total_matches"] == 2
    assert result_data["files_searched"] == 2


def test_search_files_duplicate_file_types(file_write_toolkit):
    r"""Test that duplicate file types are handled correctly."""
    # create test file
    file_write_toolkit.write_to_file("Test", "Python code", "test.py")

    # search with duplicate file types (including with dot prefix)
    result = file_write_toolkit.search_files(
        "Python", file_types=["py", "py", ".py"]
    )
    result_data = json.loads(result)

    # verify no duplicates in results (file searched only once)
    assert result_data["total_matches"] == 1
    assert result_data["files_searched"] == 1
    assert len(result_data["matches"]) == 1
    # verify normalized file types in result
    assert result_data["file_types"] == ["py"]


def test_search_files_empty_file_types(file_write_toolkit):
    r"""Test that empty strings in file_types are filtered out."""
    # create test files
    file_write_toolkit.write_to_file("Test", "Content", "test.py")
    file_write_toolkit.write_to_file("Test", "Content", "test.txt")

    # search with empty strings in file_types
    result = file_write_toolkit.search_files(
        "Content", file_types=["py", "", "txt"]
    )
    result_data = json.loads(result)

    # verify empty strings are filtered out
    assert "" not in result_data["file_types"]
    assert set(result_data["file_types"]) == {"py", "txt"}
    assert result_data["total_matches"] == 2


def test_search_files_path_with_special_chars(file_write_toolkit):
    r"""Test search in directory with special characters in name."""
    # create directory with special characters
    special_dir = "test-dir with spaces!"
    file_write_toolkit.write_to_file(
        "Test", "Content", f"{special_dir}/test.md"
    )

    # search in the directory with special characters
    result = file_write_toolkit.search_files("Content", path=special_dir)
    result_data = json.loads(result)

    # verify search succeeded
    assert "error" not in result_data
    assert result_data["total_matches"] == 1
    assert result_data["files_searched"] == 1


def test_search_files_invalid_path(file_write_toolkit):
    r"""Test search with non-existent directory path."""
    # search in non-existent directory
    result = file_write_toolkit.search_files("Content", path="nonexistent/dir")
    result_data = json.loads(result)

    # verify error is returned
    assert "error" in result_data
    assert "does not exist" in result_data["error"]


def test_search_files_path_is_file(file_write_toolkit):
    r"""Test search when path points to a file instead of directory."""
    # create a file
    file_write_toolkit.write_to_file("Test", "Content", "test.py")

    # try to search with path pointing to the file
    result = file_write_toolkit.search_files("Content", path="test.py")
    result_data = json.loads(result)

    # verify error is returned
    assert "error" in result_data
    assert "not a directory" in result_data["error"]
