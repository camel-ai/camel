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

import unittest
from unittest.mock import MagicMock, patch

from camel.agents import ChatAgent
from camel.datagen import STaRPipeline
from camel.datagen.star.star_pipeline import (
    ProblemResult,
    TraceIteration,
)
from camel.models.reward import BaseRewardModel


class TestSTaRPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_reason_agent = MagicMock(spec=ChatAgent)
        self.mock_reason_agent.step.return_value = MagicMock(
            msg=MagicMock(content="Mock reasoning trace")
        )

        self.mock_evaluate_agent = MagicMock(spec=ChatAgent)
        self.mock_evaluate_agent.step.return_value = MagicMock(
            msg=MagicMock(
                parsed={
                    "correctness": 0.8,
                    "clarity": 0.9,
                    "completeness": 0.85,
                    "feedback": "Good explanation",
                }
            )
        )

        self.test_problems = [
            {
                "id": "problem_0",
                "problem": (
                    "If John has 5 apples and gives 2 to Mary, "
                    "how many does he have left?"
                ),
                "type": "arithmetic",
                "solution": "3",
            }
        ]

    def test_pipeline_initialization(self):
        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
        )
        self.assertEqual(len(pipeline.problems), 1)
        self.assertEqual(pipeline.max_iterations, 3)
        self.assertEqual(pipeline.score_threshold, 0.7)
        self.assertIsNone(pipeline.reward_model)
        self.assertIsNone(pipeline.evaluator)
        self.assertIsNone(pipeline.few_shot_examples)

    def test_pipeline_initialization_with_few_shot(self):
        few_shot = "Example: 2 + 2 = 4"
        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
            few_shot_examples=few_shot,
        )
        self.assertEqual(pipeline.few_shot_examples, few_shot)

    def test_generate_reasoning_trace(self):
        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
        )
        trace = pipeline.generate_reasoning_trace(
            self.test_problems[0]["problem"]
        )
        self.assertEqual(trace, "Mock reasoning trace")
        self.mock_reason_agent.reset.assert_called_once()
        self.mock_reason_agent.step.assert_called_once()

    def test_agent_evaluate_trace(self):
        evaluation_response = {
            "correctness": 0.8,
            "clarity": 0.9,
            "completeness": 0.85,
            "feedback": "Good explanation, but could be more detailed",
        }
        self.mock_evaluate_agent.step.return_value = MagicMock(
            msg=MagicMock(parsed=evaluation_response)
        )

        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
        )

        evaluation = pipeline.evaluate_trace(
            self.test_problems[0]["problem"],
            "Test reasoning trace",
        )

        self.assertIsInstance(evaluation, dict)
        self.assertEqual(evaluation["correctness"], 0.8)
        self.assertEqual(evaluation["clarity"], 0.9)
        self.assertEqual(evaluation["completeness"], 0.85)
        self.assertEqual(
            evaluation["feedback"],
            "Good explanation, but could be more detailed",
        )

    def test_reward_model_single_score_evaluation(self):
        mock_reward_model = MagicMock(spec=BaseRewardModel)
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = 0.85

        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
            reward_model=mock_reward_model,
        )
        pipeline.evaluator = mock_evaluator

        evaluation = pipeline.evaluate_trace(
            self.test_problems[0]["problem"],
            "Test reasoning trace",
        )

        self.assertIsInstance(evaluation, dict)
        self.assertEqual(evaluation["overall"], 0.85)
        self.assertIn("feedback", evaluation)

    def test_reward_model_multi_score_evaluation(self):
        mock_reward_model = MagicMock(spec=BaseRewardModel)
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {
            "correctness": 0.8,
            "coherence": 0.9,
            "helpfulness": 0.85,
        }

        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
            reward_model=mock_reward_model,
        )
        pipeline.evaluator = mock_evaluator

        evaluation = pipeline.evaluate_trace(
            self.test_problems[0]["problem"],
            "Test reasoning trace",
        )

        self.assertIsInstance(evaluation, dict)
        self.assertEqual(evaluation["correctness"], 0.8)
        self.assertEqual(evaluation["coherence"], 0.9)
        self.assertEqual(evaluation["helpfulness"], 0.85)
        self.assertIn("feedback", evaluation)

    def test_improve_trace(self):
        improved_trace = "Improved reasoning with more details"
        self.mock_reason_agent.step.return_value = MagicMock(
            msg=MagicMock(content=improved_trace)
        )

        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
        )

        result = pipeline.improve_trace(
            self.test_problems[0]["problem"],
            "Original trace",
            "Add more details",
        )

        self.assertEqual(result, improved_trace)
        self.mock_reason_agent.reset.assert_called_once()
        self.mock_reason_agent.step.assert_called_once()

    def test_process_problem(self):
        # Mock responses for the process_problem pipeline
        mock_reason_responses = [
            # Initial reasoning trace
            MagicMock(msg=MagicMock(content="Initial reasoning trace")),
        ]
        mock_evaluate_responses = [
            # Evaluation response
            MagicMock(
                msg=MagicMock(
                    parsed={
                        "correctness": 0.95,
                        "clarity": 0.9,
                        "completeness": 0.95,
                        "feedback": "Excellent explanation",
                    }
                )
            ),
        ]
        self.mock_reason_agent.step.side_effect = mock_reason_responses
        self.mock_evaluate_agent.step.side_effect = mock_evaluate_responses

        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
        )

        result = pipeline.process_problem(self.test_problems[0])

        self.assertIsInstance(result, ProblemResult)
        self.assertEqual(result.problem, self.test_problems[0]["problem"])
        self.assertEqual(result.final_trace, "Initial reasoning trace")
        self.assertEqual(len(result.improvement_history), 1)
        self.assertIsInstance(result.improvement_history[0], TraceIteration)

    def test_process_problem_with_rationalization(self):
        # Mock responses for the process_problem pipeline with rationalization
        mock_reason_responses = [
            # Initial reasoning trace
            MagicMock(msg=MagicMock(content="Initial reasoning trace")),
            # Improved trace after rationalization
            MagicMock(msg=MagicMock(content="Improved reasoning trace")),
        ]
        mock_evaluate_responses = [
            # First evaluation
            MagicMock(
                msg=MagicMock(
                    parsed={
                        "correctness": 0.6,
                        "clarity": 0.5,
                        "completeness": 0.6,
                        "feedback": "Needs improvement",
                    }
                )
            ),
            # Second evaluation after improvement
            MagicMock(
                msg=MagicMock(
                    parsed={
                        "correctness": 0.9,
                        "clarity": 0.9,
                        "completeness": 0.9,
                        "feedback": "Much better",
                    }
                )
            ),
        ]
        self.mock_reason_agent.step.side_effect = mock_reason_responses
        self.mock_evaluate_agent.step.side_effect = mock_evaluate_responses

        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
            score_threshold=0.8,  # Set high threshold to trigger improvement
        )

        result = pipeline.process_problem(
            self.test_problems[0], rationalization=True
        )

        self.assertIsInstance(result, ProblemResult)
        self.assertEqual(result.problem, self.test_problems[0]["problem"])
        self.assertEqual(result.final_trace, "Improved reasoning trace")
        self.assertEqual(len(result.improvement_history), 2)
        self.assertIsInstance(result.improvement_history[0], TraceIteration)
        self.assertIsInstance(result.improvement_history[1], TraceIteration)

    @patch("json.dump")
    def test_generate_with_output(self, mock_dump):
        # Mock responses for the full pipeline
        mock_reason_responses = [
            # Initial reasoning trace
            MagicMock(msg=MagicMock(content="Initial reasoning trace")),
        ]
        mock_evaluate_responses = [
            # Evaluation response
            MagicMock(
                msg=MagicMock(
                    parsed={
                        "correctness": 0.95,
                        "clarity": 0.9,
                        "completeness": 0.95,
                        "feedback": "Excellent explanation",
                    }
                )
            ),
        ]
        self.mock_reason_agent.step.side_effect = mock_reason_responses
        self.mock_evaluate_agent.step.side_effect = mock_evaluate_responses

        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
            output_path="test_output.json",
        )

        results = pipeline.generate()

        # Verify the results structure
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertIn("problem", result)
        self.assertIn("final_trace", result)
        self.assertIn("improvement_history", result)

        # Verify output was written
        mock_dump.assert_called_once()
        args = mock_dump.call_args[0]
        self.assertEqual(args[0], {"traces": results})

    def test_invalid_problem_format(self):
        invalid_problem = {"id": "problem_0", "type": "arithmetic"}
        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=[invalid_problem],
        )

        with self.assertRaises(ValueError) as context:
            pipeline.process_problem(invalid_problem)

        self.assertIn(
            "Each problem dictionary must contain a 'problem' key",
            str(context.exception),
        )


if __name__ == "__main__":
    unittest.main()
