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
from typing import Dict, Any, Optional, List
import re

from camel.extractors.base import BaseExtractor


class MedicineExtractor(BaseExtractor):
    """Medical data extractor for processing medical domain responses.
    
    This extractor can handle:
    - Patient case descriptions and symptoms
    - Diagnostic results
    - Treatment plans
    - Clinical reasoning processes
    - Medical references
    - ICD codes
    
    It supports multiple input formats:
    - Structured format with clear headers
    - Semi-structured format with partial headers
    - Free text format requiring NLP extraction
    """

    def __init__(
        self,
        cache_templates: bool = True,
        max_cache_size: int = 1000,
        extraction_timeout: float = 30.0,
        **kwargs,
    ):
        super().__init__(
            cache_templates=cache_templates,
            max_cache_size=max_cache_size,
            extraction_timeout=extraction_timeout,
            **kwargs,
        )
        
        # Define multiple pattern sets for different formats
        self._pattern_sets = {
            'standard': {
                'symptoms': [
                    r'symptoms?[：:](.*?)(?=\n|$)',
                    r'presenting complaints?[：:](.*?)(?=\n|$)',
                    r'chief complaints?[：:](.*?)(?=\n|$)',
                ],
                'diagnosis': [
                    r'diagnosis[：:](.*?)(?=\n|$)',
                    r'assessment[：:](.*?)(?=\n|$)',
                    r'impression[：:](.*?)(?=\n|$)',
                ],
                'treatment': [
                    r'treatment[：:](.*?)(?=\n|$)',
                    r'management[：:](.*?)(?=\n|$)',
                    r'plan[：:](.*?)(?=\n|$)',
                    r'intervention[：:](.*?)(?=\n|$)',
                ],
                'reasoning': [
                    r'clinical reasoning[：:](.*?)(?=\n|$)',
                    r'rationale[：:](.*?)(?=\n|$)',
                    r'analysis[：:](.*?)(?=\n|$)',
                ],
                'references': [
                    r'references?[：:](.*?)(?=\n|$)',
                    r'citations?[：:](.*?)(?=\n|$)',
                    r'sources?[：:](.*?)(?=\n|$)',
                ],
                'icd_codes': [
                    r'icd[- ]codes?[：:](.*?)(?=\n|$)',
                    r'diagnosis codes?[：:](.*?)(?=\n|$)',
                ],
                'difficulty': [
                    r'difficulty[：:](.*?)(?=\n|$)',
                    r'complexity[：:](.*?)(?=\n|$)',
                    r'level[：:](.*?)(?=\n|$)',
                ],
            },
            'free_text': {
                'symptoms': [
                    r'patient (?:presents|reports|complains of) (.*?)(?=\.|$)',
                    r'symptoms include (.*?)(?=\.|$)',
                ],
                'diagnosis': [
                    r'diagnosed with (.*?)(?=\.|$)',
                    r'likely diagnosis is (.*?)(?=\.|$)',
                ],
                'treatment': [
                    r'treated with (.*?)(?=\.|$)',
                    r'recommended treatment includes (.*?)(?=\.|$)',
                ],
            }
        }

    def _try_extract_with_patterns(
        self, text: str, patterns: List[str]
    ) -> Optional[str]:
        """Try to extract content using multiple patterns.

        Args:
            text (str): Text to extract from
            patterns (List[str]): List of regex patterns to try

        Returns:
            Optional[str]: Extracted content or None if no match found
        """
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        return None

    def _extract_from_format(
        self, text: str, format_patterns: Dict[str, List[str]]
    ) -> Dict[str, Optional[str]]:
        """Extract content using a specific format's patterns.

        Args:
            text (str): Text to extract from
            format_patterns (Dict[str, List[str]]): Format-specific patterns

        Returns:
            Dict[str, Optional[str]]: Extracted content by key
        """
        extracted = {}
        for key, patterns in format_patterns.items():
            extracted[key] = self._try_extract_with_patterns(text, patterns)
        return extracted

    async def extract(
        self, response: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract key information from medical responses.

        Args:
            response (str): Raw response text
            context (Optional[Dict[str, Any]]): Optional context including:
                - source_type: Data source type
                - specialty: Medical specialty
                - evidence_level: Level of evidence
                - format: Expected format ('standard' or 'free_text')

        Returns:
            Dict[str, Any]: Dictionary containing:
                - question: Case description
                - final_answer: Diagnostic conclusion
                - ground_truth: Treatment plan
                - chain_of_thought: Clinical reasoning
                - difficulty: Case complexity
                - raw_markdown: Original content
                - metadata: Additional medical context
        """
        if not self._is_setup:
            raise RuntimeError("Extractor must be initialized before use")
        
        if not response or not response.strip():
            raise ValueError("Empty response")

        # Try standard format first, then free text
        formats_to_try = ['standard', 'free_text']
        extracted = {}
        
        for format_name in formats_to_try:
            format_extracted = self._extract_from_format(
                response, self._pattern_sets[format_name]
            )
            # Update extracted dict with non-None values
            extracted.update({
                k: v for k, v in format_extracted.items()
                if v is not None and k not in extracted
            })

        # Extract difficulty if not already found
        if 'difficulty' not in extracted or not extracted['difficulty']:
            difficulty_patterns = self._pattern_sets['standard']['difficulty']
            extracted['difficulty'] = (
                self._try_extract_with_patterns(response, difficulty_patterns)
                or "unspecified"
            )

        # Construct return dictionary
        return {
            'question': extracted.get('symptoms', ''),
            'final_answer': extracted.get('diagnosis', ''),
            'ground_truth': extracted.get('treatment', ''),
            'chain_of_thought': extracted.get('reasoning', ''),
            'difficulty': extracted.get('difficulty', 'unspecified'),
            'raw_markdown': response,
            'metadata': {
                'references': extracted.get('references', ''),
                'icd_codes': extracted.get('icd_codes', ''),
                'specialty': context.get('specialty') if context else None,
                'evidence_level': context.get('evidence_level') if context else None,
                'format_used': next(
                    (fmt for fmt in formats_to_try if any(
                        extracted.get(k) for k in self._pattern_sets[fmt].keys()
                    )),
                    'unknown'
                ),
            }
        } 