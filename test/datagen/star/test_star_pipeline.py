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
            batch_size=10,
            max_workers=4,
        )
        self.assertEqual(len(pipeline.problems), 1)
        self.assertEqual(pipeline.max_iterations, 3)
        self.assertEqual(pipeline.score_threshold, 0.7)
        self.assertIsNone(pipeline.reward_model)
        self.assertIsNone(pipeline.evaluator)
        self.assertIsNone(pipeline.few_shot_examples)
        self.assertEqual(pipeline.batch_processor.batch_size, 10)
        self.assertEqual(pipeline.batch_processor.max_workers, 4)

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
            MagicMock(msg=MagicMock(content="Initial reasoning trace")),
        ]
        mock_evaluate_responses = [
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

    def test_score_threshold_dict(self):
        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=self.test_problems,
            score_threshold={"correctness": 0.8, "clarity": 0.7},
        )

        # Test with scores meeting thresholds
        scores = {"correctness": 0.9, "clarity": 0.8, "completeness": 0.6}
        self.assertTrue(pipeline._check_score_threshold(scores))

        # Test with scores below thresholds
        scores = {"correctness": 0.7, "clarity": 0.6, "completeness": 0.9}
        self.assertFalse(pipeline._check_score_threshold(scores))

    @patch("builtins.open")
    @patch("json.dump")
    @patch("json.load")
    def test_generate_with_output(self, mock_load, mock_dump, mock_open):
        mock_load.return_value = {"traces": []}
        mock_open.return_value.__enter__ = mock_open
        mock_open.return_value.__exit__ = MagicMock()

        mock_reason_responses = [
            MagicMock(msg=MagicMock(content="Initial reasoning trace")),
            MagicMock(msg=MagicMock(content="Improved reasoning trace")),
        ]
        mock_evaluate_responses = [
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
            MagicMock(
                msg=MagicMock(
                    parsed={
                        "correctness": 0.98,
                        "clarity": 0.95,
                        "completeness": 0.98,
                        "feedback": "Perfect explanation",
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
            max_iterations=1,
            score_threshold=0.99,
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
        mock_dump.assert_called()
        args = mock_dump.call_args_list[-1][0]  # Get last call args
        expected_result = {
            "traces": [
                {
                    "id": "problem_0",
                    "type": "arithmetic",
                    "problem": "If John has 5 apples and gives 2 to Mary, "
                    "how many does he have left?",
                    "solution": "3",
                    "final_trace": "Improved reasoning trace",
                    "evaluate_success": False,
                    "boxed_answer_success": False,
                    "improvement_history": [
                        {
                            "iteration": 1,
                            "trace": "Initial reasoning trace",
                            "evaluation": {
                                "correctness": 0.95,
                                "clarity": 0.9,
                                "completeness": 0.95,
                                "feedback": "Excellent explanation",
                            },
                        }
                    ],
                }
            ]
        }
        self.assertEqual(args[0], expected_result)

    def test_invalid_problem_format(self):
        test_cases = [
            (
                {"id": "problem_0", "type": "arithmetic"},
                "Problem dictionary must contain 'problem' key.",
            ),
            ({"problem": 123}, "Problem 'problem' field must be a string."),
            (
                {"problem": "test", "id": []},
                "Problem 'id' must be of type (<class 'str'>, <class 'int'>"
                ", <class 'NoneType'>) if present.",
            ),
            (
                {"problem": "test", "type": 123},
                "Problem 'type' must be of type str if present.",
            ),
            (
                {"problem": "test", "solution": 123},
                "Problem 'solution' must be of type str if present.",
            ),
        ]

        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=[],
        )

        for invalid_problem, expected_error in test_cases:
            with self.assertRaises(ValueError) as context:
                pipeline.validate_problem_format(invalid_problem)
            self.assertIn(expected_error, str(context.exception))

    def test_batch_processing(self):
        # Test with multiple problems
        test_problems = [
            {
                "id": f"problem_{i}",
                "problem": f"Test problem {i}",
                "type": "test",
                "solution": str(i),
            }
            for i in range(3)
        ]

        # Create enough mock responses for all iterations
        mock_reason_responses = [
            MagicMock(
                msg=MagicMock(
                    content=f"Reasoning trace for {problem['problem']}"
                )
            )
            for problem in test_problems
        ]
        mock_evaluate_responses = [
            MagicMock(
                msg=MagicMock(
                    parsed={
                        "correctness": 0.9,
                        "clarity": 0.9,
                        "completeness": 0.9,
                        "feedback": f"Feedback for {problem['problem']}",
                    }
                )
            )
            for problem in test_problems
        ]

        self.mock_reason_agent.step.side_effect = mock_reason_responses
        self.mock_evaluate_agent.step.side_effect = mock_evaluate_responses

        pipeline = STaRPipeline(
            reason_agent=self.mock_reason_agent,
            evaluate_agent=self.mock_evaluate_agent,
            problems=test_problems,
            batch_size=2,  # Small batch size to test batching
            max_workers=2,
        )

        results = pipeline.generate()

        # Verify results
        self.assertEqual(len(results), 3)

        # Create a map of problem text to expected trace
        expected_traces = {
            problem["problem"]: f"Reasoning trace for {problem['problem']}"
            for problem in test_problems
        }

        # Verify each result matches its corresponding problem
        for result in results:
            problem_text = result["problem"]
            self.assertIn(problem_text, expected_traces)
            self.assertEqual(
                result["final_trace"], expected_traces[problem_text]
            )


if __name__ == "__main__":
    unittest.main()
