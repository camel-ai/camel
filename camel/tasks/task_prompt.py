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
from camel.prompts import TextPrompt

# ruff: noqa: E501
TASK_DECOMPOSE_PROMPT = TextPrompt(
    """As a Task Decomposer with the role of {role_name}, your objective is to divide the given task into subtasks.
You have been provided with the following objective:

{content}

Please format the subtasks as a numbered list within <tasks> tags, as demonstrated below:
<tasks>
<task>Subtask 1</task>
<task>Subtask 2</task>
</tasks>

Each subtask should be concise, concrete, and achievable for a {role_name}.
Ensure that the task plan is created without asking any questions.
Be specific and clear.
"""
)


TASK_COMPOSE_PROMPT = TextPrompt(
    """As a Task composer with the role of {role_name}, your objective is to gather result from all sub tasks to get the final answer.
The root task is:

{content}

The additional information of the task is:

{additional_info}

The related tasks result and status:

{other_results}

so, the final answer of the root task is: 
"""
)


TASK_EVOLVE_PROMPT = TextPrompt(
    """As a Task Creator for {role_name}, your objective is to draw inspiration from the provided task to develop an entirely new one.
The new task should fall within the same domain as the given task but be more complex and unique.
It must be reasonable, understandable, and actionable by {role_name}.
The created task must be enclosed within <task> </task> tags.
<task>
... created task
</task>

## given task
{content}

## created task
"""
)
