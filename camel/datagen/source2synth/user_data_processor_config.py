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

from pydantic import BaseModel, ConfigDict, Field

from camel.agents.multi_hop_generator_agent import MultiHopGeneratorAgent


class ProcessorConfig(BaseModel):
    r"""Data processing configuration class"""

    def __repr__(self):
        return (
            f"ProcessorConfig("
            f"seed={self.seed}, min_length={self.min_length}, "
            f"max_length={self.max_length}, "
            f"complexity_threshold={self.complexity_threshold}, "
            f"dataset_size={self.dataset_size}, "
            f"use_ai_model={self.use_ai_model}"
            f")"
        )

    model_config = ConfigDict(
        validate_assignment=True,
        frozen=False,
        protected_namespaces=(),
        arbitrary_types_allowed=True,
    )

    seed: int = Field(  # Generate a random seed for reproducibility
        default_factory=lambda: random.randint(0, 1000),
        description="Random seed for reproducibility",
    )

    min_length: int = Field(
        default=50, description="Minimum text length", ge=0
    )

    max_length: int = Field(
        default=512, description="Maximum text length", gt=0
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

    hop_generating_agent: MultiHopGeneratorAgent = Field(
        default_factory=lambda: MultiHopGeneratorAgent(),
        description="Agent for generating multi-hop text",
    )
