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


from collections import defaultdict
import os
from datetime import datetime

from camel.logger import get_logger, enable_logging

# Enable logging if needed
enable_logging()

# Get a logger for this module
logger = get_logger('o1datagen')


class O1DataGene:
    def __init__(self, chat_agent, golden_answers=None, search_limit=100):
        self.chat_agent = chat_agent
        self.golden_answers = golden_answers if golden_answers else {}
        self.search_limit = search_limit
        self.solution_tree = defaultdict(dict)  # Store correct solution steps
        logger.info("O1DataGene initialized with search_limit=%d", search_limit)

    def get_answer(self, question, context=""):
        """
        Get the AI's thought process and answer
        """
        prompt = f"""Please think step by step and solve this problem: {question}
        Existing content: {context}
        Requirements:
        1. Analyze the problem requirements
        2. List the steps to solve the problem
        3. Execute the solution process
        4. Provide the final answer
        Please explain the thought process of each step in detail.
        """
        response = self.chat_agent.step(prompt)
        answer = response.msgs[0].content
        logger.info("AI thought process:\n%s", answer)
        return answer

    def verify_answer(self, question, answer):
        """
        Verify if the answer is correct
        """
        prompt = f"""Please determine if the following two answers express the same meaning:
        Question: {question}
        Answer 1: {answer}
        Answer 2: {self.golden_answers[question]}
        Just answer "True" or "False".
        """
        response = self.chat_agent.step(prompt)
        is_correct = response.msgs[0].content.strip().lower() == "true"
        logger.info("Answer verification result: %s", is_correct)
        return is_correct

    def monte_carlo_tree_search(self, question, partial_solution=""):
        """
        Generate and verify answers using Monte Carlo Tree Search
        """
        logger.info("Starting Monte Carlo Tree Search")
        best_solution = None
        best_score = 0
        for i in range(self.search_limit):
            # Generate new answer
            current_solution = self.get_answer(question, partial_solution)
            # Verify answer
            is_correct = self.verify_answer(question, current_solution)
            if is_correct:
                logger.info("Correct answer found! Stopping search")
                return current_solution, True
            # Analyze error, get similarity score
            prompt = f"""Analyze the similarity of this answer to the correct answer (between 0-1):
            Question: {question}
            Generated answer: {current_solution}
            Correct answer: {self.golden_answers[question]}
            Just return a number between 0-1.
            """
            response = self.chat_agent.step(prompt)
            try:
                score = float(response.msgs[0].content.strip())
                if score > best_score:
                    best_score = score
                    best_solution = current_solution
                logger.info("Current search progress: %d/%d, best score: %.2f", i+1, self.search_limit, best_score)
            except ValueError:
                continue
        return best_solution, False

    def binary_search_error(self, question, solution):
        """
        Use binary search to locate the first error
        """
        logger.info("Starting binary search for error location")
        sentences = solution.split('。')
        left, right = 0, len(sentences)
        while left < right:
            mid = (left + right) // 2
            partial_solution = '。'.join(sentences[:mid]) + '。'
            logger.info("Checking solution fragment:\n%s", partial_solution)
            # Verify if the current part is correct
            is_correct = self.verify_answer(question, partial_solution)
            if is_correct:
                left = mid + 1
            else:
                right = mid
        error_position = left
        logger.info("First error position found: sentence %d", error_position)
        return error_position

    def solve(self, question):
        """
        Main process to solve the problem
        """
        logger.info("\n=== Starting to solve the problem: %s ===", question)
        # 1. Use Monte Carlo Tree Search to generate answer
        solution, is_correct = self.monte_carlo_tree_search(question)
        if is_correct:
            logger.info("Problem solved!")
            self.solution_tree[question] = {
                "solution": solution,
                "is_correct": True,
                "timestamp": datetime.now().isoformat()
            }
            return solution
        # 2. If the answer is not completely correct, use binary search to locate the error
        error_pos = self.binary_search_error(question, solution)
        # 3. Store the correct part
        correct_part = '。'.join(solution.split('。')[:error_pos]) + '。'
        final_solution = self.get_answer(question, correct_part)
        self.solution_tree[question] = {
            "solution": final_solution,
            "partial_correct": correct_part,
            "error_position": error_pos,
            "is_correct": False,
            "timestamp": datetime.now().isoformat()
        }
        logger.info("Final answer:\n%s", final_solution)
        return final_solution

    def import_qa_from_json(self, json_file_path):
        """
        Import question and answer data from JSON file
        JSON format should be: {"question1": "answer1", "question2": "answer2", ...}
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                qa_data = json.load(f)
            # Update golden_answers
            self.golden_answers.update(qa_data)
            logger.info(f"Successfully imported {len(qa_data)} QA pairs from {json_file_path}")
            return True
        except Exception as e:
            logger.error(f"Error importing JSON data: {str(e)}")
            return False

    def export_solutions(self, filepath='solutions.json'):
        """
        Export the solution process and results to a JSON file
        """
        export_data = {
            "solutions": self.solution_tree,
            "golden_answers": self.golden_answers,
            "export_time": datetime.now().isoformat()
        }
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Solutions exported successfully to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting solutions: {str(e)}")
