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

import os

import pytest

from examples.file_io.unstructured_modules_example import (
    chunk_url_content_example,
    clean_text_example,
    extract_data_example,
    parse_file_example,
    parse_url_example,
    stage_data_example,
)


@pytest.fixture
def sample_url():
    return ("https://www.cnn.com/2023/01/30/sport/empire-state-building-green-"
            "philadelphia-eagles-spt-intl/index.html")


@pytest.fixture
def sample_text():
    return "Some dirty text â€™ with extra spaces and – dashes."


@pytest.fixture
def sample_email_text():
    return "Contact me at example@email.com."


# Define test cases


def test_parse_file_example():
    # Setup: ensure any pre-existing 'mydoc.docx' is removed
    if os.path.exists("mydoc.txt"):
        os.remove("mydoc.txt")

    # Execution: call the function
    result = parse_file_example()

    # Assertion: check if the result is as expected
    expected = [
        "Important Analysis", "Here is my first thought.",
        "Here is my second thought."
    ]
    assert result == expected, f"Expected {expected}, got {result}"

    # Cleanup: remove the created file after the test
    if os.path.exists("mydoc.txt"):
        os.remove("mydoc.txt")


def test_parse_url_example(sample_url):
    content = parse_url_example()
    assert isinstance(content, str)
    assert len(content) > 0


def test_clean_text_example(sample_text):
    cleaned_text = clean_text_example()
    assert isinstance(cleaned_text, str)
    assert cleaned_text == "Some dirty text  with extra spaces and   dashes."


def test_extract_data_example(sample_email_text):
    extracted_data = extract_data_example()
    assert isinstance(extracted_data, list)
    assert extracted_data == ["example@email.com"]


def test_stage_data_example(sample_url):
    staged_data = stage_data_example()
    assert isinstance(staged_data, dict)
    assert staged_data['rows'][0] == {
        'data': {
            'type': 'UncategorizedText',
            'element_id': 'e78902d05b0cb1e4c38fc7a79db450d5',
            'text': 'CNN\n        \xa0—'
        },
        'metadata': {
            'filetype':
            'text/html',
            'languages': ['eng'],
            'page_number':
            1,
            'url':
            'https://www.cnn.com/2023/01/30/sport/'
            'empire-state-building-green-philadelphia-eagles-spt-'
            'intl/index.html',
            'emphasized_text_contents': ['CNN'],
            'emphasized_text_tags': ['span']
        }
    }


def test_chunk_url_content_example(sample_url):
    chunked_sections = chunk_url_content_example()
    assert len(chunked_sections) == 7
