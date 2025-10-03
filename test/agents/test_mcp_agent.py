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

from typing import List

import pytest

from camel.parsers.mcp_tool_call_parser import extract_tool_calls_from_text


@pytest.mark.parametrize(
    "content,expected",
    [
        (
            """Here is the call:
```json
{
  \"server_idx\": 0,
  \"tool_name\": \"search_tool\",
  \"tool_args\": {\"query\": \"hello\"}
}
```
""",
            [
                {
                    "server_idx": 0,
                    "tool_name": "search_tool",
                    "tool_args": {"query": "hello"},
                }
            ],
        ),
        (
            """Please run this: {\"server_idx\": 1, \"tool_name\": \"math\",
            \"tool_args\": {\"a\": 1, \"b\": 2}}""",
            [
                {
                    "server_idx": 1,
                    "tool_name": "math",
                    "tool_args": {"a": 1, "b": 2},
                }
            ],
        ),
        (
            """Tool candidate {'server_idx': 0, 'tool_name': 'search',
            'tool_args': {'query': 'plan 2'}}""",
            [
                {
                    "server_idx": 0,
                    "tool_name": "search",
                    "tool_args": {"query": "plan 2"},
                }
            ],
        ),
        (
            """Multiple calls: [{\"server_idx\": 0, \"tool_name\": \"alpha\",
            \"tool_args\": {}}, {\"server_idx\": 1, \"tool_name\": \"beta\",
            \"tool_args\": {\"q\": \"x\"}}]""",
            [
                {"server_idx": 0, "tool_name": "alpha", "tool_args": {}},
                {
                    "server_idx": 1,
                    "tool_name": "beta",
                    "tool_args": {"q": "x"},
                },
            ],
        ),
    ],
)
def test_extract_tool_calls_from_text(
    content: str, expected: List[dict]
) -> None:
    tool_calls = extract_tool_calls_from_text(content)

    assert len(tool_calls) == len(expected)
    for idx, tool_call in enumerate(tool_calls):
        for key, value in expected[idx].items():
            assert tool_call[key] == value


def test_extract_tool_calls_without_payload() -> None:
    assert extract_tool_calls_from_text("No calls available") == []


def test_extract_tool_calls_from_yaml_block() -> None:
    pytest.importorskip("yaml")

    content = (
        "Here is the YAML call:\n"
        "```yaml\n"
        "server_idx: 2\n"
        "tool_name: yaml_tool\n"
        "tool_args:\n"
        "  prompt: Hello\n"
        "```\n"
    )

    expected = {
        "server_idx": 2,
        "tool_name": "yaml_tool",
        "tool_args": {"prompt": "Hello"},
    }

    tool_calls = extract_tool_calls_from_text(content)

    assert len(tool_calls) == 1
    assert tool_calls[0] == expected
