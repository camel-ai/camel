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
from typing import Any, Dict, Optional

from camel.extractors import ExtractorStrategy
from camel.logger import get_logger

logger = get_logger(__name__)


class GraphDictionaryStrategy(ExtractorStrategy):
    r"""Extracts and normalizes graph dictionaries"""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract and normalize a graph dictionary representation.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: Normalized dictionary as a string, else None.
        """

        text = text.strip()

        # Look for dictionary patterns with graph-like structure
        if not (text.startswith('{') and text.endswith('}')):
            logger.debug("Content is not a dictionary format (missing braces)")
            return None

        try:
            # Fix any escaped quotes before parsing
            fixed_content = text.replace('\\"', '"')
            parsed = ast.literal_eval(fixed_content)

            if isinstance(parsed, dict):
                # For empty dictionaries, return as is
                if not parsed:
                    return repr(parsed)

                # Check if it's a graph-like structure
                # We'll be more lenient here - if it's a dictionary,
                # we'll try to normalize it
                sorted_dict: Dict[Any, Any] = {}
                for k in sorted(parsed.keys(), key=lambda x: str(x)):
                    if isinstance(parsed[k], dict):
                        sorted_dict[k] = dict(
                            sorted(parsed[k].items(), key=lambda x: str(x[0]))
                        )
                    elif isinstance(parsed[k], list):
                        sorted_dict[k] = sorted(
                            parsed[k], key=lambda x: str(x)
                        )
                    else:
                        # Just copy the value if it's not a dict or list
                        sorted_dict[k] = parsed[k]

                return repr(sorted_dict)
            else:
                logger.debug(
                    f"Content is not a dictionary, got {type(parsed)}"
                )
                return None
        except (SyntaxError, ValueError) as e:
            logger.debug(f"Failed to parse as graph dictionary: {e}")
            return None


class GraphListStrategy(ExtractorStrategy):
    r"""Extracts and normalizes lists of nodes, edges, or graph partitions."""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract and normalize a graph list representation.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: Normalized list as a string if found, else None.
        """

        text = text.strip()

        # Check for list patterns
        if not (text.startswith('[') and text.endswith(']')):
            logger.debug("Content is not a list format (missing brackets)")
            return None

        try:
            # Fix any escaped quotes before parsing
            fixed_content = text.replace('\\"', '"')
            parsed = ast.literal_eval(fixed_content)

            if isinstance(parsed, list):
                # For empty lists, return as is
                if not parsed:
                    return repr(parsed)

                # Check if it's a list of lists (like partitions or edge lists)
                if all(isinstance(item, list) for item in parsed):
                    # Sort each sublist and then sort the main list
                    sorted_list = [
                        sorted(sublist, key=lambda x: str(x))
                        for sublist in parsed
                    ]
                    sorted_list.sort(key=lambda x: (len(x), str(x)))
                    return repr(sorted_list)
                else:
                    # Simple list of nodes
                    return repr(sorted(parsed, key=lambda x: str(x)))
            else:
                logger.debug(f"Content is not a list, got {type(parsed)}")
                return None
        except (SyntaxError, ValueError) as e:
            logger.debug(f"Failed to parse as graph list: {e}")
            return None


class GraphNodeListStrategy(ExtractorStrategy):
    r"""Extracts lists of node names, especially for
    text-based graph problems."""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract a list of node names from text.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: Normalized list of node names if found, else None.
        """

        text = text.strip()

        # Handle empty or no nodes case
        if text.lower() in ('no nodes', 'none'):
            return '[]'

        # Remove trailing period if present
        if text.endswith('.'):
            text = text[:-1].strip()

        # If it's a single word (like "Eric"), wrap it in a list
        if re.match(r'^[a-zA-Z0-9_]+$', text):
            return repr([text])

        # Split by commas and normalize
        nodes = [node.strip() for node in text.split(',')]

        # Filter out empty strings
        nodes = [node for node in nodes if node]

        if not nodes:
            logger.debug("No valid node names found")
            return None

        # Sort alphabetically
        nodes.sort()

        return repr(nodes)


class MathValueStrategy(ExtractorStrategy):
    r"""Extracts mathematical values including special values like 'inf'."""

    async def extract(self, text: str) -> Optional[str]:
        r"""Extract mathematical values including infinity.

        Args:
            text (str): The input text to process.

        Returns:
            Optional[str]: The extracted value as a string if found, else None.
        """
        if text is None:
            return None

        text = text.strip()

        # Handle special case for infinity
        if text.lower() in ('inf', 'infinity', '∞'):
            return 'inf'

        # Try to parse as a number
        try:
            value = ast.literal_eval(text)
            if isinstance(value, (int, float)):
                return str(value)
            else:
                logger.debug(
                    f"Content is not a numeric value, got {type(value)}"
                )
                return None
        except (SyntaxError, ValueError):
            # Check if it's a single word/token that might be a special value
            if re.match(r'^[a-zA-Z0-9_]+$', text):
                return text

            logger.debug(f"Failed to parse as mathematical value: {text}")
            return None
