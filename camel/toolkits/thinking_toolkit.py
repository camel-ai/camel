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

from typing import List, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit

logger = get_logger(__name__)


class ThinkingToolkit(BaseToolkit):
    r"""A toolkit for recording thoughts during reasoning processes."""

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        r"""Initialize the ThinkingToolkit.

        Args:
            timeout (Optional[float]): The timeout for the toolkit.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        self.plans: List[str] = []
        self.hypotheses: List[str] = []
        self.thoughts: List[str] = []
        self.contemplations: List[str] = []
        self.critiques: List[str] = []
        self.syntheses: List[str] = []
        self.reflections: List[str] = []

    def plan(self, plan: str) -> str:
        r"""Use the tool to create a plan or strategy.
        This tool is for outlining the approach or steps to be taken before
        starting the actual thinking process.

        Args:
            plan (str): A forward-looking plan or strategy.

        Returns:
            str: The recorded plan.
        """
        try:
            logger.debug(f"Plan: {plan}")
            self.plans.append(plan)
            return f"Plan: {plan}"

        except Exception as e:
            error_msg = f"Error recording plan: {e}"
            logger.error(error_msg)
            return error_msg

    def hypothesize(self, hypothesis: str) -> str:
        r"""Use the tool to form a hypothesis or make a prediction.
        This tool is for making educated guesses or predictions based on
        the plan, before detailed thinking.

        Args:
            hypothesis (str): A hypothesis or prediction to test.

        Returns:
            str: The recorded hypothesis.
        """
        try:
            logger.debug(f"Hypothesis: {hypothesis}")
            if not self.plans:
                return "Consider creating a plan before forming hypotheses."
            self.hypotheses.append(hypothesis)
            return f"Hypothesis: {hypothesis}"

        except Exception as e:
            error_msg = f"Error recording hypothesis: {e}"
            logger.error(error_msg)
            return error_msg

    def think(self, thought: str) -> str:
        r"""Use the tool to think about something.
        It will not obtain new information or change the database, but just
        append the thought to the log. Use it for initial thoughts and
        observations during the execution of the plan.

        Args:
            thought (str): A thought to think about.

        Returns:
            str: The recorded thought.
        """
        try:
            logger.debug(f"Thought: {thought}")
            if not self.plans:
                return (
                    "Consider creating a plan before thinking "
                    "through the process."
                )
            self.thoughts.append(thought)
            return f"Thought: {thought}"

        except Exception as e:
            error_msg = f"Error recording thought: {e}"
            logger.error(error_msg)
            return error_msg

    def contemplate(self, contemplation: str) -> str:
        r"""Use the tool to deeply contemplate an idea or concept.
        This tool is for deeper, more thorough exploration of thoughts,
        considering multiple perspectives and implications. It's more
        comprehensive than basic thinking but more focused than reflection.

        Args:
            contemplation (str): A deeper exploration of thoughts or concepts.

        Returns:
            str: The recorded contemplation.
        """
        try:
            logger.debug(f"Contemplation: {contemplation}")
            if not self.thoughts:
                return (
                    "Consider thinking about the topic before "
                    "deep contemplation."
                )
            self.contemplations.append(contemplation)
            return f"Contemplation: {contemplation}"

        except Exception as e:
            error_msg = f"Error recording contemplation: {e}"
            logger.error(error_msg)
            return error_msg

    def critique(self, critique: str) -> str:
        r"""Use the tool to critically evaluate current thoughts.
        This tool is for identifying potential flaws, biases, or
        weaknesses in the current thinking process.

        Args:
            critique (str): A critical evaluation of current thoughts.

        Returns:
            str: The recorded critique.
        """
        try:
            logger.debug(f"Critique: {critique}")
            if not self.contemplations:
                return "Consider contemplating deeply before critiquing."
            self.critiques.append(critique)
            return f"Critique: {critique}"

        except Exception as e:
            error_msg = f"Error recording critique: {e}"
            logger.error(error_msg)
            return error_msg

    def synthesize(self, synthesis: str) -> str:
        r"""Use the tool to combine and integrate various thoughts.
        This tool is for bringing together different thoughts, contemplations,
        and critiques into a coherent understanding.

        Args:
            synthesis (str): An integration of multiple thoughts and insights.

        Returns:
            str: The recorded synthesis.
        """
        try:
            logger.debug(f"Synthesis: {synthesis}")
            if not self.critiques:
                return "Consider critiquing thoughts before synthesizing."
            self.syntheses.append(synthesis)
            return f"Synthesis: {synthesis}"

        except Exception as e:
            error_msg = f"Error recording synthesis: {e}"
            logger.error(error_msg)
            return error_msg

    def reflect(self, reflection: str) -> str:
        r"""Use the tool to reflect on the entire process.
        This tool is for final evaluation of the entire thinking process,
        including plans, hypotheses, thoughts, contemplations, critiques,
        and syntheses.

        Args:
            reflection (str): A comprehensive reflection on the process.

        Returns:
            str: The recorded reflection.
        """
        try:
            logger.debug(f"Reflection: {reflection}")
            if not self.syntheses:
                return (
                    "Consider synthesizing insights before final reflection."
                )
            self.reflections.append(reflection)
            return f"Reflection: {reflection}"

        except Exception as e:
            error_msg = f"Error recording reflection: {e}"
            logger.error(error_msg)
            return error_msg

    def get_tools(self) -> List[FunctionTool]:
        r"""Get all tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of tools.
        """
        return [
            FunctionTool(self.plan),
            FunctionTool(self.hypothesize),
            FunctionTool(self.think),
            FunctionTool(self.contemplate),
            FunctionTool(self.critique),
            FunctionTool(self.synthesize),
            FunctionTool(self.reflect),
        ]
