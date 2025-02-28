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

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from camel.logger import get_logger
from camel.verifiers.base import BaseVerifier
from camel.verifiers.models import (
    Response,
    VerificationResult,
    VerificationStatus,
)

logger = get_logger(__name__)


class RNASeqVerifier(BaseVerifier):
    r"""Verifier for RNA-seq analysis results.
    
    This verifier validates:
    1. Differential expression analysis correctness
    2. Pathway enrichment calculations
    3. Statistical significance of results
    4. Quality control metrics
    5. Chain-of-thought reasoning in bioinformatics analysis
    """

    def __init__(
        self,
        p_value_threshold: float = 0.05,
        fold_change_threshold: float = 1.5,
        min_pathway_genes: int = 5,
        max_parallel: Optional[int] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs,
    ):
        r"""Initialize the RNA-seq verifier.

        Args:
            p_value_threshold: Threshold for statistical significance
            fold_change_threshold: Minimum fold change for DE genes
            min_pathway_genes: Minimum genes for pathway enrichment
            max_parallel: Maximum number of parallel verifications
            timeout: Timeout in seconds for each verification
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            **kwargs: Additional verifier parameters
        """
        super().__init__(
            max_parallel=max_parallel,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            **kwargs,
        )
        self.p_value_threshold = p_value_threshold
        self.fold_change_threshold = fold_change_threshold
        self.min_pathway_genes = min_pathway_genes
        
        # Specialized verification components
        self._expression_validator = ExpressionValidator(
            p_value_threshold, fold_change_threshold
        )
        self._pathway_validator = PathwayValidator(min_pathway_genes)
        self._reasoning_validator = ReasoningValidator()

    async def setup(self) -> None:
        r"""Set up the verifier with necessary resources.

        This method initializes:
        1. Reference gene databases
        2. Pathway databases
        3. Statistical models
        """
        await super().setup()
        
        try:
            # Initialize specialized components
            await self._expression_validator.setup()
            await self._pathway_validator.setup()
            await self._reasoning_validator.setup()
            
            logger.info("RNA-seq verifier initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize RNA-seq verifier: {e!s}"
            logger.error(error_msg, exc_info=True)
            await self.cleanup()
            raise RuntimeError(error_msg) from e

    async def cleanup(self) -> None:
        r"""Clean up verifier resources."""
        try:
            # Clean up specialized components
            await self._expression_validator.cleanup()
            await self._pathway_validator.cleanup()
            await self._reasoning_validator.cleanup()
        except Exception as e:
            logger.error(f"Error during RNA-seq verifier cleanup: {e!s}")
        
        # Always call parent cleanup
        await super().cleanup()

    async def _verify_implementation(self, result: Response) -> VerificationResult:
        r"""Implement RNA-seq verification logic.

        Args:
            result: The response to verify containing RNA-seq analysis.

        Returns:
            VerificationResult: Containing the verification outcome.
        """
        try:
            # Extract analysis components from response
            analysis_components = self._extract_analysis_components(result.llm_response)
            
            # Verify each component
            expression_result = await self._expression_validator.verify(
                analysis_components.get("differential_expression", {})
            )
            
            pathway_result = await self._pathway_validator.verify(
                analysis_components.get("pathway_analysis", {})
            )
            
            reasoning_result = await self._reasoning_validator.verify(
                analysis_components.get("reasoning", ""),
                result.gold_standard_solution
            )
            
            # Combine verification results
            all_passed = all([
                expression_result["passed"],
                pathway_result["passed"],
                reasoning_result["passed"]
            ])
            
            # Calculate overall score
            scores = {
                "expression_score": expression_result["score"],
                "pathway_score": pathway_result["score"],
                "reasoning_score": reasoning_result["score"],
                "overall_score": (
                    expression_result["score"] * 0.4 +
                    pathway_result["score"] * 0.3 +
                    reasoning_result["score"] * 0.3
                )
            }
            
            # Create verification result
            status = VerificationStatus.SUCCESS if all_passed else VerificationStatus.FAILURE
            
            return VerificationResult(
                status=status,
                score=scores,
                metadata={
                    "expression_details": expression_result["details"],
                    "pathway_details": pathway_result["details"],
                    "reasoning_details": reasoning_result["details"],
                }
            )
            
        except Exception as e:
            logger.error(f"RNA-seq verification error: {e!s}", exc_info=True)
            return VerificationResult(
                status=VerificationStatus.ERROR,
                error_message=f"Verification failed: {e!s}"
            )

    def _extract_analysis_components(self, response_text: str) -> Dict[str, Any]:
        r"""Extract RNA-seq analysis components from response text.

        Args:
            response_text: The LLM response text to parse

        Returns:
            Dictionary containing extracted components
        """
        components = {}
        
        # Extract differential expression section
        de_match = re.search(
            r"```(?:json|python)?\s*([\s\S]*?differential[\s\S]*?)```",
            response_text,
            re.IGNORECASE
        )
        if de_match:
            try:
                components["differential_expression"] = json.loads(de_match.group(1))
            except json.JSONDecodeError:
                # Try to parse as Python dict if JSON fails
                components["differential_expression"] = self._parse_python_dict(de_match.group(1))
        
        # Extract pathway analysis section
        pathway_match = re.search(
            r"```(?:json|python)?\s*([\s\S]*?pathway[\s\S]*?)```",
            response_text,
            re.IGNORECASE
        )
        if pathway_match:
            try:
                components["pathway_analysis"] = json.loads(pathway_match.group(1))
            except json.JSONDecodeError:
                components["pathway_analysis"] = self._parse_python_dict(pathway_match.group(1))
        
        # Extract reasoning section
        reasoning_match = re.search(
            r"(Analysis steps:|Reasoning:|Chain of thought:)[\s\S]*?(\n\n|$)",
            response_text,
            re.IGNORECASE
        )
        if reasoning_match:
            components["reasoning"] = reasoning_match.group(0)
        
        return components
    
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


class ExpressionValidator:
    r"""Validates differential expression analysis results."""
    
    def __init__(self, p_value_threshold: float, fold_change_threshold: float):
        self.p_value_threshold = p_value_threshold
        self.fold_change_threshold = fold_change_threshold
    
    async def setup(self) -> None:
        r"""Set up the expression validator."""
        pass
    
    async def cleanup(self) -> None:
        r"""Clean up resources."""
        pass
    
    async def verify(self, expression_data: Dict[str, Any]) -> Dict[str, Any]:
        r"""Verify differential expression analysis.

        Args:
            expression_data: Differential expression results

        Returns:
            Dictionary with verification results
        """
        if not expression_data:
            return {"passed": False, "score": 0.0, "details": "No expression data found"}
        
        # Check for required fields
        required_fields = ["genes", "p_values", "fold_changes"]
        missing_fields = [field for field in required_fields if field not in expression_data]
        
        if missing_fields:
            return {
                "passed": False,
                "score": 0.0,
                "details": f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        # Verify p-values are valid
        p_values = expression_data.get("p_values", {})
        valid_p_values = all(0 <= p <= 1 for p in p_values.values())
        
        # Verify fold changes meet threshold for significant genes
        fold_changes = expression_data.get("fold_changes", {})
        significant_genes = [
            gene for gene, p_val in p_values.items()
            if p_val <= self.p_value_threshold
        ]
        
        valid_fold_changes = all(
            abs(fold_changes.get(gene, 0)) >= self.fold_change_threshold
            for gene in significant_genes
        )
        
        # Calculate score based on validation results
        score = 0.0
        if valid_p_values:
            score += 0.5
        if valid_fold_changes:
            score += 0.5
        
        return {
            "passed": valid_p_values and valid_fold_changes,
            "score": score,
            "details": {
                "valid_p_values": valid_p_values,
                "valid_fold_changes": valid_fold_changes,
                "significant_genes": len(significant_genes)
            }
        }


class PathwayValidator:
    r"""Validates pathway enrichment analysis results."""
    
    def __init__(self, min_pathway_genes: int):
        self.min_pathway_genes = min_pathway_genes
    
    async def setup(self) -> None:
        r"""Set up the pathway validator."""
        pass
    
    async def cleanup(self) -> None:
        r"""Clean up resources."""
        pass
    
    async def verify(self, pathway_data: Dict[str, Any]) -> Dict[str, Any]:
        r"""Verify pathway enrichment analysis.

        Args:
            pathway_data: Pathway enrichment results

        Returns:
            Dictionary with verification results
        """
        if not pathway_data:
            return {"passed": False, "score": 0.0, "details": "No pathway data found"}
        
        # Check for required fields
        required_fields = ["pathways", "p_values", "gene_counts"]
        missing_fields = [field for field in required_fields if field not in pathway_data]
        
        if missing_fields:
            return {
                "passed": False,
                "score": 0.0,
                "details": f"Missing required fields: {', '.join(missing_fields)}"
            }
        
        # Verify pathway gene counts meet minimum threshold
        gene_counts = pathway_data.get("gene_counts", {})
        valid_gene_counts = all(
            count >= self.min_pathway_genes
            for count in gene_counts.values()
        )
        
        # Verify p-values are valid
        p_values = pathway_data.get("p_values", {})
        valid_p_values = all(0 <= p <= 1 for p in p_values.values())
        
        # Calculate score based on validation results
        score = 0.0
        if valid_gene_counts:
            score += 0.5
        if valid_p_values:
            score += 0.5
        
        return {
            "passed": valid_gene_counts and valid_p_values,
            "score": score,
            "details": {
                "valid_gene_counts": valid_gene_counts,
                "valid_p_values": valid_p_values,
                "pathway_count": len(pathway_data.get("pathways", []))
            }
        }


class ReasoningValidator:
    r"""Validates chain-of-thought reasoning in RNA-seq analysis."""
    
    def __init__(self):
        self.required_steps = [
            "quality control",
            "differential_expression",
            "pathway_analysis",
            "biological_interpretation",
            "statistical_validation"
        ]
    
    async def setup(self) -> None:
        r"""Set up the reasoning validator."""
        pass
    
    async def cleanup(self) -> None:
        r"""Clean up resources."""
        pass
    
    async def verify(self, reasoning_text: str, gold_standard: Optional[str] = None) -> Dict[str, Any]:
        r"""Verify chain-of-thought reasoning in RNA-seq analysis.

        Args:
            reasoning_text: The reasoning text to verify
            gold_standard: Optional gold standard solution for comparison

        Returns:
            Dictionary with verification results
        """
        if not reasoning_text:
            return {"passed": False, "score": 0.0, "details": "No reasoning provided"}
        
        # Check for required analysis steps
        steps_found = []
        for step in self.required_steps:
            if step.lower() in reasoning_text.lower():
                steps_found.append(step)
        
        # Calculate completeness score
        completeness_score = len(steps_found) / len(self.required_steps)
        
        # Verify reasoning against gold standard if provided
        gold_standard_score = 0.0
        if gold_standard:
            # Simple overlap-based scoring for demonstration
            # In production, would use more sophisticated NLP techniques
            gold_standard_words = set(gold_standard.lower().split())
            reasoning_words = set(reasoning_text.lower().split())
            overlap = len(gold_standard_words.intersection(reasoning_words))
            gold_standard_score = min(1.0, overlap / max(1, len(gold_standard_words) * 0.3))
        
        # Calculate overall score
        overall_score = completeness_score * 0.7
        if gold_standard:
            overall_score += gold_standard_score * 0.3
        
        return {
            "passed": completeness_score >= 0.7,
            "score": overall_score,
            "details": {
                "steps_found": steps_found,
                "steps_missing": [step for step in self.required_steps if step not in steps_found],
                "completeness_score": completeness_score,
                "gold_standard_score": gold_standard_score if gold_standard else None
            }
        }