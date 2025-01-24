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
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.models.reward import BaseRewardModel, Evaluator


class TraceEvaluation(BaseModel):
    correctness: float
    clarity: float
    completeness: float
    feedback: str


class TraceIteration(BaseModel):
    iteration: int
    trace: str
    evaluation: TraceEvaluation


class ProblemResult(BaseModel):
    problem: str
    final_trace: str
    improvement_history: List[TraceIteration]


class STaRPipeline:
    r"""Pipeline for generating self-taught reasoning traces
        using the STaR methodology.

    This implements the STaR paper's approach of:
    1. Initial reasoning trace generation
    2. Self-evaluation
    3. Feedback-based improvement
    4. Iterative refinement

    Args:
        agent (ChatAgent): The chat agent used for generating and improving
            reasoning traces.
        problems_path (str): Path to JSON file containing reasoning problems.
        output_path (str, optional): Output path for saving traces.
            (default: :obj:`'./star_output.json'`)
        max_iterations (int, optional): Max iterations.
            (default: :obj:`3`)
        score_threshold (float, optional): Threshold to stop iterations.
            (default: :obj:`0.7`)
        reward_model (BaseRewardModel, optional): Model used for evaluating
        reasoning traces. If None, uses LLM self-evaluation.
        (default: :obj:`None`)
    """

    def __init__(
        self,
        agent: ChatAgent,
        problems_path: str,
        output_path: Optional[str] = './star_output.json',
        max_iterations: int = 3,
        score_threshold: float = 0.7,
        reward_model: Optional[BaseRewardModel] = None,
    ):
        r"""Initialize the STaR pipeline.

        Args:
            agent (ChatAgent): The chat agent used for generating and improving
                reasoning traces.
            problems_path (str): Path to problems JSON file.
            output_path (str, optional): Output path for saving traces.
                (default: :obj:`'./star_output.json'`)
            max_iterations (int, optional): Max Iterations
                (default: :obj:`3`)
            score_threshold (float, optional): Quality threshold.
                (default: :obj:`0.7`)
            reward_model (BaseRewardModel, optional): Model used to evaluate
            reasoning traces. If None, uses LLM self-evaluation.
            (default: :obj:`None`)
        """
        self.agent = agent
        self.problems = self.load_problems(problems_path)
        self.output_path = output_path
        self.max_iterations = max_iterations
        self.score_threshold = score_threshold
        self.reward_model = reward_model
        self.evaluator = (
            Evaluator(reward_model=reward_model) if reward_model else None
        )
        self.reasoning_traces: List[Dict[str, Any]] = []

    def load_problems(self, path: str) -> List[Dict]:
        r"""Load reasoning problems from JSON file.

        Args:
            path (str): Path to the JSON file containing the problems.

        Returns:
            List[Dict]: List of problem dictionaries loaded from the file.
        """
        with open(path, 'r') as f:
            data = json.load(f)
            return data['problems']

    def generate_reasoning_trace(self, problem: str) -> str:
        r"""Generate initial reasoning trace for a given problem.

        Args:
            problem (str): The problem text to generate reasoning for.

        Returns:
            str: Generated reasoning trace.
        """
        self.agent.reset()
        prompt = self.REASONING_TEMPLATE.format(problem=problem)
        response = self.agent.step(prompt)
        return response.msg.content

    def evaluate_trace(self, problem: str, trace: str) -> Dict[str, Any]:
        r"""Evaluate the quality of a reasoning trace.

        Args:
            problem (str): The original problem text to evaluate against.
            trace (str): The reasoning trace to evaluate.

        Returns:
            TraceEvaluation: Evaluation results containing:
                - correctness (float): Score for logical correctness
                - clarity (float): Score for clarity of explanation
                - completeness (float): Score for completeness of reasoning
                - feedback (str): Detailed feedback for improvement
        """
        self.agent.reset()
        if self.evaluator:
            # Use reward model evaluation
            messages = [
                {"role": "user", "content": problem},
                {"role": "assistant", "content": trace},
            ]
            scores = self.evaluator.evaluate(messages)
            return {
                "correctness": scores.get(
                    "correctness", scores.get("Score", 0)
                )
                / 5.0,
                "clarity": scores.get("coherence", scores.get("Score", 0))
                / 5.0,
                "completeness": scores.get(
                    "helpfulness", scores.get("Score", 0)
                )
                / 5.0,
                "feedback": "Evaluation by reward model",
            }

        else:
            # Fallback to original LLM self-evaluation
            prompt = self.EVALUATION_TEMPLATE.format(
                problem=problem, trace=trace
            )
            response = self.agent.step(prompt, response_format=TraceEvaluation)
            if response.msg.parsed is None:
                raise AttributeError("Failed to parse evaluation response")
            # Convert dict to TraceEvaluation if needed
            if isinstance(response.msg.parsed, dict):
                evaluation = TraceEvaluation(**response.msg.parsed)
            else:
                evaluation = response.msg.parsed

            return evaluation.model_dump()

    def improve_trace(self, problem: str, trace: str, feedback: str) -> str:
        r"""Generate improved reasoning trace based on feedback.

        Args:
            problem (str): The original problem text.
            trace (str): The current reasoning trace.
            feedback (str): Feedback for improving the trace.

        Returns:
            str: Improved reasoning trace.
        """
        self.agent.reset()
        prompt = self.IMPROVEMENT_TEMPLATE.format(
            problem=problem, trace=trace, feedback=feedback
        )
        response = self.agent.step(prompt)
        return response.msg.content

    def process_problem(self, problem: Dict) -> Dict[str, Any]:
        r"""Process a single problem through the STaR pipeline.

        Args:
            problem (Dict): Problem dictionary containing the problem text.

        Returns:
            ProblemResult: Results with final trace and history.
        """
        problem_text = problem['problem']
        current_trace = self.generate_reasoning_trace(problem_text)
        traces = []

        for iteration in range(self.max_iterations):
            # Evaluate current trace
            eval_dict = self.evaluate_trace(problem_text, current_trace)
            evaluation = TraceEvaluation(**eval_dict)

            # Check if quality threshold met
            avg_score = (
                evaluation.correctness
                + evaluation.clarity
                + evaluation.completeness
            ) / 3

            traces.append(
                TraceIteration(
                    iteration=iteration,
                    trace=current_trace,
                    evaluation=evaluation,
                )
            )

            if avg_score >= self.score_threshold:
                break

            # Generate improved trace
            if iteration < self.max_iterations - 1:
                current_trace = self.improve_trace(
                    problem_text, current_trace, evaluation.feedback
                )

        result = ProblemResult(
            problem=problem_text,
            final_trace=current_trace,
            improvement_history=traces,
        )

        return result.model_dump()

    def generate(self):
        r"""Execute the STaR pipeline on all problems.

        Process problems and save results.
        """
        for problem in self.problems:
            result = self.process_problem(problem)
            self.reasoning_traces.append(result)

        if self.output_path:
            with open(self.output_path, 'w') as f:
                json.dump(self.reasoning_traces, f, indent=2)

    # Templates for generating reasoning, evaluation and improving them.
    REASONING_TEMPLATE = """Let's solve this step by step:
Problem: {problem}
1. First, let's understand what we're asked
2. Let's break this down into parts
3. Let's solve each part systematically
4. Finally, let's verify our solution

Please show your complete reasoning process."""

    EVALUATION_TEMPLATE = """Please evaluate this reasoning trace and 
provide scores and feedback in valid JSON format.

Problem: {problem}

Reasoning Trace:
{trace}

Evaluate for:
1. Correctness (Is each step logically sound?)
2. Clarity (Is the explanation clear and well-structured?)
3. Completeness (Are all necessary steps included?)

Respond ONLY with a JSON object in this exact format:
{{
    "correctness": <score between 0 and 1>,
    "clarity": <score between 0 and 1>,
    "completeness": <score between 0 and 1>,
    "feedback": "<specific feedback for improvement>"
}}"""

    IMPROVEMENT_TEMPLATE = """Based on this feedback, generate an 
improved reasoning trace:
Problem: {problem}

Previous Trace:
{trace}

Feedback:
{feedback}

Generate a new, improved reasoning trace that addresses the feedback."""
