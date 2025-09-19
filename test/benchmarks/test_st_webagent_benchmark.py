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
from pathlib import Path

from camel.benchmarks.st_webagent_benchmark import (
    STWebAgentBenchmark,
    STWebAgentResult,
)


def _dummy_result(task_id: str) -> STWebAgentResult:
    return STWebAgentResult(
        task_id=task_id,
        completion_rate=1.0,
        completion_under_policy=1.0,
        partial_completion_under_policy=1.0,
        policy_violations={
            "user_consent": 0,
            "boundary": 0,
            "strict_execution": 0,
            "hierarchy": 0,
            "robustness": 0,
            "error_handling": 0,
        },
        risk_ratios={
            "user_consent": 0.0,
            "boundary": 0.0,
            "strict_execution": 0.0,
            "hierarchy": 0.0,
            "robustness": 0.0,
            "error_handling": 0.0,
        },
        execution_time=0.01,
        steps_taken=1,
        success=True,
    )


def test_stwebagent_benchmark_loads_csv():
    data_root = Path("st-webagentbench")
    csv_path = data_root / "stwebagentbench" / "test.csv"
    assert csv_path.exists(), "Expected st-webagentbench/test.csv to exist"

    benchmark = STWebAgentBenchmark(
        data_dir=str(data_root),
        save_to="tbench_results",
        processes=1,
    ).load()

    # Basic shape checks
    df = benchmark._data  # type: ignore[attr-defined]
    assert len(df) > 0
    assert "full_json" in df.columns

    # Ensure JSON lines are parsable
    sample = df.iloc[0]["full_json"]
    if isinstance(sample, str):
        json.loads(sample)


def test_stwebagent_benchmark_run_with_monkeypatched_evaluator(monkeypatch):
    data_root = Path("st-webagentbench")
    benchmark = STWebAgentBenchmark(
        data_dir=str(data_root),
        save_to="tbench_results",
        processes=1,
    ).load()

    def fake_eval(self, task, agent):
        return _dummy_result(task.task_id)

    monkeypatch.setattr(
        STWebAgentBenchmark,
        "_evaluate_task",
        fake_eval,
        raising=True,
    )

    # Run on a small subset to keep the test fast and deterministic
    start_len = len(benchmark._results)  # type: ignore[attr-defined]
    benchmark.run(agent=None, on="test", subset=3)  # type: ignore[arg-type]
    end_len = len(benchmark._results)  # type: ignore[attr-defined]

    assert end_len - start_len == 3

    summary = benchmark.get_summary_metrics()
    assert summary["total_tasks"] == 3
    assert summary["successful_tasks"] == 3
    assert summary["avg_completion_rate"] == 1.0
    assert summary["avg_completion_under_policy"] == 1.0
