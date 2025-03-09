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

import ast
import re
from typing import Optional

from camel.extractors.base import Extractor, ExtractorStrategy
from camel.logger import get_logger

logger = get_logger(__name__)


class BoxedListStrategy(ExtractorStrategy):
    r"""Extracts list content from \\boxed{}."""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract list content from \\boxed{} environments and normalize it.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: Normalized list as a string if found, else None.
        """
        # Look for \boxed{...} pattern
        boxed_pattern = r'\\boxed\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        matches = re.findall(boxed_pattern, text)

        if not matches:
            logger.debug("No \\boxed{} content found in the response")
            return None

        for content in matches:
            content = content.strip()

            if content.startswith('[') and content.endswith(']'):
                try:
                    # Fix any escaped quotes before parsing
                    fixed_content = content.replace('\\"', '"')
                    parsed_list = ast.literal_eval(fixed_content)
                    if isinstance(parsed_list, list):
                        # Sort the list for normalization
                        sorted_list = sorted(parsed_list, key=lambda x: str(x))
                        return repr(sorted_list)
                except (SyntaxError, ValueError):
                    logger.debug("Failed to parse as Python list")

            logger.debug("Content is not a valid Python list")
            return None

        logger.debug("Failed to extract list from \\boxed{} content")
        return None


class ListExtractor(Extractor):
    r"""Extractor for normalizing lists from \\boxed{} environments."""

    def __init__(
        self,
        _cache_templates=True,
        max_cache_size=5000,
        extraction_timeout=60.0,
        _batch_size=20,
        _monitoring_interval=10.0,
        _cpu_threshold=90.0,
        _memory_threshold=90.0,
    ):
        super().__init__(
            _cache_templates=_cache_templates,
            max_cache_size=max_cache_size,
            extraction_timeout=extraction_timeout,
            _batch_size=_batch_size,
            _monitoring_interval=_monitoring_interval,
            _cpu_threshold=_cpu_threshold,
            _memory_threshold=_memory_threshold,
        )

    async def setup(self) -> None:
        r"""Set up the list extractor with the boxed list strategy."""
        await super().setup()

        self.add_strategy(BoxedListStrategy(), 0)

        logger.info("ListExtractor initialized with BoxedListStrategy")

    async def extract(self, text: str) -> str:
        r"""Extract and normalize a list from text.

        This method overrides the base extract method to ensure it always
        returns a string representation of a list, never None.

        Args:
            text (str): Text containing a list to extract and normalize

        Returns:
            str: String representation of the normalized list,
                 or "[]" if extraction fails
        """
        if text is None:
            logger.debug("Input text is None, returning empty list string")
            return "[]"

        result = await super().extract(text)
        if result is None:
            logger.debug("No list extracted, returning empty list string")
            return "[]"
        return result
