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
import os
import platform
from urllib.parse import urlparse

import pytest

from camel.utils.filename import (
    MAX_FILENAME_LENGTH,
    WINDOWS_RESERVED,
    sanitize_filename,
)

on_windows = pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Reserved device names only apply on Windows.",
)


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


@on_windows
@pytest.mark.parametrize(
    "name",
    [
        # These four were already covered by the set.
        "con",
        "nul",
        "com1",
        "lpt3",
        # These were missing from it, so they were returned unchanged.
        "com5",
        "com9",
        "lpt4",
        "lpt9",
        "COM7",
    ],
)
def test_sanitize_filename_prefixes_every_reserved_device_name(name):
    r"""Windows reserves COM1-COM9 and LPT1-LPT9, not just the first few."""
    result = sanitize_filename(name)
    assert result == f"_{name}"
    assert result.upper() not in WINDOWS_RESERVED


@on_windows
@pytest.mark.parametrize(
    ("name", "max_length"),
    [
        # Truncating "nullify" to 3 produced "nul", the null device: writing
        # there succeeds and discards the data.
        ("nullify", 3),
        ("CONSOLE", 3),
        ("printer", 3),
        ("auxiliary", 3),
        ("computer", 4),
        ("lpt1234", 4),
    ],
)
def test_sanitize_filename_truncation_cannot_produce_a_reserved_name(
    name, max_length
):
    r"""The length cut must not create the very name the check rejects."""
    result = sanitize_filename(name, max_length=max_length)
    assert result.upper() not in WINDOWS_RESERVED
    assert len(result) <= max_length


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("report ", "report"),
        ("report  ", "report"),
        ("a b ", "a b"),
    ],
)
def test_sanitize_filename_strips_trailing_spaces(name, expected):
    r"""A trailing space is dropped by the filesystem, so the returned name
    would not be the name on disk."""
    assert sanitize_filename(name) == expected


def test_sanitize_filename_never_exceeds_max_length_when_prefixed():
    r"""Prefixing a reserved name grows it, so max_length must still hold."""
    result = sanitize_filename("con", max_length=3)
    assert len(result) <= 3
    assert result.upper() not in WINDOWS_RESERVED


def test_sanitize_filename_result_is_the_name_on_disk(tmp_path):
    r"""The returned name must round-trip: a file created under it has to
    appear in the directory listing under exactly that name and read back."""
    for name, kwargs in [
        ("nullify", {"max_length": 3}),
        ("com5", {}),
        ("lpt9", {}),
        ("report ", {}),
        ("con", {}),
        ("cafe.txt", {}),
    ]:
        target = tmp_path / str(len(os.listdir(tmp_path)))
        target.mkdir()
        sanitized = sanitize_filename(name, **kwargs)
        path = target / sanitized
        path.write_text("payload", encoding="utf-8")

        assert os.listdir(target) == [sanitized], (
            f"sanitize_filename({name!r}, {kwargs}) returned {sanitized!r} "
            f"but the directory contains {os.listdir(target)!r}"
        )
        assert path.read_text(encoding="utf-8") == "payload"
