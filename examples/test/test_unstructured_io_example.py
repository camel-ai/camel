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

import os

import pytest

from examples.loaders.unstructured_io_example import (
    chunk_url_content_example,
    clean_text_example,
    extract_data_example,
    parse_file_example,
    parse_url_example,
    stage_data_example,
)


@pytest.fixture
def sample_url():
    return (
        "https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
        "philadelphia-eagles-spt-intl/index.html"
    )


@pytest.fixture
def sample_dirty_text():
    return "Some dirty text â€™ with extra spaces and – dashes."  # noqa: RUF001


@pytest.fixture
def sample_email_text():
    return "Contact me at example@email.com."


# Define test cases


def test_parse_file_example():
    # Setup: ensure any pre-existing 'mydoc.docx' is removed
    if os.path.exists("mydoc.txt"):
        os.remove("mydoc.txt")

    # Execution: call the function
    content = parse_file_example()

    # Assertion: check if the result is as expected
    expected_string = (
        "Important Analysis\n\nHere is my first "
        "thought.\n\nHere is my second thought."
    )
    assert content == expected_string

    # Cleanup: remove the created file after the test
    if os.path.exists("mydoc.txt"):
        os.remove("mydoc.txt")


def test_parse_url_example(sample_url):
    content = parse_url_example(sample_url)
    assert isinstance(content, str)
    assert len(content) > 0


def test_clean_text_example(sample_dirty_text):
    cleaned_text = clean_text_example(sample_dirty_text)
    assert isinstance(cleaned_text, str)
    assert cleaned_text == "Some dirty text with extra spaces and dashes."


def test_extract_data_example(sample_email_text):
    extracted_data = extract_data_example(sample_email_text)
    assert isinstance(extracted_data, list)
    assert extracted_data == ["example@email.com"]


def test_stage_data_example(sample_url):
    staged_data = stage_data_example(sample_url)
    assert isinstance(staged_data, dict)
    assert staged_data['rows'][0] == {
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


def test_chunk_url_content_example(sample_url):
    chunked_sections = chunk_url_content_example(sample_url)
    assert len(chunked_sections) == 7
