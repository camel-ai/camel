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
"""Type definitions for verification results and metrics."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VerificationMetrics(BaseModel):
    """Metrics used in verification process."""

    name: str = Field(..., description="Name of the metric")
    value: float = Field(
        ..., ge=0, le=1, description="Metric value between 0 and 1"
    )
    weight: float = Field(
        1.0, ge=0, description="Weight of this metric in overall score"
    )
    threshold: float = Field(
        0.7, ge=0, le=1, description="Passing threshold for this metric"
    )

    class Config:
        """Pydantic configuration."""

        frozen = True


class VerificationResult(BaseModel):
    """Results from verification process."""

    score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Overall verification score between 0 and 1",
    )
    passed: bool = Field(
        ..., description="Whether verification passed overall threshold"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Detailed verification results"
    )
    metrics: List[VerificationMetrics] = Field(
        default_factory=list, description="List of individual metrics"
    )
    feedback: str = Field(..., description="Human-readable feedback message")
    error: Optional[str] = Field(
        None, description="Error message if verification failed"
    )

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary, handling nested models."""
        d = super().dict(*args, **kwargs)
        if "metrics" in d:
            d["metrics"] = [m.dict() for m in self.metrics]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VerificationResult":
        """Create from dictionary, handling nested models."""
        if "metrics" in data:
            data["metrics"] = [
                VerificationMetrics(**m) if isinstance(m, dict) else m
                for m in data["metrics"]
            ]
        return cls(**data)

    class Config:
        """Pydantic configuration."""

        frozen = True
