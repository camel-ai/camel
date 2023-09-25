# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from io import BytesIO
from pathlib import Path

import pytest

from camel.functions.data_io_functions import (
    DocxFile,
    File,
    HtmlFile,
    JsonFile,
    PdfFile,
    TxtFile,
    read_file,
    strip_consecutive_newlines,
)


# Define a FakeFile class for testing purposes
class FakeFile(File):
    """A fake file for testing purposes"""

    @classmethod
    def from_bytes(cls, file: BytesIO) -> "FakeFile":
        return NotImplemented


# Define paths to test resources
UNIT_TESTS_ROOT = Path(__file__).parent.resolve()
TESTS_ROOT = UNIT_TESTS_ROOT.parent.resolve()
PROJECT_ROOT = TESTS_ROOT.parent.resolve()
RESOURCE_ROOT = PROJECT_ROOT / "test"
SAMPLE_ROOT = RESOURCE_ROOT / "data_samples"


# Test functions for each file type
def test_docx_file():
    with open(SAMPLE_ROOT / "test_hello.docx", "rb") as f:
        file = BytesIO(f.read())
        file.name = "test.docx"
        docx_file = DocxFile.from_bytes(file)

    assert docx_file.name == "test.docx"
    assert len(docx_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert docx_file.docs[0]["page_content"] == "Hello World"


def test_docx_file_with_multiple_pages():
    with open(SAMPLE_ROOT / "test_hello_multi.docx", "rb") as f:
        file = BytesIO(f.read())
        file.name = "test.docx"
        docx_file = DocxFile.from_bytes(file)

    assert docx_file.name == "test.docx"
    assert len(docx_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert (docx_file.docs[0]["page_content"] ==
            "Hello World 1\nHello World 2\nHello World 3")


def test_pdf_file_with_single_page():
    with open(SAMPLE_ROOT / "test_hello.pdf", "rb") as f:
        file = BytesIO(f.read())
        file.name = "test_hello.pdf"
        pdf_file = PdfFile.from_bytes(file)

    assert pdf_file.name == "test_hello.pdf"
    assert len(pdf_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert pdf_file.docs[0]["page_content"] == "Hello World"


def test_pdf_file_with_multiple_pages():
    with open(SAMPLE_ROOT / "test_hello_multi.pdf", "rb") as f:
        file = BytesIO(f.read())
        file.name = "test_hello_multiple.pdf"
        pdf_file = PdfFile.from_bytes(file)

    assert pdf_file.name == "test_hello_multiple.pdf"
    assert len(pdf_file.docs) == 3
    assert pdf_file.docs[0]["page_content"] == "Hello World 1"
    assert pdf_file.docs[1]["page_content"] == "Hello World 2"
    assert pdf_file.docs[2]["page_content"] == "Hello World 3"


def test_txt_file():
    with open(SAMPLE_ROOT / "test_hello.txt", "rb") as f:
        file = BytesIO(f.read())
        file.name = "test.txt"
        txt_file = TxtFile.from_bytes(file)

    assert txt_file.name == "test.txt"
    assert len(txt_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert txt_file.docs[0]["page_content"] == "Hello World"


def test_json_file():
    with open(SAMPLE_ROOT / "test_hello.json", "rb") as f:
        file = BytesIO(f.read())
        file.name = "test.json"
        json_file = JsonFile.from_bytes(file)

    assert json_file.name == "test.json"
    assert len(json_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert json_file.docs[0]["page_content"] == '{"message": "Hello World"}'


def test_html_file():
    with open(SAMPLE_ROOT / "test_hello.html", "rb") as f:
        file = BytesIO(f.read())
        file.name = "test.html"
        html_file = HtmlFile.from_bytes(file)

    assert html_file.name == "test.html"
    assert len(html_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert html_file.docs[0]["page_content"] == "Hello World"


# Test the `read_file` function with each file type
def test_read_file():
    for ext, FileClass in [
        (".docx", DocxFile),
        (".pdf", PdfFile),
        (".txt", TxtFile),
        (".json", JsonFile),
        (".html", HtmlFile),
    ]:
        with open(SAMPLE_ROOT / f"test_hello{ext}", "rb") as f:
            file = BytesIO(f.read())
            file.name = f"test_hello{ext}"
            file_obj = read_file(file)

        assert isinstance(file_obj, FileClass)
        assert file_obj.name == f"test_hello{ext}"
        assert len(file_obj.docs) == 1
        # Access 'page_content' from the dictionary in the docs list
        assert (file_obj.docs[0]["page_content"] == "Hello World"
                or '{"message": "Hello World"}')


# Test that read_file raises a NotImplementedError for unsupported file types
def test_read_file_not_implemented():
    file = BytesIO(b"Hello World")
    file.name = "test.unknown"
    with pytest.raises(NotImplementedError):
        read_file(file)


# Test the File.copy() method
def test_file_copy():
    # Create a Document and FakeFile instance
    document = {"page_content": "test content", "metadata": {"page": "1"}}
    file = FakeFile("test_file", "1234", {"author": "test"}, [document])

    # Create a copy of the file
    file_copy = file.copy()

    # Check that the original and copy are distinct objects
    assert file is not file_copy

    # Check that the copy has the same attributes as the original
    assert file.name == file_copy.name
    assert file.id == file_copy.id

    # Check that the mutable attributes were deeply copied
    assert file.metadata == file_copy.metadata
    assert file.metadata is not file_copy.metadata

    # Check that the documents were deeply copied
    assert file.docs == file_copy.docs
    assert file.docs is not file_copy.docs

    # Check that individual documents are not the same objects
    assert file.docs[0] is not file_copy.docs[0]

    # Check that the documents have the same attributes
    assert file.docs[0]["page_content"] == file_copy.docs[0]["page_content"]
    assert file.docs[0]["metadata"] == file_copy.docs[0]["metadata"]


# Test the strip_consecutive_newlines function
def test_strip_consecutive_newlines():
    # Test with multiple consecutive newlines
    text = "\n\n\n"
    expected = "\n"
    assert strip_consecutive_newlines(text) == expected

    # Test with newlines and spaces
    text = "\n \n \n"
    expected = "\n"
    assert strip_consecutive_newlines(text) == expected

    # Test with newlines and tabs
    text = "\n\t\n\t\n"
    expected = "\n"
    assert strip_consecutive_newlines(text) == expected

    # Test with mixed whitespace characters
    text = "\n \t\n \t \n"
    expected = "\n"
    assert strip_consecutive_newlines(text) == expected

    # Test with no consecutive newlines
    text = "\nHello\nWorld\n"
    expected = "\nHello\nWorld\n"
    assert strip_consecutive_newlines(text) == expected
