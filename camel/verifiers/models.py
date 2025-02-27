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

from pydantic import BaseModel, Field, root_validator


class VerificationStatus(Enum):
    r"""Enum representing the status of a verification."""

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    TIMEOUT = "timeout"


class VerificationMetrics(BaseModel):
    r"""Metrics collected during verification."""

    total_verifications: int = Field(
        default=0, description="Total number of verifications performed"
    )
    successful_verifications: int = Field(
        default=0, description="Number of successful verifications"
    )
    failed_verifications: int = Field(
        default=0, description="Number of failed verifications"
    )
    error_verifications: int = Field(
        default=0,
        description="Number of verifications that resulted in errors",
    )
    timeout_verifications: int = Field(
        default=0, description="Number of verifications that timed out"
    )
    total_duration: float = Field(
        default=0.0,
        description="Total duration of all verifications in seconds",
    )
    avg_duration: float = Field(
        default=0.0, description="Average duration per verification in seconds"
    )


class VerificationResult(BaseModel):
    r"""Structured result from a verification."""

    status: VerificationStatus = Field(
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


class TaskType(str, Enum):
    r"""Enumeration of supported task types."""

    MATHEMATICAL_PROGRAMMING = "mathematical_programming"
    LOGIC = "logic"
    ADVANCE_MATH = "advance_math"
    COMPUTATIONAL_BIOLOGY = "computational_biology"
    COMPUTATIONAL_CHEMISTRY = "computational_chemistry"
    QUANTUM_PHYSICS = "quantum_physics"
    GRAPH_THEORY = "graph_theory"
    CAUSAL_INFERENCE = "causal_inference"
    SOFTWARE_ENGINEERING = "software_engineering"
    SECURITY = "security"
    CRYPTOGRAPHY = "cryptography"
    EDA = "eda"
    MEDICINE = "medicine"
    FINANCE = "finance"
    LAW = "law"
    BOARD_GAMES = "board_games"


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


class MachineInfo(BaseModel):
    r"""Information about the machine running the generation."""

    hostname: str = Field(description="Name of the host machine")
    cpu_info: Dict[str, Any] = Field(description="CPU information")
    gpu_info: Optional[Dict[str, Any]] = Field(
        description="GPU information if available"
    )
    memory_info: Dict[str, Any] = Field(description="Memory usage information")
    platform: str = Field(description="Operating system platform")

    @root_validator(pre=True)
    def validate_machine_info(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        r"""Validate that required machine info fields are present."""
        required_cpu_fields = ['processor', 'cores']
        required_memory_fields = ['total', 'available']

        cpu_info = values.get('cpu_info', {})
        memory_info = values.get('memory_info', {})

        for field in required_cpu_fields:
            if field not in cpu_info:
                raise ValueError(f"Missing required CPU info field: {field}")

        for field in required_memory_fields:
            if field not in memory_info:
                raise ValueError(
                    f"Missing required memory info field: {field}"
                )

        return values
