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
from unittest.mock import MagicMock

import pytest
from openai import RateLimitError as OpenAIRateLimitError

from camel.agents.chat_agent import _RATE_LIMIT_ERRORS


def test_rate_limit_errors_includes_openai():
    """Verify OpenAI's RateLimitError is always in the collection."""
    assert OpenAIRateLimitError in _RATE_LIMIT_ERRORS


def test_rate_limit_errors_includes_anthropic_when_installed():
    """If anthropic SDK is installed, its RateLimitError should be included."""
    try:
        from anthropic import RateLimitError as AnthropicRateLimitError

        assert AnthropicRateLimitError in _RATE_LIMIT_ERRORS
    except ImportError:
        pytest.skip("anthropic SDK not installed")


def test_rate_limit_errors_catches_openai():
    """Verify the tuple works in an except clause with OpenAI errors."""
    caught = False
    try:
        raise OpenAIRateLimitError(
            "rate limit",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
    except _RATE_LIMIT_ERRORS:
        caught = True
    assert caught, "OpenAI RateLimitError should be caught by _RATE_LIMIT_ERRORS"


def test_rate_limit_errors_catches_anthropic():
    """Verify the tuple catches Anthropic rate limit errors when SDK is installed."""
    try:
        from anthropic import RateLimitError as AnthropicRateLimitError
    except ImportError:
        pytest.skip("anthropic SDK not installed")

    caught = False
    try:
        raise AnthropicRateLimitError(
            "rate limit",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
    except _RATE_LIMIT_ERRORS:
        caught = True
    assert caught, "Anthropic RateLimitError should be caught by _RATE_LIMIT_ERRORS"
