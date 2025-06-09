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

import json
from abc import ABC, abstractmethod
from typing import Dict, Optional

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.logger import get_logger

logger = get_logger(__name__)


class BaseScorer(ABC):
    @abstractmethod
    def score(
        self, reference_prompt: str, candidate_prompt: str
    ) -> Dict[str, int]:
        r"""Compare a candidate prompt against a reference prompt and
        return a tuple of scores. The higher the score, the better.
        For example, (diversity, difficulty, feasibility).
        """
        pass


class MathScorer(BaseScorer):
    def __init__(self, agent: Optional[ChatAgent] = None):
        self.system_msg = """
You are an evaluator for math problems. Your task is to compare a new math 
problem against a reference math problem by trying to solve it, and rate it 
in **three dimensions**.

1. Diversity (1-5): How novel is the new problem compared to the 
reference? 1 = almost the same, 5 = completely different.

2. Difficulty (1-10): Rate the relative difficulty compared to the reference 
problem. 1 = much less difficult, 5 = similar difficulty, 10 = much more 
difficult. The difficulty should be based on the complexity of reasoning—i.e., 
problems that require multi-step reasoning or clever methods to solve.

3. Solvability (1-10): How likely is the problem solvable using standard math 
techniques and only contain one question that could be answered by a number or 
a formula? 1 = very unsolvable or ambiguous, 10 = solvable and could be 
answered by a number or a formula.

Respond with a JSON object like: 
{ "solution": ..., "diversity": ..., "difficulty": ..., "solvability": ... }
"""
        self.agent = agent or ChatAgent(self.system_msg)

    class MathScoreSchema(BaseModel):
        diversity: int = Field(
            ...,
            description=(
                "Score for the diversity of the math problem "
                "compared to the reference"
            ),
        )
        difficulty: int = Field(
            ..., description="Score for the relative difficulty"
        )
        solvability: int = Field(
            ...,
            description="Score for the solvability of the problem",
        )

    def score(
        self, reference_problem: str, new_problem: str
    ) -> Dict[str, int]:
        r"""Evaluates the new math problem relative to the reference math
        problem.

        Args:
            reference_problem (str): The reference math problem.
            new_problem (str): The new or evolved math problem.

        Returns:
            Dict[str, int]: A dictionary with scores for diversity, difficulty,
            validity, and solvability.
        """
        query = (
            f"Reference problem:\n{reference_problem}\n\n"
            f"New problem:\n{new_problem}\n\n"
            "Try to solve the new problem. Then provide scores in JSON format."
        )
        response = self.agent.step(query, response_format=self.MathScoreSchema)
        score_data = json.loads(response.msg.content)
        return score_data


class GeneralScorer(BaseScorer):
    def __init__(self, agent: Optional[ChatAgent] = None):
        self.system_msg = (
            "You are an evaluator for problems in various domains. Your task "
            "is to compare a new problem against a reference problem, and rate"
            " it in **three dimensions**, each scored from 1 to 5.\n\n"
            "1. Diversity (1-5): How novel is the new problem compared to the "
            "reference? 1 = very similar, 5 = completely different.\n"
            "2. Complexity (1-5): Relative to the reference problem. "
            "1 = much less complex, 3 = similar complexity, "
            "5 = much more complex.\n"
            "3. Validity (1-5): How well-defined, meaningful, the problem is."
            "1 = vague/flawed, 5 = precise and fully meaningful.\n"
            "Respond with a JSON object like: "
            "{ \"diversity\": ..., \"complexity\": ..., \"validity\": ... }"
        )
        self.agent = agent or ChatAgent(self.system_msg)

    class GeneralScoreSchema(BaseModel):
        diversity: int = Field(
            ...,
            description=(
                "Score for the diversity of the problem "
                "compared to the reference."
            ),
        )
        complexity: int = Field(
            ...,
            description=("Score for the relative complexity of the problem."),
        )
        validity: int = Field(
            ...,
            description=(
                "Score estimating the likelihood that the problem is "
                "well-defined."
            ),
        )

    def score(
        self, reference_problem: str, new_problem: str
    ) -> Dict[str, int]:
        r"""Evaluates the new problem against the reference problem using
        structured scoring.

        Args:
            reference_problem (str): The original problem.
            new_problem (str): The evolved or new problem.

        Returns:
            Dict[str, int]: A dictionary with scores for diversity, complexity,
                and validity.
        """
        query = (
            f"Reference problem:\n{reference_problem}\n\n"
            f"New problem:\n{new_problem}\n\n"
            "Provide scores in JSON format."
        )
        response = self.agent.step(
            query, response_format=self.GeneralScoreSchema
        )
        score_data = json.loads(response.msg.content)
        return score_data
