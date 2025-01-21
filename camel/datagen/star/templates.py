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


from dataclasses import dataclass


@dataclass(frozen=True)
class STaRTemplates:
    """Contains template prompts for STaR reasoning generation"""

    reasoning_template = """Let's solve this step by step:
Problem: {problem}
1. First, let's understand what we're asked
2. Let's break this down into parts
3. Let's solve each part systematically
4. Finally, let's verify our solution

Please show your complete reasoning process."""

    evaluation_template = """Please evaluate this reasoning trace and 
provide scores and feedback in valid JSON format.

Problem: {problem}

Reasoning Trace:
{trace}

Evaluate for:
1. Correctness (Is each step logically sound?)
2. Clarity (Is the explanation clear and well-structured?)
3. Completeness (Are all necessary steps included?)

Respond ONLY with a JSON object in this exact format:
{{
    "correctness": <score between 0 and 1>,
    "clarity": <score between 0 and 1>,
    "completeness": <score between 0 and 1>,
    "feedback": "<specific feedback for improvement>"
}}"""

    improvement_template = """Based on this feedback, generate an 
    improved reasoning trace:
Problem: {problem}

Previous Trace:
{trace}

Feedback:
{feedback}

Generate a new, improved reasoning trace that addresses the feedback."""
