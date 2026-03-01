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

"""Tests for generalized rate-limit error handling in ChatAgent."""

import openai
import pytest

from camel.utils.commons import get_rate_limit_errors


def test_get_rate_limit_errors_includes_openai():
    """OpenAI is always installed, so its RateLimitError must be present."""
    errors = get_rate_limit_errors()
    assert isinstance(errors, tuple)
    assert len(errors) >= 1
    assert openai.RateLimitError in errors


def test_get_rate_limit_errors_includes_anthropic_when_installed():
    """If anthropic is installed, its RateLimitError must be collected."""
    try:
        import anthropic
    except ImportError:
        pytest.skip("anthropic not installed")

    errors = get_rate_limit_errors()
    assert anthropic.RateLimitError in errors


def test_rate_limit_errors_are_exception_subclasses():
    """Every collected error must be an Exception subclass."""
    errors = get_rate_limit_errors()
    for err_cls in errors:
        assert issubclass(
            err_cls, Exception
        ), f"{err_cls} is not an Exception subclass"


def test_rate_limit_errors_usable_in_except():
    """The returned tuple must be usable in an ``except`` clause."""
    errors = get_rate_limit_errors()
    # Construct a fake openai RateLimitError and verify it's caught
    try:
        raise openai.RateLimitError(
            message="test",
            response=type(
                "FakeResponse",
                (),
                {
                    "status_code": 429,
                    "headers": {},
                    "request": type("R", (), {"method": "POST", "url": "/"})(),
                },
            )(),
            body=None,
        )
    except errors:
        pass  # Expected — the tuple works in except
    except Exception:
        pytest.fail("Rate limit error was not caught by the error tuple")
