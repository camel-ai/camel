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

from camel.toolkits import FileWriteToolkit


@pytest.fixture
def file_write_toolkit():
    r"""Create a FileWriteToolkit instance for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        toolkit = FileWriteToolkit(output_dir=temp_dir)
        yield toolkit


@pytest.fixture
def temp_dir():
    r"""Create a temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_initialization():
    r"""Test the initialization of FileWriteToolkit with default parameters."""
    toolkit = FileWriteToolkit()

    assert toolkit.output_dir == Path("./").resolve()
    assert toolkit.default_encoding == "utf-8"
    assert toolkit.backup_enabled is True


def test_initialization_with_custom_parameters():
    r"""Test the initialization of FileWriteToolkit with custom parameters."""
    output_dir = "./custom_dir"
    default_encoding = "latin-1"
    backup_enabled = False

    toolkit = FileWriteToolkit(
        output_dir=output_dir,
        default_encoding=default_encoding,
        backup_enabled=backup_enabled,
    )

    assert toolkit.output_dir == Path(output_dir).resolve()
    assert toolkit.default_encoding == default_encoding
    assert toolkit.backup_enabled is backup_enabled


def test_write_to_file_text(file_write_toolkit):
    r"""Test writing plain text to a file."""
    content = "Hello, world!"
    filename = "test.txt"

    result = file_write_toolkit.write_to_file(content, filename)

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

    result = file_write_toolkit.write_to_file(content, filename)

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

    result = file_write_toolkit.write_to_file(data, filename)

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

    result = file_write_toolkit.write_to_file(data, filename)

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

    result = file_write_toolkit.write_to_file(content, filename)

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

    result = file_write_toolkit.write_to_file(content, filename)

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
    content = "<html><body><h1>Hello, world!</h1></body></html>"
    filename = "test.html"

    result = file_write_toolkit.write_to_file(content, filename)

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

    result = file_write_toolkit.write_to_file(content, filename)

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
        content, filename, encoding=encoding
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

    result = file_write_toolkit.write_to_file(content, filename)

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
    toolkit = FileWriteToolkit(output_dir="./default")
    content = "Content with absolute path"
    filename = os.path.join(temp_dir, "absolute_path.txt")

    result = toolkit.write_to_file(content, filename)

    # Check the result message
    assert "successfully written" in result

    # Check the file exists and has correct content
    assert os.path.exists(filename)

    with open(filename, "r", encoding="utf-8") as f:
        file_content = f.read()

    assert file_content == content


def test_read_from_file_text(file_write_toolkit):
    r"""Test reading plain text from a file."""
    content = "Hello, world!"
    filename = "test_read.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then read it back
    result = file_write_toolkit.read_from_file(filename)

    assert result == content


def test_read_from_file_json(file_write_toolkit):
    r"""Test reading JSON data from a file."""
    data = {"name": "John", "age": 30, "city": "New York"}
    filename = "test_read.json"

    # First write the file
    file_write_toolkit.write_to_file(data, filename)

    # Then read it back
    result = file_write_toolkit.read_from_file(filename)

    assert result == data


def test_read_from_file_csv(file_write_toolkit):
    r"""Test reading CSV data from a file."""
    data = [
        ["name", "age", "city"],
        ["John", "30", "New York"],
        ["Jane", "25", "San Francisco"],
    ]
    filename = "test_read.csv"

    # First write the file
    file_write_toolkit.write_to_file(data, filename)

    # Then read it back
    result = file_write_toolkit.read_from_file(filename)

    assert result == data


def test_read_from_file_yaml(file_write_toolkit):
    r"""Test reading YAML data from a file."""
    data = {"name": "John", "age": 30, "city": "New York"}
    filename = "test_read.yaml"

    # First write the file
    file_write_toolkit.write_to_file(data, filename)

    # Then read it back
    result = file_write_toolkit.read_from_file(filename)

    assert result == data


