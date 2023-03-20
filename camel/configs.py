from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Union


@dataclass
class ChatGPTConfig:
    temperature: float = 0.2  # openai default: 1.0
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    stop: Optional[Union[str, Sequence[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    logit_bias: Dict = field(default_factory=dict)
    user: str = ""
