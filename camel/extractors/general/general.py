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

from typing import Optional

from camel.extractors import ExtractorStrategy
from camel.logger import get_logger

logger = get_logger(__name__)


class BoxedStrategy(ExtractorStrategy):
    r"""Extracts content from \\boxed{} environments."""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract content from \\boxed{} environments.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: Content inside \\boxed{} if found, else None.
        """
        # Find the start of the boxed content
        boxed_pattern = "\\boxed{"
        if boxed_pattern not in text:
            logger.debug("No \\boxed{} content found in the response")
            return None

        start_idx = text.find(boxed_pattern) + len(boxed_pattern)
        if start_idx >= len(text):
            logger.debug("Malformed \\boxed{} (no content after opening)")
            return None

        # Use stack-based approach to handle nested braces
        stack = 1  # Start with one opening brace
        end_idx = start_idx
        escape_mode = False

        for i in range(start_idx, len(text)):
            char = text[i]

            # Handle escape sequences
            if escape_mode:
                escape_mode = False
                continue

            if char == '\\':
                escape_mode = True
                continue

            if char == '{':
                stack += 1
            elif char == '}':
                stack -= 1

            if stack == 0:  # Found the matching closing brace
                end_idx = i
                break

        # Check if we found a complete boxed expression
        if stack != 0:
            logger.debug("Unbalanced braces in \\boxed{} content")
            return None

        # Extract the content
        content = text[start_idx:end_idx].strip()
        logger.debug(f"Extracted boxed content: {content}")
        return content
