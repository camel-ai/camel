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
import unittest
from unittest.mock import MagicMock, mock_open, patch

from camel.agents import ChatAgent
from camel.datagen.star import STaRPipeline


class TestSTaRPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_agent = MagicMock(spec=ChatAgent)
        self.mock_agent.step.return_value = MagicMock(
            msg=MagicMock(content="Mock reasoning trace")
        )

        self.test_problems = {
            "problems": [
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
        }

        self.exists_patch = patch("os.path.exists", return_value=True)
        self.mock_exists = self.exists_patch.start()

        self.open_patch = patch(
            "builtins.open",
            mock_open(read_data=json.dumps(self.test_problems)),
        )
        self.mock_open = self.open_patch.start()

    def tearDown(self):
        self.exists_patch.stop()
        self.open_patch.stop()

    def test_pipeline_initialization(self):
        pipeline = STaRPipeline(
            agent=self.mock_agent, problems_path="test_problems.json"
        )
        self.assertEqual(len(pipeline.problems), 1)
        self.assertEqual(pipeline.max_iterations, 3)
        self.assertEqual(pipeline.score_threshold, 0.9)

    def test_generate_reasoning_trace(self):
        pipeline = STaRPipeline(
            agent=self.mock_agent, problems_path="test_problems.json"
        )
        trace = pipeline.generate_reasoning_trace(
            self.test_problems["problems"][0]["problem"]
        )
        self.assertEqual(trace, "Mock reasoning trace")
        self.mock_agent.step.assert_called_once()

    def test_evaluate_trace(self):
        evaluation_response = {
            "correctness": 0.8,
            "clarity": 0.9,
            "completeness": 0.85,
            "feedback": "Good explanation, but could be more detailed",
        }
        self.mock_agent.step.return_value = MagicMock(
            msg=MagicMock(content=json.dumps(evaluation_response))
        )

        pipeline = STaRPipeline(
            agent=self.mock_agent, problems_path="test_problems.json"
        )

        evaluation = pipeline.evaluate_trace(
            self.test_problems["problems"][0]["problem"],
            "Test reasoning trace",
        )

        self.assertIsInstance(evaluation, dict)
        self.assertIn("correctness", evaluation)
        self.assertIn("clarity", evaluation)
        self.assertIn("completeness", evaluation)
        self.assertIn("feedback", evaluation)
        self.assertEqual(evaluation["correctness"], 0.8)
        self.assertEqual(evaluation["clarity"], 0.9)

    def test_improve_trace(self):
        improved_trace = "Improved reasoning with more details"
        self.mock_agent.step.return_value = MagicMock(
            msg=MagicMock(content=improved_trace)
        )

        pipeline = STaRPipeline(
            agent=self.mock_agent, problems_path="test_problems.json"
        )

        result = pipeline.improve_trace(
            self.test_problems["problems"][0]["problem"],
            "Original trace",
            "Add more details",
        )

        self.assertEqual(result, improved_trace)
        self.mock_agent.step.assert_called_once()

    @patch("json.dump")
    def test_full_pipeline_execution(self, mock_dump):
        # Mock responses for the full pipeline
        mock_responses = [
            # Initial reasoning trace
            MagicMock(msg=MagicMock(content="Initial reasoning trace")),
            # Evaluation response
            MagicMock(
                msg=MagicMock(
                    content=json.dumps(
                        {
                            "correctness": 0.95,
                            "clarity": 0.9,
                            "completeness": 0.95,
                            "feedback": "Excellent explanation",
                        }
                    )
                )
            ),
        ]
        self.mock_agent.step.side_effect = mock_responses

        pipeline = STaRPipeline(
            agent=self.mock_agent,
            problems_path="test_problems.json",
            output_path="test_output.json",
        )

        pipeline.generate()

        # Verify the output was written
        mock_dump.assert_called_once()
        args, kwargs = mock_dump.call_args
        self.assertIsInstance(args[0], list)

        # Verify the structure of the output
        output = args[0]
        self.assertEqual(len(output), 1)
        self.assertIn("problem", output[0])
        self.assertIn("final_trace", output[0])
        self.assertIn("improvement_history", output[0])

    def test_invalid_json_evaluation(self):
        # Test handling of invalid JSON in evaluation response
        self.mock_agent.step.return_value = MagicMock(
            msg=MagicMock(content="Invalid JSON response")
        )

        pipeline = STaRPipeline(
            agent=self.mock_agent, problems_path="test_problems.json"
        )

        with self.assertRaises(json.JSONDecodeError):
            pipeline.evaluate_trace(
                self.test_problems["problems"][0]["problem"],
                "Test reasoning trace",
            )


if __name__ == "__main__":
    unittest.main()