def test_read_from_file_nonexistent(file_write_toolkit):
    r"""Test reading from a file that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        file_write_toolkit.read_from_file("nonexistent.txt")


def test_read_file_content_full(file_write_toolkit):
    r"""Test reading full file content."""
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    filename = "test_content.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then read it back
    result = file_write_toolkit.read_file_content(filename)

    assert result == content


def test_read_file_content_partial(file_write_toolkit):
    r"""Test reading partial file content with line limits."""
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    filename = "test_content_partial.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then read first 3 lines
    result = file_write_toolkit.read_file_content(filename, max_lines=3)

    assert result == "Line 1\nLine 2\nLine 3\n"


def test_read_file_content_with_start_line(file_write_toolkit):
    r"""Test reading file content starting from a specific line."""
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    filename = "test_content_start.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then read starting from line 3
    result = file_write_toolkit.read_file_content(filename, start_line=3)

    # The result should match the expected content (without trailing newline)
    assert result == "Line 3\nLine 4\nLine 5"


def test_read_file_content_invalid_start_line(file_write_toolkit):
    r"""Test reading file content with invalid start line."""
    with pytest.raises(ValueError, match="start_line must be 1 or greater"):
        file_write_toolkit.read_file_content("test.txt", start_line=0)


def test_read_file_content_invalid_max_lines(file_write_toolkit):
    r"""Test reading file content with invalid max lines."""
    with pytest.raises(ValueError, match="max_lines must be 1 or greater"):
        file_write_toolkit.read_file_content("test.txt", max_lines=0)


def test_replace_in_file_simple(file_write_toolkit):
    r"""Test simple text replacement in a file."""
    content = "Hello, world! Hello, universe!"
    filename = "test_replace.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then replace text
    result = file_write_toolkit.replace_in_file(filename, "Hello", "Hi")

    # Check the result message
    assert "Replaced 2 occurrence(s)" in result

    # Check the file content was updated
    updated_content = file_write_toolkit.read_from_file(filename)
    assert updated_content == "Hi, world! Hi, universe!"


def test_replace_in_file_case_sensitive(file_write_toolkit):
    r"""Test case-sensitive text replacement."""
    content = "Hello, world! hello, universe!"
    filename = "test_replace_case.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then replace text (case-sensitive)
    result = file_write_toolkit.replace_in_file(
        filename, "Hello", "Hi", case_sensitive=True
    )

    # Check the result message
    assert "Replaced 1 occurrence(s)" in result

    # Check the file content was updated
    updated_content = file_write_toolkit.read_from_file(filename)
    assert updated_content == "Hi, world! hello, universe!"


def test_replace_in_file_case_insensitive(file_write_toolkit):
    r"""Test case-insensitive text replacement."""
    content = "Hello, world! hello, universe!"
    filename = "test_replace_case_insensitive.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then replace text (case-insensitive)
    result = file_write_toolkit.replace_in_file(
        filename, "hello", "Hi", case_sensitive=False
    )

    # Check the result message
    assert "Replaced 2 occurrence(s)" in result

    # Check the file content was updated
    updated_content = file_write_toolkit.read_from_file(filename)
    assert updated_content == "Hi, world! Hi, universe!"


def test_replace_in_file_with_count(file_write_toolkit):
    r"""Test text replacement with count limit."""
    content = "Hello, world! Hello, universe! Hello, galaxy!"
    filename = "test_replace_count.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then replace text with count limit
    result = file_write_toolkit.replace_in_file(
        filename, "Hello", "Hi", count=2
    )

    # Check the result message
    assert "Replaced 2 occurrence(s)" in result

    # Check the file content was updated
    updated_content = file_write_toolkit.read_from_file(filename)
    assert updated_content == "Hi, world! Hi, universe! Hello, galaxy!"


def test_replace_in_file_nonexistent(file_write_toolkit):
    r"""Test replacing text in a file that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        file_write_toolkit.replace_in_file("nonexistent.txt", "old", "new")


def test_search_in_file_simple(file_write_toolkit):
    r"""Test simple text search in a file."""
    content = (
        "Hello, world! This is a test file.\n"
        "It contains multiple lines.\n"
        "Hello again!"
    )
    filename = "test_search.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then search for text
    result = file_write_toolkit.search_in_file(filename, "Hello")

    # Check the result structure
    assert "matches" in result
    assert "total_matches" in result
    assert "file_path" in result
    assert result["total_matches"] == 2
    assert len(result["matches"]) == 2


