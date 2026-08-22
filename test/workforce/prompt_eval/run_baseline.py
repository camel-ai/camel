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
r"""Baseline harness for the workflow-summarization prompt.

Runs each case in dataset.py through a real model using the *current*
production prompt (WorkflowSummary.get_instruction_prompt + schema), grades
the output with the shared grader, and writes a JSON scorecard. Run it once
on ``main`` to capture the baseline, then again on your prompt-edit branch and
diff the two scorecards — that is the before/after evidence issue #3375 asks
for.

Requires a model key (e.g. OPENAI_API_KEY). Usage:

    python test/workforce/prompt_eval/run_baseline.py \
        --model gpt-4o-mini --runs 3 --out baseline.json

Determinism note: LLM output varies run-to-run. Use --runs N (>=3) and read
the mean/worst columns, not a single sample, before declaring a win.
"""

import argparse
import json
import statistics
from typing import Any, Dict, List

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from camel.utils.context_utils import WorkflowSummary

# Run as a plain script: `python test/workforce/prompt_eval/run_baseline.py`.
# The script's own directory is on sys.path, so import siblings directly.
from dataset import CASES, EvalCase
from grader import grade_workflow_summary


def _summarize_once(case: EvalCase, model) -> WorkflowSummary:
    r"""Reproduce the production summarization call for one transcript."""
    agent = ChatAgent(
        system_message=(
            "You are a helpful assistant that summarizes conversations"
        ),
        model=model,
    )
    prompt = (
        f"{WorkflowSummary.get_instruction_prompt().rstrip()}\n\n"
        f"AGENT CONVERSATION TO BE SUMMARIZED:\n{case.transcript}"
    )
    response = agent.step(prompt, response_format=WorkflowSummary)
    parsed = response.msgs[-1].parsed
    if not isinstance(parsed, WorkflowSummary):
        raise ValueError(f"model did not return a WorkflowSummary: {parsed!r}")
    return parsed


def _grade_case(case: EvalCase, ws: WorkflowSummary) -> Dict[str, Any]:
    generic = grade_workflow_summary(ws)
    violations = list(generic.violations)
    for check in case.expect:
        v = check(ws)
        if v:
            violations.append(v)
    # total checks = 8 generic + case-specific expectations.
    total = 8 + len(case.expect)
    return {
        "score": round(1.0 - len(violations) / total, 3),
        "violations": violations,
    }


def run(model_platform: str, model_type: str, runs: int) -> Dict[str, Any]:
    model = ModelFactory.create(
        model_platform=ModelPlatformType(model_platform),
        model_type=model_type,
    )
    results: Dict[str, Any] = {"cases": {}, "config": {
        "model_platform": model_platform,
        "model_type": model_type,
        "runs": runs,
    }}
    all_scores: List[float] = []

    for case in CASES:
        scores: List[float] = []
        sample_violations: List[List[str]] = []
        for _ in range(runs):
            ws = _summarize_once(case, model)
            graded = _grade_case(case, ws)
            scores.append(graded["score"])
            sample_violations.append(graded["violations"])
        results["cases"][case.name] = {
            "mean": round(statistics.mean(scores), 3),
            "worst": min(scores),
            "scores": scores,
            "violations_last_run": sample_violations[-1],
        }
        all_scores.extend(scores)

    results["overall_mean"] = round(statistics.mean(all_scores), 3)
    results["overall_worst"] = min(all_scores)
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model-platform", default="openai")
    ap.add_argument("--model", dest="model_type", default="gpt-4o-mini")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", default="baseline.json")
    args = ap.parse_args()

    results = run(args.model_platform, args.model_type, args.runs)
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nOverall mean={results['overall_mean']} "
          f"worst={results['overall_worst']}  ({args.runs} runs/case)")
    for name, r in results["cases"].items():
        flag = "" if r["worst"] == 1.0 else "  <-- has violations"
        print(f"  {name:32s} mean={r['mean']:.3f} worst={r['worst']:.3f}{flag}")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
