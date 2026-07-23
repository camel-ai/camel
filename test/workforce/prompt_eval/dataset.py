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
r"""Eval dataset for the workflow-summarization prompt.

Each case is a synthetic agent transcript (the input the summarizer sees) plus
``expect`` assertions used by the grader in run_baseline.py. Add cases that
cover the axes you care about: task complexity (short vs long), presence of
tool calls, failures/recovery, and continuation (update vs create).
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from camel.utils.context_utils import WorkflowSummary


@dataclass
class EvalCase:
    name: str
    # The conversation the summarizer must compress. Kept as a plain string;
    # the runner appends it to the instruction prompt exactly as production
    # does (structured_prompt + "AGENT CONVERSATION TO BE SUMMARIZED:\n...").
    transcript: str
    # Extra case-specific assertions on top of the generic grader. Each returns
    # a violation string, or None if satisfied.
    expect: List[Callable[[WorkflowSummary], Optional[str]]] = field(
        default_factory=list
    )


def _tags_include(*wanted: str):
    def check(ws: WorkflowSummary) -> Optional[str]:
        have = {t.lower() for t in ws.tags}
        missing = [w for w in wanted if not any(w in h for h in have)]
        return f"expected a tag related to {missing}" if missing else None

    return check


def _max_words_description(n: int):
    def check(ws: WorkflowSummary) -> Optional[str]:
        import re

        wc = len(re.findall(r"\S+", ws.task_description))
        return f"task_description {wc} words (> {n})" if wc > n else None

    return check


def _has_failure_note():
    def check(ws: WorkflowSummary) -> Optional[str]:
        return (
            None
            if ws.failure_and_recovery_strategies
            else "expected a failure_and_recovery entry"
        )

    return check


def _no_failure_note():
    def check(ws: WorkflowSummary) -> Optional[str]:
        return (
            "hallucinated a failure when none occurred"
            if ws.failure_and_recovery_strategies
            else None
        )

    return check


CASES: List[EvalCase] = [
    EvalCase(
        name="trivial_math",
        transcript=(
            "user: What is 17 * 23?\n"
            "assistant: 17 * 23 = 391.\n"
        ),
        # Prompt says trivial tasks should stay short (<60 words) and not
        # invent tools/failures.
        expect=[
            _max_words_description(40),
            _no_failure_note(),
        ],
    ),
    EvalCase(
        name="web_scrape_with_tool",
        transcript=(
            "user: Get the titles of the top 5 posts on Hacker News.\n"
            "assistant: I'll fetch the front page.\n"
            "tool_call: BrowserToolkit.visit_page(url='https://news.ycombinator.com')\n"
            "tool_result: <html> ... 5 story titles ...\n"
            "assistant: Here are the top 5 titles: [...].\n"
        ),
        expect=[
            _tags_include("web", "scrap"),
            _no_failure_note(),
        ],
    ),
    EvalCase(
        name="pandas_failure_then_recovery",
        transcript=(
            "user: Analyze sales.csv and give me the monthly totals.\n"
            "assistant: Running an analysis script.\n"
            "tool_call: CodeExecutionToolkit.run(code='import pandas as pd; ...')\n"
            "tool_result: ModuleNotFoundError: No module named 'pandas'\n"
            "assistant: Pandas is missing, installing it.\n"
            "tool_call: CodeExecutionToolkit.run(code='pip install pandas')\n"
            "tool_result: Successfully installed pandas-2.2.0\n"
            "assistant: Re-ran analysis. Monthly totals: [...].\n"
        ),
        expect=[
            _has_failure_note(),
            _tags_include("data", "analysis"),
        ],
    ),
    EvalCase(
        name="continuation_update",
        transcript=(
            "SYSTEM CONTEXT: A prior workflow 'list_github_stargazers' was "
            "loaded (filename: list_github_stargazers).\n"
            "user: Same as before but also fetch each stargazer's location.\n"
            "assistant: Extending the previous stargazer workflow to include "
            "location via the GitHub API.\n"
            "tool_call: GithubToolkit.get_stargazers(repo='camel-ai/camel')\n"
            "tool_result: [{login, location}, ...]\n"
            "assistant: Done, added location column.\n"
        ),
        # This is a refinement of a loaded workflow -> operation_mode 'update'
        # with the same task_title and a target filename.
        expect=[
            lambda ws: (
                None
                if ws.operation_mode == "update"
                else "expected operation_mode=update for a continuation"
            ),
            lambda ws: (
                None
                if (ws.target_workflow_filename or "").strip()
                else "expected target_workflow_filename to be set"
            ),
        ],
    ),
]
