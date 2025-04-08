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
from typing import Optional

from camel.extractors.base import BaseExtractorStrategy
from camel.logger import get_logger

logger = get_logger(__name__)


class BoxedStrategy(BaseExtractorStrategy):
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


class PythonListStrategy(BaseExtractorStrategy):
    r"""Extracts and normalizes Python lists."""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract and normalize a Python list.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: Normalized list as a string if found, else None.
        """

        text = text.strip()
        if not (text.startswith('[') and text.endswith(']')):
            logger.debug("Content is not a list format (missing brackets)")
            return None

        try:
            # Fix any escaped quotes before parsing
            fixed_content = text.replace('\\"', '"')
            parsed = ast.literal_eval(fixed_content)
            if isinstance(parsed, list):
                # Sort the list for normalization
                sorted_list = sorted(parsed, key=lambda x: str(x))
                return repr(sorted_list)
            else:
                logger.debug(f"Content is not a list, got {type(parsed)}")
                return None
        except (SyntaxError, ValueError) as e:
            logger.debug(f"Failed to parse as Python list: {e}")
            return None


class PythonDictStrategy(BaseExtractorStrategy):
    r"""Extracts and normalizes Python dictionaries."""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract and normalize a Python dictionary.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: Normalized dictionary as a string, else None.
        """

        text = text.strip()
        if not (text.startswith('{') and text.endswith('}')):
            logger.debug("Content is not a dictionary format (missing braces)")
            return None

        try:
            # Fix any escaped quotes before parsing
            fixed_content = text.replace('\\"', '"')
            parsed = ast.literal_eval(fixed_content)
            if isinstance(parsed, dict):
                # Sort the dictionary items for normalization
                sorted_dict = dict(
                    sorted(parsed.items(), key=lambda x: str(x[0]))
                )
                return repr(sorted_dict)
            else:
                logger.debug(
                    f"Content is not a dictionary, got {type(parsed)}"
                )
                return None
        except (SyntaxError, ValueError) as e:
            logger.debug(f"Failed to parse as Python dictionary: {e}")
            return None


class PythonSetStrategy(BaseExtractorStrategy):
    r"""Extracts and normalizes Python sets."""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract and normalize a Python set.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: Normalized set as a string if found, else None.
        """

        text = text.strip()
        # Check for set syntax: {1, 2, 3} or set([1, 2, 3])
        if not (
            (text.startswith('{') and text.endswith('}'))
            or (text.startswith('set(') and text.endswith(')'))
        ):
            logger.debug("Content is not a set format")
            return None

        try:
            # Fix any escaped quotes before parsing
            fixed_content = text.replace('\\"', '"')
            parsed = ast.literal_eval(fixed_content)
            if isinstance(parsed, set):
                # Sort the set elements for normalization
                sorted_set = sorted(parsed, key=lambda x: str(x))
                return repr(set(sorted_set))
            else:
                logger.debug(f"Content is not a set, got {type(parsed)}")
                return None
        except (SyntaxError, ValueError) as e:
            logger.debug(f"Failed to parse as Python set: {e}")
            return None


class PythonTupleStrategy(BaseExtractorStrategy):
    r"""Extracts and normalizes Python tuples."""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract and normalize a Python tuple.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: Normalized tuple as a string if found, else None.
        """

        text = text.strip()
        # Check for tuple syntax: (1, 2, 3) or (1,)
        if not (text.startswith('(') and text.endswith(')')):
            logger.debug("Content is not a tuple format (missing parentheses)")
            return None

        try:
            # Fix any escaped quotes before parsing
            fixed_content = text.replace('\\"', '"')
            parsed = ast.literal_eval(fixed_content)
            if isinstance(parsed, tuple):
                # Sort the tuple elements for normalization
                sorted_tuple = tuple(sorted(parsed, key=lambda x: str(x)))
                return repr(sorted_tuple)
            else:
                logger.debug(f"Content is not a tuple, got {type(parsed)}")
                return None
        except (SyntaxError, ValueError) as e:
            logger.debug(f"Failed to parse as Python tuple: {e}")
            return None
