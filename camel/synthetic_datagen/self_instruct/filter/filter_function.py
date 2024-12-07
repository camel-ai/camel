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
import re
from abc import ABC, abstractmethod
from typing import List

from rouge import Rouge


class FilterFunction(ABC):
    r"""A base abstract class for filter functions.

    Subclasses must implement the `apply` method, which determines whether
    a given instruction passes the filter criteria.

    """

    @abstractmethod
    def apply(self, instruction: str) -> bool:
        r"""Evaluate the given instruction based on the filter's criteria.

        Args:
            instruction (str): The instruction to evaluate.

        Returns:
            bool: True if the instruction passes the filter, False otherwise.
        """
        pass


class LengthFilter(FilterFunction):
    r"""Filters instructions based on their word count.

    Args:
        min_len (int): The minimum word count required for an instruction.
        max_len (int): The maximum word count allowed for an instruction.
    """

    def __init__(self, min_len: int = 5, max_len: int = 200):
        self.min_len = min_len
        self.max_len = max_len

    def apply(self, instruction: str) -> bool:
        r"""Filter the instruction

        Args:
            instruction (str): the instruction to be filtered

        Returns:
            bool: True if the length of the instruction is within the range
            of [min_len, max_len]
        """
        word_count = len(instruction.split())
        return self.min_len <= word_count <= self.max_len


class KeywordFilter(FilterFunction):
    r"""Filters instructions that contain specific undesirable keywords.

    Args:
        keywords (List[str]): A list of keywords to filter out.
    """

    def __init__(self, keywords: List[str]):
        self.keywords = [keyword.lower() for keyword in keywords]

    def apply(self, instruction: str) -> bool:
        r"""Filter the instruction

        Args:
            instruction (str): the instruction to be filtered

        Returns:
            bool: True Instruction must NOT contain any of the keywords.
        """
        lower_instr = instruction.lower()
        return not any(keyword in lower_instr for keyword in self.keywords)


class PunctuationFilter(FilterFunction):
    r"""Filters instructions that begin with a non-alphanumeric character."""

    def apply(self, instruction: str) -> bool:
        r"""Filter the instruction

        Args:
            instruction (str): the instruction to be filtered

        Returns:
            bool: True if the instruction does not start with punctuation.
        """
        return not re.match(r'^[^\w\s]', instruction)


class NonEnglishFilter(FilterFunction):
    r"""Filters instructions that do not begin with English letters."""

    def apply(self, instruction: str) -> bool:
        r"""Filter the instruction

        Args:
            instruction (str): the instruction to be filtered

        Returns:
            bool: True if the instruction starts with an English letter.
        """
        return bool(re.match(r'^[A-Za-z]', instruction))


class RougeSimilarityFilter(FilterFunction):
    r"""Filters instructions that are too similar to existing instructions
    based on ROUGE scores.

    Args:
        existing_instructions (List[str]): A list of existing instructions to
            compare against.
        threshold (float): The similarity threshold for filtering (default is
            0.7).
    """

    def __init__(
        self, existing_instructions: List[str], threshold: float = 0.7
    ):
        self.existing_instructions = existing_instructions
        self.threshold = threshold
        self.rouge = Rouge()

    def apply(self, instruction: str) -> bool:
        r"""Filter the instruction

        Args:
            instruction (str): the instruction to be filtered

        Returns:
            bool: True if the instruction's similarity to any existing
            instruction is below the threshold.
        """
        if not self.existing_instructions:
            return True

        for existing_instr in self.existing_instructions:
            scores = self.rouge.get_scores(instruction, existing_instr)
            score = scores[0]['rouge-l']['f']
            if score > self.threshold:
                return False

        return True
