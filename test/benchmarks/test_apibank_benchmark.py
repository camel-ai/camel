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

from camel.benchmarks import APIBankBenchmark
from camel.benchmarks.apibank import APIBankSample

# Mock data for the APIBankBenchmark
MOCK_API_DATA = [
    {
        "api_call": "huggingface_api_call_example",
        "domain": "Natural Language Processing Text Classification",
    }
]
MOCK_GROUND_TRUTH = {"role": "API", "output": "huggingface_api_output_example"}
MOCK_CHAT_HISTORY = [
    {
        "role": "User",
        "text": "How do I use the HuggingFace API for text classification?",
    },
    {
        "role": "API",
        "api_name": "huggingface_api",
        "param_dict": {"input": "text"},
        "result": {"output": "huggingface_api_output_example"},
    },
    {
        "role": "AI",
        "text": "You can use the HuggingFace API to classify text using \
            their models.",
    },
]

# Create mock API samples
MOCK_SAMPLE = APIBankSample.from_chat_history(MOCK_CHAT_HISTORY)

# Mock data that the benchmark will load
MOCK_DATA = {
    "level-1-mock": [
        {
            "chat_history": MOCK_CHAT_HISTORY,
            "ground_truth": MOCK_GROUND_TRUTH,
            "api_calls": MOCK_API_DATA,
        }
    ]
}


def test_apibank_benchmark():
    # Patch necessary functions and classes to prevent real file system access
    with (
        patch("os.listdir", return_value=["level-1-mock.jsonl"]),
        patch("pathlib.Path.mkdir"),
        patch("os.chdir"),
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.is_dir", return_value=True),
        patch("builtins.open", mock_open()) as mock_file,
        patch("camel.benchmarks.apibank.Evaluator") as mock_evaluator,
        patch("camel.benchmarks.apibank.agent_call") as mock_agent_call,
        patch("camel.benchmarks.apibank.get_api_call") as mock_get_api_call,
        patch.object(APIBankBenchmark, 'load') as mock_load,
    ):
        # Initialize APIBankBenchmark with mock paths within the patch context
        save_to = "mock_save_to.json"
        benchmark = APIBankBenchmark(save_to=save_to)

        # Mock the agent call to return a fixed API response
        mock_agent_call.return_value = "huggingface_api_output_example"
        # Mock the get_api_call to return a fixed API call
        mock_get_api_call.return_value = "mock_api_call"

        # Mock the evaluator to return correct evaluation
        mock_evaluator.return_value = MagicMock()
        evaluator_instance = mock_evaluator.return_value
        evaluator_instance.evaluate.return_value = (
            True,
            "huggingface_api_output_example",
        )
        evaluator_instance.get_all_sample_ids.return_value = [0]
        evaluator_instance.dataset = (
            MOCK_SAMPLE  # Provide mock data as a list of samples
        )
        evaluator_instance.get_model_input.return_value = (
            "mock_api_description",
            MOCK_CHAT_HISTORY,
        )

        # Mock the load method to load mock data directly
        mock_load.return_value = None
        benchmark._data = MOCK_DATA  # Manually set mock data for the benchmark

        # Run the benchmark
        result = benchmark.run(
            agent=MagicMock(), level="level-1", randomize=False, subset=1
        )

        # Assert that the benchmark loaded the data correctly
        assert len(benchmark._data["level-1-mock"]) == 1
        assert (
            benchmark._data["level-1-mock"][0]["chat_history"][0]["text"]
            == "How do I use the HuggingFace API for text classification?"
        )

        # Assert the benchmark results
        assert result["total"] == 1
        assert result["correct"] == 1
        assert result["accuracy"] == 1.0

        # Verify that the results were written correctly to the save_to file
        written_data = json.loads(mock_file().write.call_args[0][0])
        print(MOCK_SAMPLE)
        assert written_data["Model_output"] == "huggingface_api_output_example"
        assert written_data["Correct"]