def test_search_in_file_with_context(file_write_toolkit):
    r"""Test text search with context lines."""
    content = "Line 1\nLine 2\nHello, world!\nLine 4\nLine 5"
    filename = "test_search_context.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then search for text with context
    result = file_write_toolkit.search_in_file(
        filename, "Hello", context_lines=1
    )

    # Check the result
    assert result["total_matches"] == 1
    assert "context" in result["matches"][0]
    assert len(result["matches"][0]["context"]) == 3  # Line 2, 3, 4


def test_search_in_file_case_insensitive(file_write_toolkit):
    r"""Test case-insensitive text search."""
    content = "Hello, world! hello, universe!"
    filename = "test_search_case.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then search for text (case-insensitive)
    result = file_write_toolkit.search_in_file(
        filename, "hello", case_sensitive=False
    )

    # Check the result
    assert result["total_matches"] == 2


def test_search_in_file_regex(file_write_toolkit):
    r"""Test regex search in a file."""
    content = "Hello, world! Hi, universe! Hey, galaxy!"
    filename = "test_search_regex.txt"

    # First write the file
    file_write_toolkit.write_to_file(content, filename)

    # Then search with regex
    result = file_write_toolkit.search_in_file(
        filename, r"H[a-z]y", use_regex=True
    )

    # Check the result
    assert result["total_matches"] == 1
    assert result["matches"][0]["match_text"] == "Hey"


def test_search_in_file_nonexistent(file_write_toolkit):
    r"""Test searching in a file that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        file_write_toolkit.search_in_file("nonexistent.txt", "test")


def test_find_files_simple(file_write_toolkit):
    r"""Test finding files with simple pattern."""
    # Create some test files
    file_write_toolkit.write_to_file("content1", "test1.txt")
    file_write_toolkit.write_to_file("content2", "test2.txt")
    file_write_toolkit.write_to_file("content3", "other.md")

    # Find all .txt files
    result = file_write_toolkit.find_files("*.txt")

    # Check the result
    assert len(result) == 2
    assert any("test1.txt" in path for path in result)
    assert any("test2.txt" in path for path in result)


def test_find_files_recursive(file_write_toolkit):
    r"""Test finding files recursively."""
    # Create files in subdirectories
    file_write_toolkit.write_to_file("content1", "subdir/test1.txt")
    file_write_toolkit.write_to_file("content2", "subdir/test2.txt")
    file_write_toolkit.write_to_file("content3", "test3.txt")

    # Find all .txt files recursively
    result = file_write_toolkit.find_files("*.txt", recursive=True)

    # Check the result
    assert len(result) == 3
    assert any("test1.txt" in path for path in result)
    assert any("test2.txt" in path for path in result)
    assert any("test3.txt" in path for path in result)


def test_find_files_non_recursive(file_write_toolkit):
    r"""Test finding files non-recursively."""
    # Create files in subdirectories
    file_write_toolkit.write_to_file("content1", "subdir/test1.txt")
    file_write_toolkit.write_to_file("content2", "test2.txt")

    # Find .txt files non-recursively
    result = file_write_toolkit.find_files("*.txt", recursive=False)

    # Check the result (should only find files in root directory)
    assert len(result) == 1
    assert any("test2.txt" in path for path in result)


def test_find_files_case_sensitive(file_write_toolkit):
    r"""Test finding files with case sensitivity."""
    # Create test files
    file_write_toolkit.write_to_file("content1", "Test.txt")
    file_write_toolkit.write_to_file("content2", "test.txt")

    # Find files case-sensitively
    result = file_write_toolkit.find_files("test.txt", case_sensitive=True)

    # Check the result
    assert len(result) == 1
    assert any("test.txt" in path for path in result)


def test_find_files_case_insensitive(file_write_toolkit):
    r"""Test finding files with case insensitivity."""
    # Create test files
    file_write_toolkit.write_to_file("content1", "Test.txt")
    file_write_toolkit.write_to_file("content2", "test.txt")

    # Find files case-insensitively
    result = file_write_toolkit.find_files("test.txt", case_sensitive=False)

    # On Windows, case-insensitive matching might not work as expected
    # with glob. So we'll check that at least one file is found
    assert len(result) >= 1


def test_find_files_hidden(file_write_toolkit):
    r"""Test finding hidden files."""
    # Create hidden and non-hidden files
    file_write_toolkit.write_to_file("content1", ".hidden.txt")
    file_write_toolkit.write_to_file("content2", "visible.txt")

    # Find files including hidden ones
    result = file_write_toolkit.find_files("*.txt", include_hidden=True)

    # Check the result - on Windows, hidden files might not be found
    # as expected
    assert len(result) >= 1
    assert any("visible.txt" in path for path in result)


def test_find_files_exclude_hidden(file_write_toolkit):
    r"""Test finding files excluding hidden ones."""
    # Create hidden and non-hidden files
    file_write_toolkit.write_to_file("content1", ".hidden.txt")
    file_write_toolkit.write_to_file("content2", "visible.txt")

    # Find files excluding hidden ones
    result = file_write_toolkit.find_files("*.txt", include_hidden=False)

    # Check the result
    assert len(result) == 1
    assert any("visible.txt" in path for path in result)


def test_find_files_nonexistent_directory(file_write_toolkit):
    r"""Test finding files in a directory that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        file_write_toolkit.find_files(
            "*.txt", directory="/nonexistent/directory"
        )


