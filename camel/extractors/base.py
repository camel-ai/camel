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

from pydantic import BaseModel, Field


class ExtractionResult(BaseModel):
    r"""Result of content extraction.

    Attributes:
        content: The extracted content in a format suitable for verification
        success: Whether the extraction was successful
        error: Optional error message if extraction failed
    """

    content: Dict[str, Any] = Field(
        default_factory=dict,
        description="The extracted content in a format suitable for"
        " verification",
    )
    success: bool = Field(
        ..., description="Whether the extraction was successful"
    )
    error: Optional[str] = Field(
        default=None, description="Optional error message if extraction failed"
    )


class BaseExtractor(ABC):
    r"""Base class for all response extractors.

    An extractor takes the response of the LLM and extracts the relevant parts,
    converting them into a format that the verifier can handle.
    """

    def __init__(self, **kwargs):
        r"""Initialize the extractor.

        Args:
            **kwargs: Additional extractor parameters
        """
        self._metadata = kwargs

    @abstractmethod
    async def extract(
        self, response: str, context: Optional[Dict[str, Any]] = None
    ) -> ExtractionResult:
        """Extract relevant parts from an LLM response.

        Args:
            response: Raw LLM response
            context: Optional context for extraction

        Returns:
            ExtractionResult containing extracted content and status

        Raises:
            ValueError: If response is empty
        """
        if not response.strip():
            raise ValueError("Empty response")
        return ExtractionResult(success=False, error="Not implemented")
