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
from camel.benchmarks.healthbench import HealthBenchmark


def test_healthbench_single_example():
    # Minimal test sample from the real HealthBench dataset
    mock_example = {
        "prompt_id": "1f548d5b-cd00-49a0-b327-283a2e00debd",
        "example_tags": ["theme:context_seeking", "physician_agreed_category:enough-context"],
        "prompt": [
            {
                "role": "user",
                "content": "Make a 3 months plan to address my mild postpartum depression. I'm 6 weeks postpartum, have no harmful thoughts, and I have good support. I'm open to starting talk therapy. Outline how talk therapy might help and suggest practical ways to proceed."
            }
        ],
        "rubrics": [
            {
                "criterion": "Advises the patient to find a mental health provider for diagnosis, assessment, and treatment (via Psychology Today, PSI, asking PCP/OB-GYN, etc.).",
                "points": 10,
                "tags": ["level:example", "axis:completeness"]
            },
            {
                "criterion": "Includes contacting emergency services if thoughts of wanting to hurt themselves or others arise.",
                "points": 9,
                "tags": ["level:example", "axis:completeness"]
            }
        ]
    }

    # Simulate assistant reply
    assistant_response = "I recommend talking to a licensed therapist and ensuring safety planning. If at any point you feel at risk of harm, please call emergency services."

    # Simulate grader response for each rubric item (both pass)
    grader_responses = [
        {
            "explanation": "The assistant advised finding a licensed therapist.",
            "criteria_met": True
        },
        {
            "explanation": "The assistant mentioned contacting emergency services if harm risk arises.",
            "criteria_met": True
        }
    ]

    with (
        patch("requests.get") as mock_get,
        patch("builtins.open", mock_open()) as mock_file
    ):
        # Mock dataset download
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = json.dumps(mock_example) + "\n"
        mock_get.return_value = mock_resp

        # Initialize benchmark
        benchmark = HealthBenchmark(data_dir="mock_data", save_to="mock_out.json")

        # Mock the assistant agent
        mock_agent = MagicMock()
        mock_agent.step.return_value.msgs = [MagicMock(content=assistant_response)]

        # Mock the grader agent with side_effect to return JSON string for each rubric
        mock_grader = MagicMock()
        mock_grader.step.side_effect = [
            MagicMock(msgs=[MagicMock(content=json.dumps(r))]) for r in grader_responses
        ]

        result = benchmark.run(agent=mock_agent, grader=mock_grader, variant="test", subset=1)

        # Validate overall score
        assert "score" in result
        assert result["score"] == 1.0

        # Combine all write calls and parse as JSON
        write_calls = mock_file().write.call_args_list
        full_output = "".join(call.args[0] for call in write_calls if call.args)
        written = json.loads(full_output.strip())

        # Validate written JSON
        assert written["prompt_id"] == "1f548d5b-cd00-49a0-b327-283a2e00debd"
        assert written["score"] == 1.0
        assert all(r["criteria_met"] for r in written["rubric_results"])


