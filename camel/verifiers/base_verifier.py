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
"""Base verifier class that all domain-specific verifiers inherit from."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from datasets import Dataset


class BaseVerifier(ABC):
    """Abstract base class for all verifiers.

    This class defines the interface that all domain-specific verifiers
    must implement.
    It provides common functionality and enforces a consistent verification
    pattern.
    """

    def __init__(self, criteria: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the verifier.

        Args:
            criteria: Optional dictionary of verification criteria that
            override defaults
        """
        self.criteria = criteria or {}

    @abstractmethod
    def verify(
        self,
        data: Dataset,
        criteria: Optional[Dict[str, Any]] = None,
    ) -> Dataset:
        """Verify the provided data.

        Args:
            data: Dataset containing items to verify
            criteria: Optional verification criteria for this specific call

        Returns:
            Dataset with verification results added

        Note:
            The returned dataset should include at minimum a 'correct' column
            indicating whether each item passed verification.
        """
        raise NotImplementedError

    def _calculate_score(
        self,
        details: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """Calculate overall verification score from component scores.

        Args:
            details: Dictionary of component verification results
            weights: Optional weights for each component

        Returns:
            Float between 0 and 1 representing overall score
        """
        if not details:
            return 0.0

        weights = weights or {k: 1.0 for k in details.keys()}
        total_weight = sum(weights[k] for k in details.keys() if k in weights)

        if total_weight == 0:
            return 0.0

        weighted_sum = sum(
            details[k] * weights[k]
            for k in details.keys()
            if k in weights and isinstance(details[k], (int, float))
        )

        return weighted_sum / total_weight

    def _format_feedback(
        self, details: Dict[str, Any], threshold: float = 0.7
    ) -> str:
        """Format verification details into human-readable feedback.

        Args:
            details: Dictionary of verification details
            threshold: Score threshold for passing

        Returns:
            Formatted feedback string
        """
        feedback = []

        for key, value in details.items():
            if isinstance(value, (int, float)):
                status = "PASS" if value >= threshold else "FAIL"
                feedback.append(f"{key}: {value:.2f} [{status}]")
            else:
                feedback.append(f"{key}: {value}")

        return "\n".join(feedback)

    def __repr__(self) -> str:
        """Return string representation of the verifier."""
        return f"{self.__class__.__name__}(criteria={self.criteria})"
