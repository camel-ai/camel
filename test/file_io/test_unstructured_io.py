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
import pytest

from camel.file_io.unstructured_io import UnstructuredModules


# Create a fixture to initialize the UnstructuredModules instance
@pytest.fixture
def unstructured_instance():
    return UnstructuredModules()


# Test the ensure_unstructured_version method
def test_ensure_unstructured_version(unstructured_instance):
    # Test with a valid version
    unstructured_instance.ensure_unstructured_version("0.10.30")

    # Test with an invalid version (should raise a ValueError)
    with pytest.raises(ValueError):
        unstructured_instance.ensure_unstructured_version("1.0.0")


# Test the parse_file_or_url method
def test_parse_file_or_url(unstructured_instance):
    # You can mock the required dependencies and test different scenarios here

    # Test parsing a valid URL (mock the necessary dependencies)
    result = unstructured_instance.parse_file_or_url(
        "https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
        "philadelphia-eagles-spt-intl/index.html")
    assert isinstance(result, list)

    # Test parsing a non-existent file (should raise FileNotFoundError)
    with pytest.raises(FileNotFoundError):
        unstructured_instance.parse_file_or_url("nonexistent_file.txt")


# Test the clean_text_data method
def test_clean_text_data(unstructured_instance):
    # Test with a valid cleaning option
    options = {"clean_extra_whitespace": {}}
    cleaned_text = unstructured_instance.clean_text_data(
        "  Hello  World  ", options)
    assert cleaned_text == "Hello World"  # Check the expected cleaned text

    # Test with an invalid cleaning option (should raise AttributeError)
    options = {"invalid_cleaning_option": {}}
    with pytest.raises(AttributeError):
        unstructured_instance.clean_text_data("Test Text", options)


# Test the extract_data_from_text method
def test_extract_data_from_text(unstructured_instance):
    # Test extracting an email address
    email_text = "Contact me at example@email.com."
    extracted_email = unstructured_instance.extract_data_from_text(
        "extract_email_address", email_text)
    assert extracted_email == ["example@email.com"]


# Test the chunk_elements method
def test_chunk_elements(unstructured_instance):

    url = ("https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
           "philadelphia-eagles-spt-intl/index.html")
    elements = unstructured_instance.parse_file_or_url(url)
    chunked_sections = unstructured_instance.chunk_elements(
        "chunk_by_title", elements)
    assert len(chunked_sections) == 7  # Check the number of chunks
