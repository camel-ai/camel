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

from camel.models.reward import BaseRewardModel


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
            (default::obj:`5`)
        max_len (int): The maximum word count allowed for an instruction.
            (default::obj:`200`)
    """

    def __init__(self, min_len: int = 5, max_len: int = 200):
        self.min_len = min_len
        self.max_len = max_len

    def apply(self, instruction: str) -> bool:
        r"""Filter the instruction

        Args:
            instruction (str): the instruction to be filtered.

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
            instruction (str): the instruction to be filtered.

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
            instruction (str): the instruction to be filtered.

        Returns:
            bool: True if the instruction does not start with punctuation.
        """
        return not re.match(r'^[^\w\s]', instruction)


class NonEnglishFilter(FilterFunction):
    r"""Filters instructions that do not begin with English letters."""

    def apply(self, instruction: str) -> bool:
        r"""Filter the instruction

        Args:
            instruction (str): the instruction to be filtered.

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
        threshold (float): The similarity threshold for filtering.
            (default::obj:`0.7`)
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
            instruction (str): the instruction to be filtered.

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


class RewardModelFilter(FilterFunction):
    r"""Filters instructions based on scores provided by a reward model.

    Args:
        reward_model (BaseRewardModel): The reward model used to evaluate
            the instructions.
        threshold (float): The minimum score required for an instruction
            to pass the filter.
    """

    def __init__(
        self,
        reward_model: BaseRewardModel,
        threshold: float = 0.5,
    ):
        self.prompt = ""
        self.reward_model = reward_model
        self.threshold = threshold

    def apply(self, instruction: str) -> bool:
        r"""Filter the instruction

        Args:
            instruction (str): The instruction to be filtered.

        Returns:
            bool: True if the instruction's score is above the threshold.

        Raises:
            ValueError: ValueError: If `score_types` is empty or if the
                required score is not found in `scores`.
        """

        data = [
            {"role": "user", "content": self.prompt},
            {"role": "assistant", "content": instruction},
        ]
        scores = self.reward_model.evaluate(data)
        score_types = self.reward_model.get_scores_types()
        if not score_types:
            raise ValueError("No score types available from the reward model.")

        score_type = score_types[0]
        score = scores.get(score_type, None)

        if score is None:
            raise ValueError(
                f"Score type '{score_type}' is not found in the "
                "evaluation scores."
            )

        return score >= self.threshold
