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
from unittest.mock import MagicMock, mock_open, patch

from camel.benchmarks import APIBenchBenchmark

# Mock question, API, eval, and ast data
MOCK_QUESTION_DATA = [
    {
        "question_id": 1,
        "text": "How do I use the HuggingFace API for text classification?",
        "domain": "Natural Language Processing Text Classification",
    },
]
MOCK_API_DATA = [
    {
        "api_call": "huggingface_api_call_example",
        "domain": "Natural Language Processing Text Classification",
    }
]
MOCK_EVAL_DATA = [
    {
        "api_call": "huggingface_api_call_example",
        "eval": "huggingface_api_eval_example",
    }
]
MOCK_AST_DATA = [
    {"type": "ASTNode", "value": "some_ast_1"},
    {"type": "ASTNode", "value": "some_ast_2"},
]


def test_apibench_benchmark():
    # Patch necessary functions and classes to prevent real file system access
    with (
        patch("os.listdir", return_value=["huggingface_train.json"]),
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_dir", return_value=True),
        patch("huggingface_hub.snapshot_download"),
        patch("builtins.open", mock_open()) as mock_file,
        patch(
            "camel.benchmarks.apibench.encode_question"
        ) as mock_encode_question,
        patch(
            "camel.benchmarks.apibench.evaluate_response"
        ) as mock_evaluate_response,
        patch.object(APIBenchBenchmark, 'load'),
    ):
        # Initialize APIBenchBenchmark with mock paths within the patch context
        data_dir = "/mock_data_dir"
        save_to = "mock_save_to.json"
        benchmark = APIBenchBenchmark(data_dir=data_dir, save_to=save_to)

        # Mock the encode_question function to return a fixed prompt
        mock_encode_question.return_value = (
            "How do I use the HuggingFace API for text classification?"
        )

        # Mock the evaluate_response function to return expected results
        mock_evaluate_response.return_value = (None, True, False)

        # Mock the agent's step method to return the expected response
        mock_agent = MagicMock()
        mock_agent.step.return_value.msgs = [
            MagicMock(content="HuggingFace API call here")
        ]

        # Manually set mock data for api, eval, and ast
        benchmark._data = {
            "api": MOCK_API_DATA,
            "ast": MOCK_AST_DATA,
            "questions": MOCK_QUESTION_DATA,
            "eval": MOCK_EVAL_DATA,
        }

        # Run the benchmark
        result = benchmark.run(
            agent=mock_agent,
            dataset_name="huggingface",
            randomize=False,
            subset=1,
        )

        # Assert the benchmark loaded the data correctly
        assert len(benchmark._data["questions"]) == 1
        assert (
            benchmark._data["questions"][0]["text"]
            == "How do I use the HuggingFace API for text classification?"
        )

        # Assert the benchmark results
        assert result["total"] == 1
        assert result["correct"] == 1
        assert result["hallucination"] == 0
        assert result["accuracy"] == 1.0
        assert result["hallucination rate"] == 0.0

        # Verify that the results were written correctly to the save_to file
        written_data = json.loads(mock_file().write.call_args[0][0])
        assert (
            written_data["question"]["text"]
            == "How do I use the HuggingFace API for text classification?"
        )
        assert written_data["agent_response"] == "HuggingFace API call here"
        assert written_data["correct"]
        assert not written_data["hallucination"]
        assert written_data["error"] is None
