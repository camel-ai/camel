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

import re
from typing import Any, Dict, Optional

from camel.extractors.base import BaseExtractor
from camel.logger import get_logger

logger = get_logger(__name__)


class BoxedTextExtractor(BaseExtractor):
    r"""Extractor for text enclosed in \boxed{} LaTeX-style notation.

    This extractor is designed to extract the final diagnosis from medical
    rationales where the diagnosis is enclosed in \boxed{} notation.
    """

    async def setup(self) -> None:
        r"""Set up the extractor."""
        await super().setup()
        # Compile regex pattern for extracting boxed text
        self._boxed_pattern = re.compile(r'\\boxed\{(.*?)\}', re.DOTALL)

    async def extract(
        self, response: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        r"""Extract text enclosed in \boxed{} from the response.

        Args:
            response (str): The response text containing \boxed{} notation.
            context (Optional[Dict[str, Any]]): Additional context for
                extraction (not used in this implementation).

        Returns:
            str: The extracted text from inside the \boxed{} notation.
                If no boxed text is found, returns an empty string.
        """
        if not response:
            logger.warning("Empty response provided to BoxedTextExtractor")
            return ""

        # Find all matches of boxed text
        matches = self._boxed_pattern.findall(response)

        # If multiple matches found, take the last one as it's likely
        # to be the final diagnosis
        if matches:
            extracted_text = matches[-1].strip()
            logger.debug(f"Extracted boxed text: {extracted_text}")
            return extracted_text

        logger.warning("No boxed text found in response")
        return ""
