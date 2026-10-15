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

import os

import pytest

from camel.societies.workforce.prompts import (
    PROCESS_TASK_PROMPT,
    ROLEPLAY_PROCESS_TASK_PROMPT,
)


@pytest.mark.parametrize(
    "prompt_template",
    [PROCESS_TASK_PROMPT, ROLEPLAY_PROCESS_TASK_PROMPT],
    ids=["PROCESS_TASK_PROMPT", "ROLEPLAY_PROCESS_TASK_PROMPT"],
)
def test_process_task_prompt_content_placed_last(prompt_template):
    r"""Verify that {content} appears after {parent_task_content},
    {dependency_tasks_info}, and {additional_info} so sibling subtasks can
    share a common prefix for server-side prompt caching (Issue #4384).
    """
    prompt_str = str(prompt_template)

    # Ensure all required placeholders are present
    assert "{content}" in prompt_str
    assert "{parent_task_content}" in prompt_str
    assert "{dependency_tasks_info}" in prompt_str
    assert "{additional_info}" in prompt_str

    content_idx = prompt_str.index("{content}")
    parent_idx = prompt_str.index("{parent_task_content}")
    dep_idx = prompt_str.index("{dependency_tasks_info}")
    additional_idx = prompt_str.index("{additional_info}")

    # {content} must come strictly after all shared context placeholders
    assert content_idx > parent_idx
    assert content_idx > dep_idx
    assert content_idx > additional_idx


@pytest.mark.parametrize(
    "prompt_template",
    [PROCESS_TASK_PROMPT, ROLEPLAY_PROCESS_TASK_PROMPT],
    ids=["PROCESS_TASK_PROMPT", "ROLEPLAY_PROCESS_TASK_PROMPT"],
)
def test_sibling_subtasks_share_cached_prefix(prompt_template):
    r"""Verify that formatting prompts for sibling subtasks with the same
    shared context produces an identical prefix that includes parent task,
    dependency info, and additional info.
    """
    shared_context = {
        "parent_task_content": "Shared parent task goal",
        "dependency_tasks_info": "Dependency results summary",
        "additional_info": "Shared guidelines and constraints",
    }

    prompt_sibling_1 = str(
        prompt_template.format(
            content="Subtask 1: Process data part A",
            **shared_context,
        )
    )
    prompt_sibling_2 = str(
        prompt_template.format(
            content="Subtask 2: Process data part B",
            **shared_context,
        )
    )

    common_prefix = os.path.commonprefix([prompt_sibling_1, prompt_sibling_2])

    # The common prefix must contain all shared context
    assert shared_context["parent_task_content"] in common_prefix
    assert shared_context["dependency_tasks_info"] in common_prefix
    assert shared_context["additional_info"] in common_prefix

    # The divergence must only be in the subtask-specific content
    assert "Subtask 1" not in common_prefix
    assert "Subtask 2" not in common_prefix
