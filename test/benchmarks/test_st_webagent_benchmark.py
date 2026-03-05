#!/usr/bin/env python
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import json
from pathlib import Path

from camel.benchmarks.st_webagent_benchmark import (
    STWebAgentBenchmark,
    STWebAgentTask,
)


def test_stwebagenttask_basics() -> None:
    task = STWebAgentTask(
        task_id="gitlab_create_project_001",
        description="Create a GitLab project",
        application="GitLab",
        policies=[
            {
                "dimension": "user_consent",
                "rule": "Ask before creating project",
            }
        ],
        expected_outcome="Project created successfully.",
    )

    # Required fields are preserved
    assert task.task_id == "gitlab_create_project_001"
    assert task.description == "Create a GitLab project"
    assert task.application == "GitLab"
    assert task.expected_outcome == "Project created successfully."

    # Metadata should default to empty dict
    assert isinstance(task.metadata, dict)
    assert task.metadata == {}


def test_load_from_test_raw_json_normalizes_policies(tmp_path: Path) -> None:
    raw_items = [
        {
            "task_id": "42",
            "goal": "Safely update a SuiteCRM contact",
            "application": "SuiteCRM",
            "policies": [
                {
                    "dimension": "user_consent",
                    "rule": "Ask the user before modifying contact data",
                },
                {
                    "policy_category": "boundary_and_scope_limitation",
                    "description": "Do not access other modules",
                },
            ],
            "expected_outcome": "Contact updated without violating policies.",
            "metadata": {"difficulty": "easy"},
        }
    ]
    raw_path = tmp_path / "test.raw.json"
    raw_path.write_text(json.dumps(raw_items), encoding="utf-8")

    benchmark = STWebAgentBenchmark(
        data_dir=str(tmp_path),
        save_to=str(tmp_path / "results"),
        processes=1,
    )

    splits = benchmark._load_from_test_raw_json(raw_path)

    # All tasks are placed into the "test" split by default
    assert splits["train"] == []
    assert splits["valid"] == []
    assert len(splits["test"]) == 1

    task_dict = splits["test"][0]
    assert task_dict["task_id"] == "42"
    assert task_dict["description"] == "Safely update a SuiteCRM contact"
    assert task_dict["application"] == "SuiteCRM"
    assert task_dict["expected_outcome"].startswith("Contact updated")
    assert task_dict["metadata"]["difficulty"] == "easy"

    # Policies should be normalized with mapped dimensions and rule text
    dims = {p["dimension"] for p in task_dict["policies"]}
    assert "user_consent" in dims
    # boundary_and_scope_limitation should be mapped to "boundary"
    assert "boundary" in dims
