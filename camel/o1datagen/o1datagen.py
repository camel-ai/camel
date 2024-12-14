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
from datetime import datetime
from typing import Annotated, Dict, Union

from pydantic import BaseModel, Field, confloat

from camel.agents import ChatAgent
from camel.logger import get_logger

# Get a logger for this module
logger = get_logger('o1datagen')


class AgentResponse(BaseModel):
    """Model for structured agent responses."""

    score: Annotated[float, confloat(ge=0, le=1)] = Field(
        ...,
        description="""Similarity score between 0 and 1 
        comparing current answer to correct answer""",
    )


class O1DataGene:
    r"""Class for generating and managing data through chat agent interactions.

    handling the generation of data by  a chat agent, managing golden answers,
    and maintaining a solution tree for correct solution steps.

    Args:
        chat_agent (ChatAgent): The chat agent used for generating responses
            and interacting with the system.
        golden_answers (Dict[str, str]): Dictionary containing pre-defined
            correct answers for validation and comparison. Required for answer
            verification.
        search_limit (int): Maximum number of search iterations allowed.
            (default::obj:`100`)
    """

    def __init__(
        self,
        chat_agent: ChatAgent,
        golden_answers: Dict[str, str],
        search_limit: int = 100,
    ):
        self.chat_agent = chat_agent
        self.golden_answers = golden_answers
        self.search_limit = search_limit
        self.solution_tree: Dict[str, Dict[str, Union[str, int]]] = {}
        logger.info(
            "O1DataGene initialized with search_limit=%d", search_limit
        )

    def get_answer(self, question: str, context: str = "") -> str:
        r"""Get the AI's thought process and answer.

        Args:
            question (str): The problem or question to be solved by the AI.
            context (str): Additional context or existing content to
                consider when generating the answer. (default::obj:`""`)

        Returns:
            str: The AI's detailed response including thought process and
                final answer.
        """
        prompt = f"""
        Please think step by step and solve this problem: {question}
        Existing content: {context}
        Requirements:
        1. Analyze the problem requirements
        2. List the steps to solve the problem
        3. Execute the solution process
        4. Provide the final answer
        Please explain the thought process of each step in detail.
        """
        self.chat_agent.reset()
        response = self.chat_agent.step(prompt)
        answer = response.msgs[0].content
        logger.info("AI thought process:\n%s", answer)
        return answer

    def verify_answer(self, question: str, answer: str) -> bool:
        r"""Verify if a generated answer is semantically equivalent to
            the golden answer for a given question.

        Args:
            question (str): The question to look up in the golden answers
                dictionary.
            answer (str): The answer to verify, typically generated
                by a model or provided by a user.

        Returns:
            bool: True if the answer matches the golden answer based on
                semantic equivalence (meaning the core content and meaning are
                the same, even if the exact wording differs).
                False in the following cases:
                - If the provided question doesn't exist in the golden answers
                - If the answer's meaning differs from the golden answer
        """
        golden_answer = self.golden_answers.get(question)
        if golden_answer is None:
            logger.error(f"Question '{question}' not found in golden answers.")
            return False
        prompt = f"""Please determine if the following two answers 
        express the same meaning:
        Question: {question}
        Answer 1: {answer}
        Answer 2: {golden_answer}
        Just answer "True" or "False".
        """
        self.chat_agent.reset()
        response = self.chat_agent.step(prompt)
        is_correct = response.msgs[0].content.strip().lower() == "true"
        logger.info("Answer verification result: %s", is_correct)
        return is_correct

    def monte_carlo_tree_search(
        self, question: str, partial_solution: str = ""
    ) -> tuple[str, bool]:
        r"""Generate and verify answers using Monte Carlo Tree Search.

        This method implements a Monte Carlo Tree Search approach
        to find the best solution by iteratively generating answers
        and scoring them against the golden answer.

        Args:
            question (str): The problem or question to be solved.
            partial_solution (str, optional): A partial solution to build
                upon. This canbe used to guide the search process with
                existing progress. (default::obj:`""`)

        Returns:
            tuple[str, bool]: A tuple containing:
                - str: The best solution found
                (or empty string if no solution found)
                - bool: True if a correct solution was found, False otherwise
        """
        logger.info("Starting Monte Carlo Tree Search")
        best_solution = ""  # Initialize as empty string instead of None
        best_score: float = 0.0
        for i in range(self.search_limit):
            # Generate new answer
            current_solution = self.get_answer(question, partial_solution)
            # Verify answer
            is_correct = self.verify_answer(question, current_solution)
            if is_correct:
                logger.info("Correct answer found! Stopping search")
                return current_solution, True
            prompt = (
                f"Please evaluate this solution and "
                f"give a score between 0-1:\n"
                f"Question: {question}\n"
                f"Solution: {current_solution}\n"
                f"Correct answer: {self.golden_answers.get(question, '')}\n"
                f"Return a JSON object with a single field 'score' containing "
                f"a float between 0 and 1, like this: {{'score': 0.85}}\n"
            )
            self.chat_agent.reset()
            response = self.chat_agent.step(prompt)
            try:
                response_json = response.msgs[0].content.strip()
                agent_response = AgentResponse.parse_raw(response_json)
                score = agent_response.score
                if score > best_score:
                    best_score = score
                    best_solution = current_solution
                    # Exit early if we find a very good solution (score > 0.9)
                    if score > 0.9:
                        logger.info(
                            "Found excellent solution with score %.2f. "
                            "Stopping search early.",
                            score,
                        )
                        return best_solution, False
                logger.info(
                    "Current search progress: %d/%d, best score: %.2f",
                    i + 1,
                    self.search_limit,
                    best_score,
                )
            except Exception as e:
                logger.error("Error parsing agent response: %s", str(e))
                continue
        return best_solution, False

    def binary_search_error(self, question: str, solution: str) -> int:
        r"""Use binary search to locate the first error in the solution.
        This method splits the solution into sentences using
        both English and Chinese
        sentence delimiters and performs binary search to find the first error.

        Args:
            question (str): The question being solved.
            solution (str): The complete solution to analyze.

        Returns:
            int: The position of the first error found in the solution.
            Returns -1.if no errors are found (all sentences are correct).
        """
        logger.info("Starting binary search for error location")
        # Split by both English period and Chinese period
        sentences = [
            s.strip()
            for s in solution.replace('。', '.').split('.')
            if s.strip()
        ]

        # First check if the entire solution is correct
        if self.verify_answer(question, solution):
            return -1

        left, right = 0, len(sentences)
        while left < right:
            mid = (left + right) // 2
            partial_solution = '. '.join(sentences[:mid]) + '.'
            logger.info("Checking solution fragment:\n%s", partial_solution)
            # Verify if the current part is correct
            is_correct = self.verify_answer(question, partial_solution)
            if is_correct:
                left = mid + 1
            else:
                right = mid
        logger.info("First error position found: sentence %d", left)
        return left

    def solve(self, question: str) -> str:
        r"""Main process to solve the problem.

        This method attempts to solve the problem through the following steps:
        1. Get an initial solution
        2. If not correct, use Monte Carlo Tree Search
        3. If still not correct, use binary search to locate errors
        4. Generate a new solution based on the correct parts

        Args:
            question (str): The question to solve.

        Returns:
            str: The final solution to the question.
        """
        logger.info("\n=== Starting to solve the problem: %s ===", question)
        # 1. Get initial solution
        solution = self.get_answer(question)
        if self.verify_answer(question, solution):
            logger.info("Initial solution is correct")
            return solution

        # 2. Try Monte Carlo Tree Search
        solution, is_correct = self.monte_carlo_tree_search(question)
        if is_correct:
            logger.info("Monte Carlo Tree Search found correct solution")
            return solution

        # 3. If the answer is not completely correct,
        #  use binary search to locate the error
        error_pos = self.binary_search_error(question, solution)

        # If no errors found (error_pos == -1), return the current solution
        if error_pos == -1:
            logger.info("No errors found in the solution")
            return solution

        # 4. Generate new solution based on correct part
        correct_part = '. '.join(solution.split('. ')[:error_pos]) + '.'
        final_solution = self.get_answer(question, correct_part)
        self.solution_tree[question] = {
            "solution": final_solution,
            "correct_part": correct_part,
            "error_position": error_pos,
        }
        logger.info("Final solution generated")
        return final_solution

    def import_qa_from_json(self, data: Union[str, Dict[str, str]]) -> bool:
        r"""Import question and answer data
            from either a JSON file or a dictionary.

        Args:
            data (Union[str, Dict[str, str]]): Either a path to a JSON file
                containing QA pairs or a dictionary of question-answer pairs.
                If a string is provided, it's treated as a file path.
                The expected format is:
                {"question1": "answer1",
                 "question2": "answer2",
                 ...}

        Returns:
            bool: True if import was successful, False otherwise.
        """
        try:
            if isinstance(data, str):
                logger.info("Loading QA pairs from file: %s", data)
                with open(data, 'r', encoding='utf-8') as f:
                    qa_data = json.load(f)
            else:
                logger.info("Loading QA pairs from provided dictionary")
                qa_data = data

            # Validate the data format
            if not isinstance(qa_data, dict):
                logger.error("Invalid data format: expected dictionary")
                return False

            # Update golden answers
            self.golden_answers.update(qa_data)
            logger.info("Successfully imported %d QA pairs", len(qa_data))
            return True

        except Exception as e:
            logger.error("Error importing QA data: %s", str(e))
            return False

    def export_solutions(self, filepath: str = 'solutions.json') -> None:
        r"""
        Export the solution process and results to a JSON file.
        Exports the solution tree, golden answers,
         and export timestamp to a JSON file.
        The exported data includes:
        - solutions: The solution tree
            with intermediate steps
        - golden_answers: The reference answers used for verification
        - export_time: ISO format timestamp of the export

        Args:
            filepath (str, optional): Path where the JSON file will be saved.
                Defaults to 'solutions.json'.

        Returns:None: The method writes to a file and logs
        the result but does not return any value.
        """
        export_data = {
            "solutions": self.solution_tree,
            "golden_answers": self.golden_answers,
            "export_time": datetime.now().isoformat(),
        }
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Solutions exported successfully to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting solutions: {e!s}")
