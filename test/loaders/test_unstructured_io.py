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
import uuid
from typing import Any, Dict, List, Tuple

import pytest

from camel.loaders import UnstructuredIO


# Create a fixture to initialize the UnstructuredIO instance
@pytest.fixture
def unstructured_instance() -> UnstructuredIO:
    return UnstructuredIO()


# Test the create_element_from_text method
def test_create_element_from_text(unstructured_instance: UnstructuredIO):
    # Input parameters
    test_text = "Hello, World!"
    test_id = str(uuid.uuid4())
    test_embeddings = [0.1, 0.2, 0.3]
    test_filename = "testfile.txt"
    test_directory = "/test/directory"
    test_modified = "2024-04-01"
    test_filetype = "txt"
    test_parent_id = str(uuid.uuid4())

    # Expected Metadata construction
    expected_metadata = {
        "filename": test_filename,
        "file_directory": test_directory,
        "last_modified": test_modified,
        "filetype": test_filetype,
        "parent_id": test_parent_id,
    }

    # Create the element
    element = unstructured_instance.create_element_from_text(
        text=test_text,
        element_id=test_id,
        embeddings=test_embeddings,
        filename=test_filename,
        file_directory=test_directory,
        last_modified=test_modified,
        filetype=test_filetype,
        parent_id=test_parent_id,
    )

    # Assertions to verify correct element creation
    assert element.to_dict()['text'] == test_text
    assert element.to_dict()['element_id'] == test_id
    assert element.to_dict()['embeddings'] == test_embeddings
    assert element.to_dict()['metadata'] == expected_metadata


# Test the parse_file_or_url method
def test_parse_file_or_url(unstructured_instance: UnstructuredIO):
    # You can mock the required dependencies and test different scenarios here

    # Test parsing a valid URL (mock the necessary dependencies)
    result = unstructured_instance.parse_file_or_url(
        "https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
        "philadelphia-eagles-spt-intl/index.html"
    )
    assert isinstance(result, list)

    # Test parsing a non-existent file (should raise FileNotFoundError)
    with pytest.raises(FileNotFoundError):
        unstructured_instance.parse_file_or_url("nonexistent_file.txt")


# Test the clean_text_data method
def test_clean_text_data(unstructured_instance: UnstructuredIO):
    # Test with a valid cleaning option
    test_options: List[Tuple[str, Dict[str, Any]]] = [
        ("clean_extra_whitespace", {})
    ]
    cleaned_text = unstructured_instance.clean_text_data(
        text="  Hello  World  ", clean_options=test_options
    )
    assert cleaned_text == "Hello World"

    # Test with default cleaning options (no options provided)
    default_cleaned_text = unstructured_instance.clean_text_data(
        text="\x88  Hello  World  "
    )
    assert default_cleaned_text == "Hello World"

    # Test with an invalid cleaning option (should raise ValueError)
    test_options = [("invalid_cleaning_option", {})]
    with pytest.raises(ValueError):
        unstructured_instance.clean_text_data(
            text="Test Text", clean_options=test_options
        )


# Test the extract_data_from_text method
def test_extract_data_from_text(unstructured_instance: UnstructuredIO):
    # Test extracting an email address
    test_email_text = "Contact me at example@email.com."
    extracted_email = unstructured_instance.extract_data_from_text(
        text=test_email_text, extract_type="extract_email_address"
    )
    assert extracted_email == ["example@email.com"]

    # Test with an invalid extract option (should raise ValueError)
    test_extract_type = "invalid_extracting_option"
    with pytest.raises(ValueError):
        unstructured_instance.extract_data_from_text(
            text=test_email_text,
            extract_type=test_extract_type,  # type: ignore[arg-type]
        )


# Test the stage_elements method
def test_stage_elements_for_csv(unstructured_instance: UnstructuredIO):
    # Test staging for baseplate
    test_url = (
        "https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
        "philadelphia-eagles-spt-intl/index.html"
    )
    test_elements = unstructured_instance.parse_file_or_url(test_url)
    staged_element: Any = unstructured_instance.stage_elements(
        elements=test_elements,  # type:ignore[arg-type]
        stage_type="stage_for_baseplate",
    )
    assert staged_element['rows'][0] == {
        'data': {
            'type': 'NarrativeText',
            'element_id': '0aafb4e862cf2f95e55f76b641766e39',
            'text': 'Miles Sanders scores a touchdown against the San Francisco 49ers during the NFC Championship game at Lincoln Financial Field.',  # noqa: E501
        },
        'metadata': {
            'languages': ['eng'],
            'filetype': 'text/html',
            'url': 'https://www.cnn.com/2023/01/30/sport/empire-state-building-green-philadelphia-eagles-spt-intl/index.html',
        },
    }

    # Test with an invalid stage option (should raise ValueError)
    test_stage_type = "invalid_stageing_option"
    with pytest.raises(ValueError):
        unstructured_instance.stage_elements(
            elements=test_elements,  # type:ignore[arg-type]
            stage_type=test_stage_type,  # type:ignore[arg-type]
        )


# Test the chunk_elements method
def test_chunk_elements(unstructured_instance: UnstructuredIO):
    # Test chunking content from a url
    test_url = (
        "https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
        "philadelphia-eagles-spt-intl/index.html"
    )
    test_elements = unstructured_instance.parse_file_or_url(test_url)
    chunked_sections = unstructured_instance.chunk_elements(
        elements=test_elements,  # type:ignore[arg-type]
        chunk_type="chunk_by_title",  # type:ignore[arg-type]
    )

    assert len(chunked_sections) == 7  # Check the number of chunks
    # Test with an invalid chunk option (should raise ValueError)
    with pytest.raises(ValueError):
        unstructured_instance.chunk_elements(
            elements=test_elements,  # type:ignore[arg-type]
            chunk_type="chunk_by_invalid_option",  # type:ignore[arg-type]
        )
