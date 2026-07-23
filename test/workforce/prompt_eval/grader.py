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
r"""Automated grader for WorkflowSummary output.

Encodes the constraints the summarization prompt promises to the model so a
generated summary can be scored without a human. Shared by both the
deterministic pytest suite (test_workflow_prompt_quality.py) and the live-LLM
baseline harness (run_baseline.py).

Keep in sync with the Field descriptions in
``camel/utils/context_utils.py``: if a prompt edit changes a limit, change the
matching check here in the same PR.
"""

import re
from dataclasses import dataclass, field
from typing import List

from camel.utils.context_utils import WorkflowSummary

NUM_CHECKS = 8


@dataclass
class GradeResult:
    violations: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations

    @property
    def score(self) -> float:
        return round(1.0 - len(self.violations) / NUM_CHECKS, 3)


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def grade_workflow_summary(ws: WorkflowSummary) -> GradeResult:
    r"""Grade a WorkflowSummary against the prompt's stated contract."""
    r = GradeResult()

    # 1. task_title: <= 10 words, non-empty.
    if not ws.task_title.strip():
        r.violations.append("task_title empty")
    elif _word_count(ws.task_title) > 10:
        r.violations.append(
            f"task_title has {_word_count(ws.task_title)} words (> 10)"
        )

    # 2. task_description: <= 80 words, non-empty.
    if not ws.task_description.strip():
        r.violations.append("task_description empty")
    elif _word_count(ws.task_description) > 80:
        r.violations.append(
            f"task_description has {_word_count(ws.task_description)} "
            "words (> 80)"
        )

    # 3. agent_title: <= 5 words, lowercase_with_underscores, no spaces.
    if not ws.agent_title.strip():
        r.violations.append("agent_title empty")
    elif " " in ws.agent_title or ws.agent_title != ws.agent_title.lower():
        r.violations.append(
            f"agent_title '{ws.agent_title}' not lowercase_snake_case"
        )

    # 4. steps: non-empty; each starts with a word after stripping numbering.
    if not ws.steps:
        r.violations.append("steps empty")
    else:
        for i, step in enumerate(ws.steps, 1):
            stripped = re.sub(r"^\s*(\d+[.)]|\-|\*)\s*", "", step).strip()
            if not stripped or not stripped[0].isalpha():
                r.violations.append(f"step {i} does not start with a word")
                break

    # 5. tags: 3-10 tags, kebab-case.
    if not (3 <= len(ws.tags) <= 10):
        r.violations.append(f"{len(ws.tags)} tags (expected 3-10)")
    else:
        bad = [
            t
            for t in ws.tags
            if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", t)
        ]
        if bad:
            r.violations.append(f"tags not kebab-case: {bad}")

    # 6. tools: each entry is a single line.
    for t in ws.tools:
        if "\n" in t:
            r.violations.append("a tools entry spans multiple lines")
            break

    # 7. operation_mode == 'update' requires target_workflow_filename.
    if ws.operation_mode == "update" and not (
        ws.target_workflow_filename and ws.target_workflow_filename.strip()
    ):
        r.violations.append("operation_mode=update but no target filename")

    # 8. operation_mode == 'create' must not carry a target filename.
    if ws.operation_mode == "create" and ws.target_workflow_filename:
        r.violations.append("operation_mode=create but target filename set")

    return r
