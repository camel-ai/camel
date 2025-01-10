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
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field


class ReasoningStep(BaseModel):
    step: str = Field(
        ..., description="A single step in the reasoning process."
    )


class MultiHopQA(BaseModel):
    question: str = Field(
        ..., description="The question that requires multi-hop reasoning."
    )
    reasoning_steps: List[ReasoningStep] = Field(
        ...,
        description="The steps involved in reasoning to answer the question.",
    )
    answer: str = Field(
        ..., description="The answer to the multi-hop question."
    )
    supporting_facts: List[str] = Field(
        ..., description="Facts that support the reasoning and answer."
    )
    type: str = Field(description="The type of question-answer pair.")

    class Config:
        json_schema_extra: ClassVar[Dict[str, Any]] = {
            "example": {
                "question": "What is the capital of France?",
                "reasoning_steps": [
                    {"step": "Identify the country France."},
                    {"step": "Find the capital city of France."},
                ],
                "answer": "Paris",
                "supporting_facts": [
                    "France is a country in Europe.",
                    "Paris is the capital city of France.",
                ],
                "type": "multi_hop_qa",
            }
        }


class ContextPrompt(BaseModel):
    main_context: str = Field(
        ...,
        description="The main context for generating"
        " the question-answer pair.",
    )
    related_contexts: Optional[List[str]] = Field(
        default=None,
        description="Additional contexts related to the main context.",
    )