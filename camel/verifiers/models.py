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
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class VerificationOutcome(Enum):
    r"""Enum representing the status of a verification."""

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    TIMEOUT = "timeout"

    def __bool__(self):
        r"""Only VerificationOutcome.SUCCESS is truthy; others are falsy."""
        return self is VerificationOutcome.SUCCESS


class VerificationResult(BaseModel):
    r"""Structured result from a verification."""

    status: VerificationOutcome = Field(
        description="Status of the verification"
    )
    result: str = Field(description="Verification result")
    duration: float = Field(
        default=0.0, description="Duration of verification in seconds"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the verification was performed",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the verification",
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if verification failed"
    )


class VerifierConfig(BaseModel):
    r"""Configuration for verifier behavior."""

    enabled: bool = Field(True, description="Whether verification is enabled")
    strict_mode: bool = Field(
        False, description="Whether to fail on any validation error"
    )
    timeout: Optional[float] = Field(
        None, description="Verification timeout in seconds"
    )
    max_retries: int = Field(3, description="Maximum number of retry attempts")
    retry_delay: float = Field(
        1.0, description="Delay between retries in seconds"
    )
