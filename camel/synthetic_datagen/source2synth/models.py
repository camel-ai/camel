from pydantic import BaseModel
from typing import List, Optional

class ReasoningStep(BaseModel):
    step: str


class MultiHopQA(BaseModel):
    question: str
    reasoning_steps: List[ReasoningStep]
    answer: str
    supporting_facts: List[str]
    type: str = "multi_hop_qa"

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
    main_context: str
    related_contexts: Optional[List[str]] = None
