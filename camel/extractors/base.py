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

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseExtractor(ABC):
    r"""Base class for all response extractors.

    An extractor takes the response and extracts the relevant parts,
    converting them into a format that the verifier can handle.
    """

    def __init__(self, **kwargs):
        r"""Initialize the extractor.

        Args:
            **kwargs: Additional extractor parameters.
        """
        self._metadata = kwargs
        self._is_initialized = False

    @abstractmethod
    async def cleanup(self) -> None:
        r"""Clean up extractor resources.

        This method handles cleanup of resources and resets the extractor state
        It ensures:
        1. All resources are properly released
        2. State is reset to initial
        3. Cleanup happens even if errors occur
        """
        if not self._is_initialized:
            return

        try:
            # Clear any cached data
            self._metadata = {}

        finally:
            # Always mark as uninitialized, even if cleanup fails
            self._is_initialized = False

    @abstractmethod
    async def extract(
        self, response: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        r"""Extract relevant parts from a response.

        Args:
            response: Raw response.
            context: Optional context for extraction.

        Returns:
            Dictionary containing extracted content.

        Raises:
            ValueError: If response is empty.
        """
        if not response.strip():
            raise ValueError("Empty response")
        raise NotImplementedError("Subclasses must implement extract()")
