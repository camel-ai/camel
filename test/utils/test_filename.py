# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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


def test_sanitize_filename_windows_reserved_full_range():
    """COM1-9 and LPT1-9 must all be guarded, not just 1-4/1-3."""
    from unittest.mock import patch as _patch

    with _patch("camel.utils.filename.platform") as mock_plat:
        mock_plat.system.return_value = "Windows"
        for i in range(1, 10):
            assert sanitize_filename(f"com{i}") == f"_com{i}"
            assert sanitize_filename(f"COM{i}") == f"_COM{i}"
            assert sanitize_filename(f"lpt{i}") == f"_lpt{i}"
            assert sanitize_filename(f"LPT{i}") == f"_LPT{i}"
        # Non-reserved names pass through
        assert sanitize_filename("com0") == "com0"
        assert sanitize_filename("lpt0") == "lpt0"
        assert sanitize_filename("console") == "console"


def test_sanitize_filename_truncation_produces_reserved():
    """Truncation must not yield a Windows reserved device name."""
    from unittest.mock import patch as _patch

    with _patch("camel.utils.filename.platform") as mock_plat:
        mock_plat.system.return_value = "Windows"
        # "COM5_extra_stuff" truncated to 4 chars -> "COM5"
        result = sanitize_filename("COM5_extra_stuff", max_length=4)
        assert result == "_COM5"
        # "LPT9abc" truncated to 4 -> "LPT9"
        result = sanitize_filename("LPT9abc", max_length=4)
        assert result == "_LPT9"
