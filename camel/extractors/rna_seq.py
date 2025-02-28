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

import json
import re
from typing import Any, Dict, List, Optional, Pattern, Tuple

from camel.extractors.base import BaseExtractor
from camel.logger import get_logger

logger = get_logger(__name__)


class RNASeqExtractor(BaseExtractor):
    r"""Extractor for RNA-seq analysis outputs.
    
    This extractor parses RNA-seq analysis outputs and extracts:
    1. Differential expression results
    2. Pathway enrichment analysis
    3. Quality control metrics
    4. Chain-of-thought reasoning steps
    5. Experimental design information
    """

    def __init__(
        self,
        extraction_patterns: Optional[Dict[str, Pattern]] = None,
        cache_templates: bool = True,
        max_cache_size: int = 1000,
        extraction_timeout: float = 30.0,
        **kwargs,
    ):
        r"""Initialize the RNA-seq extractor.

        Args:
            extraction_patterns: Custom regex patterns for extraction
            cache_templates: Whether to cache extraction templates
            max_cache_size: Maximum number of templates to cache
            extraction_timeout: Maximum time for extraction in seconds
            **kwargs: Additional extractor parameters
        """
        super().__init__(
            cache_templates=cache_templates,
            max_cache_size=max_cache_size,
            extraction_timeout=extraction_timeout,
            **kwargs,
        )
        self._extraction_patterns = extraction_patterns or self._get_default_patterns()

    def _get_default_patterns(self) -> Dict[str, Pattern]:
        r"""Get default extraction patterns for RNA-seq analysis.

        Returns:
            Dictionary of regex patterns for different components
        """
        return {
            "differential_expression": re.compile(
                r"```(?:json|python)?\s*([\s\S]*?differential[\s\S]*?)```",
                re.IGNORECASE
            ),
            "pathway_analysis": re.compile(
                r"```(?:json|python)?\s*([\s\S]*?pathway[\s\S]*?)```",
                re.IGNORECASE
            ),
            "quality_control": re.compile(
                r"```(?:json|python)?\s*([\s\S]*?quality[\s\S]*?)```",
                re.IGNORECASE
            ),
            "reasoning": re.compile(
                r"(Analysis steps:|Reasoning:|Chain of thought:)[\s\S]*?(\n\n|$)",
                re.IGNORECASE
            ),
            "experimental_design": re.compile(
                r"```(?:json|python)?\s*([\s\S]*?experiment[\s\S]*?)```",
                re.IGNORECASE
            ),
        }

    async def extract(
        self, response: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        r"""Extract RNA-seq analysis components from response.

        Args:
            response: Raw response from agent generation
            context: Optional context for extraction

        Returns:
            Dictionary containing extracted RNA-seq analysis components

        Raises:
            ValueError: If response is empty or invalid
            RuntimeError: If extractor is not initialized
        """
        if not self._is_setup:
            raise RuntimeError(
                f"{self.__class__.__name__} must be initialized "
                "before extraction"
            )
        if not response or not response.strip():
            raise ValueError("Empty or whitespace-only response")

        # Initialize extraction result
        extraction_result = {
            "differential_expression": {},
            "pathway_analysis": {},
            "quality_control": {},
            "reasoning": "",
            "experimental_design": {},
            "raw_markdown": response,
        }

        # Extract each component using patterns
        for component, pattern in self._extraction_patterns.items():
            match = pattern.search(response)
            if match:
                if component == "reasoning":
                    extraction_result[component] = match.group(0).strip()
                else:
                    try:
                        # Try to parse as JSON
                        json_content = match.group(1).strip()
                        extraction_result[component] = json.loads(json_content)
                    except (json.JSONDecodeError, IndexError):
                        # Fall back to Python dict parsing
                        try:
                            extraction_result[component] = self._parse_python_dict(
                                match.group(1).strip()
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to parse {component} content: {e}"
                            )

        # Extract question and final answer if available
        question_match = re.search(
            r"(Question:|Problem:)\s*([^\n]+)", response, re.IGNORECASE
        )
        if question_match:
            extraction_result["question"] = question_match.group(2).strip()

        answer_match = re.search(
            r"(Final Answer:|Result:|Conclusion:)\s*([^\n]+)",
            response,
            re.IGNORECASE,
        )
        if answer_match:
            extraction_result["final_answer"] = answer_match.group(2).strip()

        # Add context information if provided
        if context:
            extraction_result["context"] = context

        return extraction_result

    def _parse_python_dict(self, text: str) -> Dict[str, Any]:
        r"""Parse Python dictionary-like text into a dictionary.

        Args:
            text: Python dictionary-like text

        Returns:
            Parsed dictionary
        """
        # Simple parsing for demonstration - in production would use safer methods
        try:
            # Replace Python syntax with JSON syntax
            json_like = text.replace("'", "\"").replace("True", "true").replace("False", "false").replace("None", "null")
            return json.loads(json_like)
        except Exception:
            # Fallback to empty dict if parsing fails
            return {}

    async def extract_batch(
        self, responses: List[str], contexts: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        r"""Extract RNA-seq analysis components from multiple responses.

        Args:
            responses: List of raw responses from agent generation
            contexts: Optional list of contexts for extraction

        Returns:
            List of dictionaries containing extracted RNA-seq analysis components
        """
        if not self._is_setup:
            raise RuntimeError(
                f"{self.__class__.__name__} must be initialized "
                "before batch extraction"
            )

        if not contexts:
            contexts = [None] * len(responses)

        results = []
        for response, context in zip(responses, contexts):
            try:
                result = await self.extract(response, context)
                results.append(result)
            except Exception as e:
                logger.error(f"Error extracting response: {e}")
                # Add empty result to maintain alignment with input
                results.append({
                    "differential_expression": {},
                    "pathway_analysis": {},
                    "quality_control": {},
                    "reasoning": "",
                    "experimental_design": {},
                    "raw_markdown": response,
                    "error": str(e),
                })

        return results