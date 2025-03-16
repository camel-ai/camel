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

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from camel.extractors.base import BaseExtractor, BaseExtractorStrategy


class DummyStrategy(BaseExtractorStrategy):
    r"""A dummy strategy that just returns the input text."""

    async def extract(self, text: str) -> Optional[str]:
        return text


class TestExtractor(BaseExtractor):
    r"""Concrete implementation of BaseExtractor for testing."""

    def __init__(
        self,
        cache_templates: bool = True,
        max_cache_size: int = 1000,
        extraction_timeout: float = 30.0,
        batch_size: int = 10,
        **kwargs,
    ):
        pipeline: List[List[BaseExtractorStrategy]] = [[DummyStrategy()]]
        super().__init__(
            pipeline=pipeline,
            cache_templates=cache_templates,
            max_cache_size=max_cache_size,
            extraction_timeout=extraction_timeout,
            batch_size=batch_size,
            **kwargs,
        )

    async def extract(
        self, response: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        r"""Simple implementation that returns the response with a prefix."""
        if not self._is_setup:
            raise RuntimeError("Extractor not initialized")
        if not response or not response.strip():
            raise ValueError("Empty or whitespace-only response")

        prefix = "Extracted: "
        if context and "prefix" in context:
            prefix = context["prefix"]

        return f"{prefix}{response}"


@pytest.fixture
def test_extractor():
    r"""Fixture providing a TestExtractor instance."""
    return TestExtractor(
        cache_templates=True,
        max_cache_size=100,
        extraction_timeout=10.0,
        batch_size=5,
    )


def test_extractor_init():
    r"""Test BaseExtractor initialization with various parameters."""
    extractor = TestExtractor(
        cache_templates=False,
        max_cache_size=500,
        extraction_timeout=15.0,
        batch_size=20,
        custom_param="value",
    )
    assert extractor._metadata["cache_templates"] is False
    assert extractor._metadata["max_cache_size"] == 500
    assert extractor._metadata["extraction_timeout"] == 15.0
    assert extractor._metadata["batch_size"] == 20
    assert extractor._metadata["custom_param"] == "value"


@pytest.mark.asyncio
async def test_extractor_setup(test_extractor):
    r"""Test the setup method of BaseExtractor."""
    assert test_extractor._is_setup is False

    await test_extractor.setup()
    assert test_extractor._is_setup is True
    assert hasattr(test_extractor, "_template_cache")

    await test_extractor.setup()
    assert test_extractor._is_setup is True

    await test_extractor.cleanup()


@pytest.mark.asyncio
async def test_extractor_cleanup(test_extractor):
    r"""Test the cleanup method of BaseExtractor."""
    await test_extractor.setup()
    assert test_extractor._is_setup is True

    await test_extractor.cleanup()
    assert test_extractor._is_setup is False

    await test_extractor.cleanup()
    assert test_extractor._is_setup is False


@pytest.mark.asyncio
async def test_extractor_cleanup_with_errors():
    r"""Test cleanup handling when errors occur."""
    extractor = TestExtractor()
    await extractor.setup()

    # Mock _template_cache.clear to raise an exception
    extractor._template_cache = MagicMock()
    extractor._template_cache.clear.side_effect = Exception("Mock error")

    with pytest.raises(RuntimeError):
        await extractor.cleanup()

    assert extractor._is_setup is False


@pytest.mark.asyncio
async def test_extractor_context_manager():
    r"""Test using the extractor as an async context manager."""
    async with TestExtractor() as extractor:
        assert extractor._is_setup is True
        result = await extractor.extract("test")
        assert result == "Extracted: test"

    assert extractor._is_setup is False


@pytest.mark.asyncio
async def test_extractor_context_manager_with_exception():
    r"""Test context manager handles exceptions properly."""
    try:
        async with TestExtractor() as extractor:
            assert extractor._is_setup is True
            raise ValueError("Test exception")
    except ValueError:
        # The exception should be propagated, but cleanup should still happen
        assert extractor._is_setup is False


@pytest.mark.asyncio
async def test_extract_method(test_extractor):
    r"""Test the extract method of the concrete implementation."""
    await test_extractor.setup()

    # Basic extraction
    result = await test_extractor.extract("Hello World")
    assert result == "Extracted: Hello World"

    # Extraction with context
    result = await test_extractor.extract(
        "Hello World", context={"prefix": "Custom: "}
    )
    assert result == "Custom: Hello World"

    await test_extractor.cleanup()


@pytest.mark.asyncio
async def test_extract_with_empty_input(test_extractor):
    r"""Test extract method with empty input."""
    await test_extractor.setup()

    with pytest.raises(ValueError, match="Empty or whitespace-only response"):
        await test_extractor.extract("")

    with pytest.raises(ValueError, match="Empty or whitespace-only response"):
        await test_extractor.extract("   ")

    await test_extractor.cleanup()
