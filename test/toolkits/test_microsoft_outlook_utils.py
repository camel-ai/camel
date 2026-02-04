# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

from camel.toolkits.microsoft_outlook_toolkits import _utils


def test_is_email_valid_basic():
    assert _utils._is_email_valid("user@example.com") is True
    assert _utils._is_email_valid("user.@sub.domain.com") is True
    assert _utils._is_email_valid("invalid-email") is False
    assert _utils._is_email_valid("user@.com") is False
    assert _utils._is_email_valid("") is False
    assert _utils._is_email_valid("Name <user@example.com>") is True
    assert _utils._is_email_valid("Name <invalid-email>") is False


def test_get_invalid_emails():
    valid = ["a@b.com", "Name <c@d.com>"]
    invalid = ["invalid mail", "mail@.com", "Name <notanemail@mail>"]
    # Single list
    result = _utils._get_invalid_emails(valid + invalid)
    assert set(result) == set(invalid)
    # Multiple lists
    result = _utils._get_invalid_emails(valid, invalid)
    assert set(result) == set(invalid)
    # None and empty lists
    assert _utils._get_invalid_emails(None, []) == []
    # All valid
    assert _utils._get_invalid_emails(valid) == []
    # All invalid
    assert set(_utils._get_invalid_emails(invalid)) == set(invalid)
