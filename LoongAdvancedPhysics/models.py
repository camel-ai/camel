from pydantic import BaseModel
from typing import Union

class ResponseFormat(BaseModel):
   reasoning: str
   code: str
   unit: Union[str, None] = None

class AnswerFormat(BaseModel):
   gt_answer: str
   unit: Union[str, None] = None