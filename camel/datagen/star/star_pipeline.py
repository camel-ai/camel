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

from camel.agents import ChatAgent

from .templates import STaRTemplates


class STaRPipeline:
    """Pipeline for generating self-taught reasoning traces
    using the STaR methodology.

    This implements the STaR paper's approach of:
    1. Initial reasoning trace generation
    2. Self-evaluation
    3. Feedback-based improvement
    4. Iterative refinement
    """

    def __init__(
        self,
        agent: ChatAgent,
        problems_path: str,
        output_path: Optional[str] = './star_output.json',
        max_iterations: int = 3,
        score_threshold: float = 0.9,
    ):
        self.agent = agent
        self.problems = self.load_problems(problems_path)
        self.output_path = output_path
        self.max_iterations = max_iterations
        self.score_threshold = score_threshold
        self.reasoning_traces: List[Dict[str, Any]] = []

    def load_problems(self, path: str) -> List[Dict]:
        """Load reasoning problems from file."""
        with open(path, 'r') as f:
            data = json.load(f)
            return data['problems']

    def generate_reasoning_trace(self, problem: str) -> str:
        """Generate initial reasoning trace."""
        prompt = STaRTemplates.reasoning_template.format(problem=problem)
        response = self.agent.step(prompt)
        return response.msg.content

    def evaluate_trace(self, problem: str, trace: str) -> Dict[str, Any]:
        """Evaluate reasoning trace quality."""
        prompt = STaRTemplates.evaluation_template.format(
            problem=problem, trace=trace
        )
        response = self.agent.step(prompt)
        return json.loads(response.msg.content)

    def improve_trace(self, problem: str, trace: str, feedback: str) -> str:
        """Generate improved reasoning trace based on feedback."""
        prompt = STaRTemplates.improvement_template.format(
            problem=problem, trace=trace, feedback=feedback
        )
        response = self.agent.step(prompt)
        return response.msg.content

    def process_problem(self, problem: Dict) -> Dict[str, Any]:
        """Process a single problem through the STaR pipeline."""
        problem_text = problem['problem']
        current_trace = self.generate_reasoning_trace(problem_text)
        traces = []

        for iteration in range(self.max_iterations):
            # Evaluate current trace
            evaluation = self.evaluate_trace(problem_text, current_trace)

            traces.append(
                {
                    'iteration': iteration,
                    'trace': current_trace,
                    'evaluation': evaluation,
                }
            )

            # Check if quality threshold met
            avg_score = (
                evaluation['correctness']
                + evaluation['clarity']
                + evaluation['completeness']
            ) / 3

            if avg_score >= self.score_threshold:
                break

            # Generate improved trace
            if iteration < self.max_iterations - 1:
                current_trace = self.improve_trace(
                    problem_text, current_trace, evaluation['feedback']
                )

        return {
            'problem': problem_text,
            'final_trace': current_trace,
            'improvement_history': traces,
        }

    def generate(self):
        """Execute the STaR pipeline on all problems."""
        for problem in self.problems:
            result = self.process_problem(problem)
            self.reasoning_traces.append(result)

        if self.output_path:
            with open(self.output_path, 'w') as f:
                json.dump(self.reasoning_traces, f, indent=2)
