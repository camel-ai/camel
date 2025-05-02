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
from urllib.parse import urlparse

import pytest

from camel.utils.filename import MAX_FILENAME_LENGTH, sanitize_filename


def test_sanitize_filename_basic():
    """Test basic filename sanitization."""
    assert sanitize_filename("test.txt") == "test_txt"
    path = urlparse("https://example.com/my_file_name").path
    assert sanitize_filename(path) == "my_file_name"
    path = urlparse("https://example.com/file:name").path
    assert sanitize_filename(path) == "file_name"
    path = urlparse("https://example.com/file<name").path
    assert sanitize_filename(path) == "file_name"
    path = urlparse("https://example.com/file>name").path
    assert sanitize_filename(path) == "file_name"
    path = urlparse("https://example.com/file|name").path
    assert sanitize_filename(path) == "file_name"
    path = urlparse("https://example.com/file\"name").path


def test_sanitize_filename_unicode_normalization():
    """Test Unicode normalization (NFKD) and ASCII conversion."""
    # Test with accented characters
    path = urlparse("https://example.com/café.txt").path
    assert sanitize_filename(path) == "cafe_txt"
    path = urlparse("https://example.com/naïve.txt").path
    assert sanitize_filename(path) == "naive_txt"
    path = urlparse("https://example.com/résumé.pdf").path
    assert sanitize_filename(path) == "resume_pdf"

    # Test with special Unicode characters
    path = urlparse("https://example.com/file☕.txt").path
    assert sanitize_filename(path) == "file_txt"
    path = urlparse("https://example.com/file🎉.txt").path
    assert sanitize_filename(path) == "file_txt"


def test_sanitize_filename_special_characters():
    """Test handling of special characters."""
    path = urlparse("https://example.com/file/name.txt").path
    assert sanitize_filename(path) == "file_name_txt"
    path = urlparse("https://example.com/file:name.txt").path
    assert sanitize_filename(path) == "file_name_txt"
    path = urlparse("https://example.com/file\\name.txt").path
    assert sanitize_filename(path) == "file_name_txt"
    path = urlparse("https://example.com/file*name.txt").path
    assert sanitize_filename(path) == "file_name_txt"
    path = urlparse("https://example.com/file<name.txt").path
    assert sanitize_filename(path) == "file_name_txt"
    path = urlparse("https://example.com/file>name.txt").path
    assert sanitize_filename(path) == "file_name_txt"
    path = urlparse("https://example.com/file|name.txt").path
    assert sanitize_filename(path) == "file_name_txt"
    path = urlparse("https://example.com/file\"name.txt").path
    assert sanitize_filename(path) == "file_name_txt"


def test_sanitize_filename_multiple_special_chars():
    """Test handling of multiple consecutive special characters."""
    path = urlparse("https://example.com/file//name.txt").path
    assert sanitize_filename(path) == "file_name_txt"
    path = urlparse("https://example.com/file\\\\name.txt").path
    assert sanitize_filename(path) == "file_name_txt"
    path = urlparse("https://example.com/file::name.txt").path
    assert sanitize_filename(path) == "file_name_txt"
    path = urlparse("https://example.com/file**name.txt").path
    assert sanitize_filename(path) == "file_name_txt"


def test_sanitize_filename_leading_trailing():
    """Test handling of leading and trailing special characters."""
    path = urlparse("https://example.com/_file.txt").path
    assert sanitize_filename(path) == "file_txt"
    path = urlparse("https://example.com/file.txt_").path
    assert sanitize_filename(path) == "file_txt"
    path = urlparse("https://example.com/_file.txt_").path
    assert sanitize_filename(path) == "file_txt"
    path = urlparse("https://example.com/__file.txt__").path
    assert sanitize_filename(path) == "file_txt"


def test_sanitize_filename_empty():
    """Test handling of empty input."""
    assert sanitize_filename("") == "index"
    assert sanitize_filename("", default="default") == "default"


def test_sanitize_filename_max_length():
    """Test maximum length handling."""
    long_name = "a" * (MAX_FILENAME_LENGTH + 10)
    assert len(sanitize_filename(long_name)) == MAX_FILENAME_LENGTH

    # Test with custom max_length
    assert len(sanitize_filename("test.txt", max_length=5)) == 5


def test_sanitize_filename_invalid_max_length():
    """Test invalid max_length parameter."""
    with pytest.raises(ValueError):
        sanitize_filename("test.txt", max_length=0)
    with pytest.raises(ValueError):
        sanitize_filename("test.txt", max_length=-1)
