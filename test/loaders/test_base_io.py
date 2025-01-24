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
from io import BytesIO
from pathlib import Path

import pytest

from camel.loaders.base_io import (
    DocxFile,
    File,
    HtmlFile,
    JsonFile,
    PdfFile,
    TxtFile,
    create_file,
    strip_consecutive_newlines,
)


# Define a FakeFile class for testing purposes
class FakeFile(File):
    """A fake file for testing purposes"""

    @classmethod
    def from_bytes(cls, file: BytesIO, filename: str) -> "FakeFile":
        return NotImplemented


# Define paths to test resources
UNIT_TESTS_ROOT = Path(__file__).parent.resolve()
TESTS_ROOT = UNIT_TESTS_ROOT.parent.resolve()
PROJECT_ROOT = TESTS_ROOT.parent.resolve()
RESOURCE_ROOT = PROJECT_ROOT / "test"
SAMPLE_ROOT = RESOURCE_ROOT / "data_samples"


# Test functions for each file type
def test_docx_file():
    filename = "test_hello.docx"
    with open(SAMPLE_ROOT / filename, "rb") as f:
        file = BytesIO(f.read())
        docx_file = DocxFile.from_bytes(file, filename)

    assert docx_file.name == filename
    assert isinstance(docx_file, DocxFile)
    assert len(docx_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert docx_file.docs[0]["page_content"] == "Hello World"


def test_docx_file_with_multiple_pages():
    filename = "test_hello_multi.docx"
    with open(SAMPLE_ROOT / filename, "rb") as f:
        file = BytesIO(f.read())
        docx_file = DocxFile.from_bytes(file, filename)

    assert docx_file.name == filename
    assert isinstance(docx_file, DocxFile)
    assert len(docx_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert (
        docx_file.docs[0]["page_content"]
        == "Hello World 1\nHello World 2\nHello World 3"
    )


def test_pdf_file_with_single_page():
    filename = "test_hello.pdf"
    with open(SAMPLE_ROOT / filename, "rb") as f:
        file = BytesIO(f.read())
        pdf_file = PdfFile.from_bytes(file, filename)

    assert pdf_file.name == filename
    assert isinstance(pdf_file, PdfFile)
    assert len(pdf_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert pdf_file.docs[0]["page_content"] == "Hello World"


def test_pdf_file_with_multiple_pages():
    filename = "test_hello_multi.pdf"
    with open(SAMPLE_ROOT / filename, "rb") as f:
        file = BytesIO(f.read())
        pdf_file = PdfFile.from_bytes(file, filename)

    assert pdf_file.name == filename
    assert isinstance(pdf_file, PdfFile)
    assert len(pdf_file.docs) == 3
    assert pdf_file.docs[0]["page_content"] == "Hello World 1"
    assert pdf_file.docs[1]["page_content"] == "Hello World 2"
    assert pdf_file.docs[2]["page_content"] == "Hello World 3"


def test_txt_file():
    filename = "test_hello.txt"
    with open(SAMPLE_ROOT / filename, "rb") as f:
        file = BytesIO(f.read())
        txt_file = TxtFile.from_bytes(file, filename)

    assert txt_file.name == filename
    assert isinstance(txt_file, TxtFile)
    assert len(txt_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert txt_file.docs[0]["page_content"] == "Hello World"


def test_json_file():
    filename = "test_hello.json"
    with open(SAMPLE_ROOT / filename, "rb") as f:
        file = BytesIO(f.read())
        json_file = JsonFile.from_bytes(file, filename)

    assert json_file.name == filename
    assert isinstance(json_file, JsonFile)
    assert len(json_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert json_file.docs[0]["page_content"] == '{"message": "Hello World"}'


def test_html_file():
    filename = "test_hello.html"
    with open(SAMPLE_ROOT / filename, "rb") as f:
        file = BytesIO(f.read())
        html_file = HtmlFile.from_bytes(file, filename)

    assert html_file.name == filename
    assert isinstance(html_file, HtmlFile)
    assert len(html_file.docs) == 1
    # Access 'page_content' from the dictionary in the docs list
    assert html_file.docs[0]["page_content"] == "Hello World"


# Test the `create_file` function with each file type
def test_create_file():
    for ext, file_class in [
        ("docx", DocxFile),
        ("pdf", PdfFile),
        ("txt", TxtFile),
        ("json", JsonFile),
        ("html", HtmlFile),
    ]:
        filename = f"test_hello.{ext}"
        with open(SAMPLE_ROOT / filename, "rb") as f:
            file = BytesIO(f.read())
            file_obj = create_file(file, filename)

        assert isinstance(file_obj, file_class)
        assert file_obj.name == filename
        assert len(file_obj.docs) == 1
        # Access 'page_content' from the dictionary in the docs list
        assert (
            file_obj.docs[0]["page_content"] == "Hello World"
            or '{"message": "Hello World"}'
        )


# Test that `create_file` function raises a NotImplementedError
# for unsupported file types
def test_create_file_not_implemented():
    file = BytesIO(b"Hello World")
    filename = "test.unknown"
    with pytest.raises(NotImplementedError):
        create_file(file, filename)


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
    assert file.file_id == file_copy.file_id

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
