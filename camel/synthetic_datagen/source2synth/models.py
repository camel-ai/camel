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

class ContextPrompt(BaseModel):
    main_context: str
    related_contexts: Optional[List[str]] = None
