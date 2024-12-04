import re
from abc import abstractmethod, ABC
from typing import List

from rouge import Rouge


class FilterFunction(ABC):
    """A base class for filter functions."""

    @abstractmethod
    def apply(self, instruction: str) -> bool:
        pass


class LengthFilter(FilterFunction):
    def __init__(self, min_len: int = 5, max_len: int = 200):
        self.min_len = min_len
        self.max_len = max_len

    def apply(self, instruction: str) -> bool:
        return self.min_len <= len(instruction.split()) <= self.max_len


class KeywordFilter(FilterFunction):
    def __init__(self, keywords: List[str]):
        self.keywords = [keyword.lower() for keyword in keywords]

    def apply(self, instruction: str) -> bool:
        return not any(
            keyword in instruction.lower() for keyword in self.keywords)


class PunctuationFilter(FilterFunction):
    def apply(self, instruction: str) -> bool:
        return not re.match(r'^[^\w\s]', instruction)


class NonEnglishFilter(FilterFunction):
    def apply(self, instruction: str) -> bool:
        return bool(re.match(r'^[A-Za-z]', instruction))


class RougeSimilarityFilter(FilterFunction):
    def __init__(self, existing_instructions: List[str],
                 threshold: float = 0.7):
        self.existing_instructions = existing_instructions
        self.threshold = threshold
        self.rouge = Rouge()

    def apply(self, instruction: str) -> bool:
        if not self.existing_instructions:
            return True
        scores = self.rouge.get_scores(
            [instruction] * len(self.existing_instructions),
            self.existing_instructions, avg=True)
        return scores['rouge-l']['f'] <= self.threshold