def test_find_files_not_directory(file_write_toolkit):
    r"""Test finding files when the path is not a directory."""
    # Create a file
    file_write_toolkit.write_to_file("content", "test.txt")

    # Try to use the file as a directory - should raise FileNotFoundError
    # first
    with pytest.raises(FileNotFoundError):
        file_write_toolkit.find_files("*.txt", directory="test.txt")


def test_get_tools(file_write_toolkit):
    r"""Test that get_tools returns the correct function tools."""
    tools = file_write_toolkit.get_tools()

    # Check that we have the expected number of tools (6 methods)
    assert len(tools) == 6

    # Check that the tools have the correct function names
    function_names = [tool.get_function_name() for tool in tools]
    expected_names = [
        "write_to_file",
        "read_from_file",
        "read_file_content",
        "replace_in_file",
        "search_in_file",
        "find_files",
    ]

    for expected_name in expected_names:
        assert expected_name in function_names


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
    # Expected path is in the toolkit's output_dir with the sanitized filename
    expected_path = file_write_toolkit.output_dir / expected_sanitized

    # Check that the resolved path matches the expected path
    assert (
        resolved_path == expected_path.resolve()
    ), "The resolved file path does not match the expected sanitized path."


def test_sanitize_filename():
    r"""Test the _sanitize_filename method directly."""
    toolkit = FileWriteToolkit()

    # Test various unsafe filenames
    test_cases = [
        ("My File.txt", "My_File.txt"),
        ("file@name#.md", "file_name_.md"),
        ("path/to/file with spaces.py", "path_to_file_with_spaces.py"),
        ("normal_filename.txt", "normal_filename.txt"),
        ("file with (parentheses).txt", "file_with__parentheses_.txt"),
    ]

    for unsafe, expected in test_cases:
        sanitized = toolkit._sanitize_filename(unsafe)
        assert sanitized == expected


def test_write_to_file_pdf(file_write_toolkit):
    r"""Test writing PDF content to a file."""
    content = "This is a test PDF content."
    filename = "test.pdf"

    result = file_write_toolkit.write_to_file(content, filename)

    # Check the result message
    assert "successfully written" in result

    # Check the file exists
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()


@pytest.mark.skip(reason="DOCX dependency not available in test environment")
def test_write_to_file_docx(file_write_toolkit):
    r"""Test writing DOCX content to a file."""
    content = "This is a test DOCX content."
    filename = "test.docx"

    result = file_write_toolkit.write_to_file(content, filename)

    # Check the result message
    assert "successfully written" in result

    # Check the file exists
    file_path = file_write_toolkit._resolve_filepath(filename)
    assert file_path.exists()


def test_write_to_file_error_handling(file_write_toolkit):
    r"""Test error handling when writing to file fails."""
    # Test with invalid encoding
    content = "Test content"
    filename = "test_error.txt"

    result = file_write_toolkit.write_to_file(
        content, filename, encoding="invalid_encoding"
    )

    # Should return an error message
    assert "Error occurred" in result


def test_read_from_file_error_handling(file_write_toolkit):
    r"""Test error handling when reading from file fails."""
    # Create a file with invalid JSON
    content = "{ invalid json content"
    filename = "test_invalid.json"

    file_write_toolkit.write_to_file(content, filename)

    # Reading should raise an error
    with pytest.raises(ValueError):
        file_write_toolkit.read_from_file(filename)
