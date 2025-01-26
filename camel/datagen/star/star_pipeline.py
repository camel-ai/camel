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
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.models.reward import BaseRewardModel, Evaluator


class AgentTraceEvaluation(BaseModel):
    correctness: float
    clarity: float
    completeness: float
    feedback: str


class RewardTraceEvaluation(BaseModel):
    feedback: str

    def __init__(self, **data):
        # Allow dynamic score fields while ensuring feedback is present
        super().__init__(**data)

    class Config:
        extra = (
            "allow"  # Allow extra fields for different reward model dimensions
        )


class TraceIteration(BaseModel):
    iteration: int
    trace: str
    evaluation: Union[AgentTraceEvaluation, RewardTraceEvaluation]


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
        problems (List[Dict]): List of problem dictionaries to process.
        max_iterations (int, optional): Max iterations.
            (default: :obj:`3`)
        score_threshold (Union[float, Dict[str, float]], optional): Quality
            threshold. Can be either a single float value applied to all score,
            or a dictionary mapping score dimensions to their thresholds. For
            example: {"correctness": 0.8, "coherence": 0.7} If using reward
            model and threshold for a dimension is not specified, will use the
            default value 0.7. (default: :obj:`0.7`)
        reward_model (BaseRewardModel, optional): Model used for evaluating
            reasoning traces. If None, uses Agent self-evaluation.
            (default: :obj:`None`)
        output_path (str, optional): Output path for saving traces. If None,
            results will only be returned without saving to file.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        agent: ChatAgent,
        problems: List[Dict],
        max_iterations: int = 3,
        score_threshold: Union[float, Dict[str, float]] = 0.7,
        reward_model: Optional[BaseRewardModel] = None,
        output_path: Optional[str] = None,
    ):
        r"""Initialize the STaR pipeline.

        Args:
            agent (ChatAgent): The chat agent used for generating and improving
                reasoning traces.
            problems (List[Dict]): List of problem dictionaries to process.
            max_iterations (int, optional): Max Iterations
                (default: :obj:`3`)
            score_threshold (Union[float, Dict[str, float]], optional):
                Quality threshold. Can be either a single float value applied
                to average score, or a dictionary mapping score dimensions to
                their thresholds. For example: {"correctness": 0.8,
                "coherence": 0.7}. If using reward model and threshold for a
                dimension is not specified, will use the default value 0.7.
                (default: :obj:`0.7`)
            reward_model (BaseRewardModel, optional): Model used to evaluate
                reasoning traces. If None, uses Agent self-evaluation.
                (default: :obj:`None`)
            output_path (str, optional): Output path for saving traces. If
                `None`, results will only be returned without saving to file.
                (default: :obj:`None`)
        """
        self.agent = agent
        self.problems = problems
        self.output_path = output_path
        self.max_iterations = max_iterations
        self.score_threshold = score_threshold
        self.reward_model = reward_model
        self.evaluator = (
            Evaluator(reward_model=reward_model) if reward_model else None
        )
        self.reasoning_traces: List[Dict[str, Any]] = []

    def _check_score_threshold(self, scores: Dict[str, float]) -> bool:
        r"""Check if scores meet the threshold requirements.

        Args:
            scores (Dict[str, float]): Dictionary of scores for different
                dimensions.

        Returns:
            bool: True if scores meet threshold requirements, False otherwise.
        """
        # If score_threshold is a float, apply it to all dimensions
        if isinstance(self.score_threshold, float):
            return all(
                score >= self.score_threshold for score in scores.values()
            )

        # If score_threshold is a dict, check each dimension with its threshold
        # Use 0 as default threshold for unspecified dimensions
        if isinstance(self.score_threshold, dict):
            for dim, score in scores.items():
                threshold = self.score_threshold.get(dim, 0)
                if score < threshold:
                    return False
            return True

        # If score_threshold is None or invalid type, pass the check
        return True

    def _generate_feedback(self, scores: Dict[str, float]) -> str:
        r"""Generate feedback based on which dimensions need improvement.

        Args:
            scores (Dict[str, float]): Dictionary of scores for different
                dimensions.

        Returns:
            str: Feedback message indicating which dimensions need improvement.
        """
        if isinstance(self.score_threshold, float):
            below_threshold = [
                dim
                for dim, score in scores.items()
                if score < self.score_threshold
            ]
            if not below_threshold:
                return "All dimensions meet the required threshold"
            dims = ", ".join(below_threshold)
            return f"Need improvement in: {dims}"

        if isinstance(self.score_threshold, dict):
            default_threshold = 0
            below_threshold = [
                dim
                for dim, score in scores.items()
                if score < self.score_threshold.get(dim, default_threshold)
            ]
            if not below_threshold:
                return "All dimensions meet their respective thresholds"
            dims = ", ".join(below_threshold)
            return f"Need improvement in: {dims}"

        # If no threshold set, just list all dimensions and their scores
        dims = ", ".join(
            f"{dim}: {score:.2f}" for dim, score in scores.items()
        )
        return f"Current scores - {dims}"

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
            Dict[str, Any]: Evaluation results containing:
                - scores: Dict of evaluation dimensions and their scores
                - feedback: Detailed feedback for improvement

                For Agent self-evaluation, the scores will include:
                - correctness: Score for logical correctness
                - clarity: Score for clarity of explanation
                - completeness: Score for completeness of reasoning

                For reward model evaluation, the scores will depend on
                the model's evaluation dimensions.
        """
        self.agent.reset()
        if self.evaluator:
            # Use reward model evaluation
            messages = [
                {"role": "user", "content": problem},
                {"role": "assistant", "content": trace},
            ]
            scores = self.evaluator.evaluate(messages)

            # For models that return a single score
            if isinstance(scores, (int, float)) or (
                isinstance(scores, dict) and len(scores) == 1
            ):
                if isinstance(scores, dict):
                    score = next(iter(scores.values()))
                else:
                    score = scores
                scores_dict = {"overall": score}
                return {
                    **scores_dict,
                    "feedback": self._generate_feedback(scores_dict),
                }

            # For models that return multiple dimensions
            return {**scores, "feedback": self._generate_feedback(scores)}
        else:
            # Fallback to original Agent self-evaluation
            prompt = self.EVALUATION_TEMPLATE.format(
                problem=problem, trace=trace
            )
            response = self.agent.step(
                prompt, response_format=AgentTraceEvaluation
            )
            if response.msg.parsed is None:
                raise AttributeError("Failed to parse evaluation response")
            # Convert dict to AgentTraceEvaluation if needed
            if isinstance(response.msg.parsed, dict):
                evaluation = AgentTraceEvaluation(**response.msg.parsed)
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

    def process_problem(self, problem: Dict) -> ProblemResult:
        r"""Process a single problem through the STaR pipeline.

        Args:
            problem (Dict): Problem dictionary containing the problem text.

        Returns:
            ProblemResult: Results with final trace and history.
        """
        if "problem" not in problem:
            raise ValueError(
                "Each problem dictionary must contain a 'problem' key."
            )

        problem_text = problem["problem"]
        current_trace = self.generate_reasoning_trace(problem_text)
        improvement_history = []

        for iteration in range(self.max_iterations):
            # Evaluate current trace
            eval_dict = self.evaluate_trace(problem_text, current_trace)
            scores = {k: v for k, v in eval_dict.items() if k != "feedback"}

            # Record iteration history
            if self.evaluator:
                improvement_history.append(
                    TraceIteration(
                        iteration=iteration,
                        trace=current_trace,
                        evaluation=RewardTraceEvaluation(**eval_dict),
                    )
                )
            else:
                improvement_history.append(
                    TraceIteration(
                        iteration=iteration,
                        trace=current_trace,
                        evaluation=AgentTraceEvaluation(
                            **scores, feedback=eval_dict["feedback"]
                        ),
                    )
                )

            # Check if quality threshold met
            if self._check_score_threshold(scores):
                break

            # Generate improved trace
            current_trace = self.improve_trace(
                problem_text, current_trace, eval_dict["feedback"]
            )

        return ProblemResult(
            problem=problem_text,
            final_trace=current_trace,
            improvement_history=improvement_history,
        )

    def generate(self) -> List[Dict[str, Any]]:
        r"""Execute the STaR pipeline on all problems.

        Process problems and return results. If output_path is specified,
        also save results to file.

        Returns:
            List[Dict[str, Any]]: List of processed results
        """
        for problem in self.problems:
            result = self.process_problem(problem)
            self.reasoning_traces.append(result.model_dump())

        if self.output_path:
            with open(self.output_path, 'w') as f:
                json.dump({'traces': self.reasoning_traces}, f, indent=2)

        return self.reasoning_traces

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
