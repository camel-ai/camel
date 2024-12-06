from pydantic import BaseModel, Field
from typing import List, Optional

class ReasoningStep(BaseModel):
    step: str = Field(..., description="A single step in the reasoning process.")


class MultiHopQA(BaseModel):
    question: str = Field(..., description="The question that requires multi-hop reasoning.")
    reasoning_steps: List[ReasoningStep] = Field(..., description="The steps involved in reasoning to answer the question.")
    answer: str = Field(..., description="The answer to the multi-hop question.")
    supporting_facts: List[str] = Field(..., description="Facts that support the reasoning and answer.")
    type: str = Field(default="multi_hop_qa", description="The type of question-answer pair.")

    class Config:
        schema_extra = {
            "example": {
                "question": "What is the capital of France?",
                "reasoning_steps": [
                    {"step": "Identify the country France."},
                    {"step": "Find the capital city of France."}
                ],
                "answer": "Paris",
                "supporting_facts": [
                    "France is a country in Europe.",
                    "Paris is the capital city of France."
                ],
                "type": "multi_hop_qa"
            }
        }

class ContextPrompt(BaseModel):
    main_context: str = Field(..., description="The main context for generating the question-answer pair.")
    related_contexts: Optional[List[str]] = Field(default=None, description="Additional contexts related to the main context.")
