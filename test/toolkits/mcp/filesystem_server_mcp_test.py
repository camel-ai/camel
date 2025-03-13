import os
import asyncio
import tempfile
import pytest

# Import the async tools you want to test.
# Adjust the import path if necessary.
from camel.toolkits.mcp.servers.filesystem_server_mcp import read_file, list_directory

@pytest.mark.asyncio
async def test_read_file_success():
    """
    Test that read_file returns the correct file contents when given a valid file.
    """
    # Create a temporary file with known content.
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
        tmp.write("Hello, Camel AI!\n")
        tmp_path = tmp.name

    try:
        # Call the read_file tool and remove trailing whitespace.
        result = await read_file(file_path=tmp_path)
        # Check that the result matches the content (newline removed by rstrip).
        assert result == "Hello, Camel AI!"
    finally:
        # Clean up the temporary file.
        os.remove(tmp_path)

@pytest.mark.asyncio
async def test_read_file_error():
    """
    Test that read_file returns an error message when the file does not exist.
    """
    non_existent_file = "this_file_does_not_exist.txt"
    result = await read_file(file_path=non_existent_file)
    # Check that the error message is returned.
    assert "Error reading file" in result

@pytest.mark.asyncio
async def test_list_directory_success():
    """
    Test that list_directory returns the correct list of entries for a valid directory.
    """
    # Create a temporary directory.
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a few temporary files in the directory.
        file_names = ["file1.txt", "file2.txt", "file3.txt"]
        for name in file_names:
            file_path = os.path.join(tmp_dir, name)
            with open(file_path, "w") as f:
                f.write("Test content")
        
        # Call the list_directory tool.
        result = await list_directory(directory_path=tmp_dir)
        # Convert the newline-separated result into a list.
        entries = result.split("\n")
        
        # Check that every file we created is in the directory listing.
        for name in file_names:
            assert name in entries

@pytest.mark.asyncio
async def test_list_directory_error():
    """
    Test that list_directory returns an error message when the directory does not exist.
    """
    non_existent_directory = "this_directory_does_not_exist"
    result = await list_directory(directory_path=non_existent_directory)
    assert "Error listing directory" in result
