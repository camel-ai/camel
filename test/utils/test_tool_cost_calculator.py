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

import pytest

from camel.utils.tool_cost_calculator import ToolCostCalculator


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


@pytest.mark.parametrize(
    "tool_name,args,result,expected_category,base_tokens",
    [
        (
            "search_google",
            {"query": "ai trends 2025"},
            "found 10 results",
            "search_api",
            50,
        ),
        (
            "browser_get_som_screenshot",
            {"url": "https://example.com"},
            "screenshot captured",
            "browser_automation",
            500,
        ),
        (
            "shell_exec",
            {"command": "ls -la"},
            "listing done",
            "code_execution",
            100,
        ),
        (
            "create_note",
            {"content": "hello world"},
            "note created",
            "simple_utility",
            50,
        ),
    ],
)
def test_estimate_tool_cost_basic(
    tool_name, args, result, expected_category, base_tokens
):
    calc = ToolCostCalculator(token_counter=None)

    info = calc.estimate_tool_cost(tool_name, args, result)

    input_text = next(iter(args.values())) if args else ""
    expected_prompt = _word_count(str(input_text))
    expected_completion = _word_count(str(result))

    assert info["prompt_tokens"] == expected_prompt
    assert info["completion_tokens"] == expected_completion

    assert (
        info["total_tokens"]
        == base_tokens + expected_prompt + expected_completion
    )

    assert info["tool_category"] == expected_category
