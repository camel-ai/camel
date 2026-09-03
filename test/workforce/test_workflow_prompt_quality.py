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
r"""Prompt-quality tests for workflow memory summarization/selection.

These tests are deterministic (no LLM calls). They encode the *contract*
that the summarization prompt promises to the model, so that a generated
``WorkflowSummary`` can be graded automatically. The same
``grade_workflow_summary`` function is reused by the live-LLM baseline
harness in ``test/workforce/prompt_eval/`` to score real model output.

Run:
    pytest test/workforce/test_workflow_prompt_quality.py -v
"""

import os
import re
import sys
from typing import List

import pytest

from camel.utils.context_utils import WorkflowSummary

# Shared grader lives in the prompt_eval package next to the baseline harness,
# so the deterministic tests and the live-LLM eval score output the same way.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "prompt_eval"))
from grader import grade_workflow_summary  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures: a known-good summary and mutated bad ones.
# --------------------------------------------------------------------------- #
def _good_summary(**overrides) -> WorkflowSummary:
    base = dict(
        agent_title="data_analyst",
        task_title="Summarize weekly sales into a report",
        task_description=(
            "Pull the weekly sales figures, compute totals per region, "
            "and produce a short written summary highlighting the top and "
            "bottom performers for the leadership channel."
        ),
        tools=[
            "SlackToolkit: post the report -> delivered summary to the "
            "leadership channel",
        ],
        steps=[
            "1. Load the weekly sales spreadsheet",
            "2. Aggregate totals per region",
            "3. Post the summary to Slack",
        ],
        failure_and_recovery_strategies=[],
        notes_and_observations="",
        tags=["data-analysis", "report-generation", "slack-automation"],
        operation_mode="create",
        target_workflow_filename=None,
    )
    base.update(overrides)
    return WorkflowSummary(**base)


class TestGraderOnGoodOutput:
    def test_good_summary_passes(self):
        result = grade_workflow_summary(_good_summary())
        assert result.passed, result.violations
        assert result.score == 1.0


class TestGraderCatchesViolations:
    def test_task_title_too_long(self):
        ws = _good_summary(
            task_title="This is an overly long generic task title that "
            "keeps going well past ten words for sure"
        )
        assert "task_title" in " ".join(grade_workflow_summary(ws).violations)

    def test_task_description_too_long(self):
        ws = _good_summary(task_description=" ".join(["word"] * 81))
        v = " ".join(grade_workflow_summary(ws).violations)
        assert "task_description" in v

    def test_agent_title_not_snake_case(self):
        ws = _good_summary(agent_title="Data Analyst")
        assert "agent_title" in " ".join(grade_workflow_summary(ws).violations)

    def test_too_few_tags(self):
        ws = _good_summary(tags=["data-analysis"])
        assert "tags" in " ".join(grade_workflow_summary(ws).violations)

    def test_tags_not_kebab_case(self):
        ws = _good_summary(
            tags=["data_analysis", "Report Generation", "slack"]
        )
        assert "kebab" in " ".join(grade_workflow_summary(ws).violations)

    def test_empty_steps(self):
        ws = _good_summary(steps=[])
        assert "steps empty" in grade_workflow_summary(ws).violations

    def test_update_without_target_filename(self):
        ws = _good_summary(
            operation_mode="update", target_workflow_filename=None
        )
        assert any(
            "update" in v for v in grade_workflow_summary(ws).violations
        )

    def test_create_with_stray_target_filename(self):
        ws = _good_summary(
            operation_mode="create",
            target_workflow_filename="some_other_workflow",
        )
        assert any(
            "create" in v for v in grade_workflow_summary(ws).violations
        )


# --------------------------------------------------------------------------- #
# Selection-prompt parsing robustness.
#
# The production selection step turns an LLM reply like "1, 3, 5" into indices
# via re.findall(r'\d+', ...). This mirrors that parse so we can pin the
# behaviour and expose failure modes (stray digits, over/under selection)
# without spinning up a full Workforce. Keep in sync with
# WorkflowMemoryManager._select_relevant_workflows.
# --------------------------------------------------------------------------- #
def _parse_selection(reply: str, max_files: int, num_workflows: int) -> List[int]:
    numbers = re.findall(r"\d+", reply)
    indices = [int(n) - 1 for n in numbers[:max_files]]
    return [i for i in indices if 0 <= i < num_workflows]


class TestSelectionParsing:
    def test_clean_reply(self):
        assert _parse_selection("1, 3, 5", 3, 6) == [0, 2, 4]

    def test_prose_wrapped_reply(self):
        assert _parse_selection("I would pick 2 and 4.", 2, 6) == [1, 3]

    def test_over_selection_is_truncated(self):
        # Model returns more than asked; only first max_files kept.
        assert _parse_selection("1, 2, 3, 4", 2, 6) == [0, 1]

    def test_out_of_range_indices_dropped(self):
        assert _parse_selection("1, 99", 2, 3) == [0]

    @pytest.mark.xfail(
        reason="Known failure mode: stray digits in prose (e.g. a year) are "
        "parsed as selections. Documents a case the optimized prompt should "
        "make impossible by constraining the reply format.",
        strict=True,
    )
    def test_stray_digit_in_prose_should_not_be_selected(self):
        # 'top 3 from 2024' -> digits 3 and 2024; 3-1=2 becomes a phantom pick.
        assert _parse_selection("the top 3 from 2024", 1, 6) == []
