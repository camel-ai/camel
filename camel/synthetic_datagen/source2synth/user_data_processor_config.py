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

import random
from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass
class ProcessorConfig(BaseModel):
    """Data processing configuration class"""

    seed: int = Field(  # Generate a random seed for reproducibility
        default=random.randint(0, 1000),
        description="Random seed for reproducibility",
    )

    min_length: int = Field(
        default=50, description="Minimum text length", ge=0
    )

    max_length: int = Field(
        default=512, description="Maximum text length", gt=0
    )

    quality_threshold: float = Field(
        default=0.7,
        description="Quality threshold for processing",
        ge=0.0,
        le=1.0,
    )

    complexity_threshold: float = Field(
        default=0.5,
        description="Complexity threshold for processing",
        ge=0.0,
        le=1.0,
    )

    dataset_size: int = Field(
        default=1000, description="Target size of the dataset", gt=0
    )

    use_ai_model: bool = Field(
        default=True, description="Whether to use AI model in processing"
    )

    model_temperature: float = Field(
        default=0.4,
        description="Temperature parameter for AI model generation",
        ge=0.0,
        le=1.0,
    )

    max_tokens: int = Field(
        default=4096,
        description="Maximum number of tokens for AI model output",
        gt=0,
    )

    class Config:
        """Pydantic model configuration"""

        validate_assignment = True
        frozen = True
