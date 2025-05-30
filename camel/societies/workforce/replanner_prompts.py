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

ANALYZE_FAILURE_PROMPT = TextPrompt(
    """You need to analyze why a task has failed based on the information provided.
The content of the failed task is:

==============================
{content}
==============================

Here is the error log or execution history of the task:

==============================
{error_log}
==============================

Here is the execution history of the task:

==============================
{history}
==============================

You must return a concise analysis of why the task failed. Consider the following possible reasons:
1. Task complexity (too complex for a single agent)
2. Missing prerequisites or dependencies
3. Lack of necessary tools or capabilities
4. Logical errors in the task description
5. Resource limitations
6. Other specific reasons

Your analysis should be brief but insightful, focusing on the root cause of the failure.
"""
)

REPLAN_TASK_PROMPT = TextPrompt(
    """You need to replan a failed task based on the failure analysis.
The content of the original task is:

==============================
{original_content}
==============================

The analysis of why the task failed:

==============================
{failure_reason}
==============================

Information about available worker nodes that could potentially handle this task:

==============================
{child_nodes_info}
==============================

Based on this information, you need to replan the task. You can:
1. Reformulate the task description to be clearer or more achievable
2. Adjust the scope of the task (narrow it if too broad)
3. Provide more specific instructions or context
4. Suggest a different approach to solving the task

Your replanned task should address the identified failure reasons while maintaining the original goal.
Return only the new task description.
"""
)

GET_MAX_DEPTH_PROMPT = TextPrompt(
    """You need to determine the appropriate maximum depth for a task based on its characteristics.
The content of the task is:

==============================
{content}
==============================

Here are some additional details about the task:

==============================
{additional_info}
==============================

Different types of tasks may benefit from different maximum depths:
- Technical tasks (programming, data analysis) may need deeper decomposition (5 levels)
- Creative tasks (writing, design) may work well with medium decomposition (4 levels)
- Simple or straightforward tasks may only need shallow decomposition (3 levels)

Based on the task content and details, determine the appropriate maximum depth for this task.
Your response should be a single integer representing the recommended maximum depth.
"""
)
